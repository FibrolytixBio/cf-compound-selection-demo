from typing import List, Dict, Optional, Literal
import os
import asyncio, concurrent.futures
from pathlib import Path
import fcntl
import json
import time

import httpx
from pydantic import BaseModel, Field
from pubmedclient.models import Db, EFetchRequest, ESearchRequest
from pubmedclient.sdk import efetch, esearch, pubmedclient_client


# ============================= Web Search =============================


class WebSearchRequest(BaseModel):
    query: str = Field(
        description="The search string used to query the web, such as a topic, question, or keyword."
    )
    max_results: int = Field(
        default=5,
        ge=1,
        le=100,
        description="Maximum number of search results to return (1-100).",
    )


def search_web(request: WebSearchRequest) -> List[Dict[str, str]]:
    """Search the web using Tavily API with token-optimized results"""
    api_key = os.environ.get("TAVILY_API_KEY")

    url = "https://api.tavily.com/search"
    headers = {"Content-Type": "application/json"}
    payload = {
        "api_key": api_key,
        "query": request.query,
        "search_depth": "basic",
        "max_results": request.max_results,
        "include_answer": False,
        "include_raw_content": False,
        "include_images": False,
    }

    with httpx.Client(timeout=30) as client:
        response = client.post(url, json=payload, headers=headers)
        response.raise_for_status()
        data = response.json()

        results = []
        for result in data.get("results", [])[: request.max_results]:
            snippet = result.get("content", "")
            title = result.get("title", "No title")
            results.append(
                {
                    "title": title,
                    "snippet": snippet,
                    "url": result.get("url", "")[:50],
                }
            )
        return results


# ============================= PubMed Search =============================


class FileBasedRateLimiter:
    def __init__(self, max_requests: int = 3, time_window: float = 1.0):
        self.max_requests = max_requests
        self.time_window = time_window
        self.state_file = Path("/tmp/pubmed_rate_limiter.json")

    async def acquire(self):
        # Use asyncio's run_in_executor for file operations
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._acquire_sync)

    def _acquire_sync(self):
        # Create file if it doesn't exist
        if not self.state_file.exists():
            self.state_file.write_text(json.dumps({"requests": []}))

        # Acquire exclusive lock
        with open(self.state_file, "r+") as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            try:
                data = json.load(f)
                current_time = time.time()

                # Clean old requests
                data["requests"] = [
                    req
                    for req in data["requests"]
                    if current_time - req < self.time_window
                ]

                # Check if we need to wait
                if len(data["requests"]) >= self.max_requests:
                    oldest = data["requests"][0]
                    wait_time = self.time_window - (current_time - oldest)
                    if wait_time > 0:
                        time.sleep(wait_time)
                        current_time = time.time()
                        data["requests"] = [
                            req
                            for req in data["requests"]
                            if current_time - req < self.time_window
                        ]

                # Add current request
                data["requests"].append(current_time)

                # Write back
                f.seek(0)
                json.dump(data, f)
                f.truncate()
            finally:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)


class SearchPubmedAbstractsRequest(BaseModel):
    term: str = Field(
        ...,
        description="""Entrez text query. All special characters must be URL encoded. 
        Spaces may be replaced by '+' signs. For very long queries (more than several 
        hundred characters), consider using an HTTP POST call. See PubMed or Entrez 
        help for information about search field descriptions and tags. Search fields 
        and tags are database specific.""",
    )

    retmax: Optional[int] = Field(
        10,
        description="""Number of UIDs to return (default=10, max=100).""",
    )

    sort: Optional[str] = Field(
        None,
        description="""Sort method for results. PubMed values:
        - pub_date: descending sort by publication date
        - Author: ascending sort by first author
        - JournalName: ascending sort by journal name
        - relevance: default sort order ("Best Match")""",
    )
    field: Optional[str] = Field(
        None,
        description="""Search field to limit entire search. Equivalent to adding [field] 
        to term.""",
    )
    datetype: Optional[Literal["mdat", "pdat", "edat"]] = Field(
        None,
        description="""Type of date used to limit search:
        - mdat: modification date
        - pdat: publication date
        - edat: Entrez date
        Generally databases have only two allowed values.""",
    )
    reldate: Optional[int] = Field(
        None,
        description="""When set to n, returns items with datetype within the last n 
        days.""",
    )
    mindate: Optional[str] = Field(
        None,
        description="""Start date for date range. Format: YYYY/MM/DD, YYYY/MM, or YYYY. 
        Must be used with maxdate.""",
    )
    maxdate: Optional[str] = Field(
        None,
        description="""End date for date range. Format: YYYY/MM/DD, YYYY/MM, or YYYY. 
        Must be used with mindate.""",
    )


pubmed_rate_limiter = FileBasedRateLimiter(max_requests=10, time_window=1.0)


async def search_pubmed_abstracts_async(request: SearchPubmedAbstractsRequest) -> str:
    """Helper function to search PubMed abstracts asynchronously."""
    max_retries = 3
    base_delay = 1.0

    for attempt in range(max_retries):
        try:
            async with pubmedclient_client() as client:
                await pubmed_rate_limiter.acquire()

                request_params = request.model_dump()
                try:
                    request_params["api_key"] = os.environ["NCBI_API_KEY"]
                except KeyError:
                    print(
                        "NCBI_API_KEY isn't set! Current value is {os.environ.get['NCBI_API_KEY']}"
                    )
                search_request = ESearchRequest(db=Db.PUBMED, **request_params)

                search_response = await esearch(client, search_request)
                ids = search_response.esearchresult.idlist

                if ids:
                    await pubmed_rate_limiter.acquire()

                    fetch_request = EFetchRequest(
                        db=Db.PUBMED,
                        id=",".join(ids),
                        retmode="text",
                        rettype="abstract",
                    )
                    fetch_response = await efetch(client, fetch_request)
                    return fetch_response
                else:
                    return "No results found for the given search terms."
        except Exception as e:
            if "429" in str(e) and attempt < max_retries - 1:
                # Exponential backoff
                delay = base_delay * (2**attempt)
                await asyncio.sleep(delay)
                continue
            raise


def search_pubmed_abstracts(request: SearchPubmedAbstractsRequest) -> str:
    """Search abstracts on PubMed database based on the request parameters.

    Returns a list of strings containing:

    * the title of the article
    * the abstract content
    * the authors
    * the journal name
    * the publication date
    * the DOI
    * the PMID
    """
    coro = search_pubmed_abstracts_async(request)

    try:  # ← are we already inside an event loop?
        asyncio.get_running_loop()
    except RuntimeError:  # no loop → just run it normally
        return asyncio.run(coro)

    # we’re in a loop → off-load to a fresh thread so we can block safely
    with concurrent.futures.ThreadPoolExecutor(1) as pool:
        return pool.submit(asyncio.run, coro).result()
