#!/usr/bin/env python3
"""
Search Tools - Refactored with focused outputs and natural language summaries
"""

import os
import asyncio

from tavily import TavilyClient
from pubmedclient.models import Db, EFetchRequest, ESearchRequest
from pubmedclient.sdk import efetch, esearch, pubmedclient_client

from agentic_system.tools.tool_utils import (
    FileBasedRateLimiter,
    tool_cache,
    ai_summarized_output,
)


# ============================= Web Search =============================

# Initialize Tavily client
api_key = os.environ.get("TAVILY_API_KEY")
tavily_client = TavilyClient(api_key=api_key)
tavily_cache_name = "tavily"


@tool_cache(tavily_cache_name)
def search_web(query: str, max_results: int = 5) -> str:
    """Search the web for information on a given query.

    Args:
        query (str): The search string used to query the web, such as a topic, question, or keyword.
        max_results (int, optional): Maximum number of search results to return (1-10). Defaults to 5.

    Returns:
        str: Natural language summary of search results including AI-generated overview and detailed results.
    """
    response = tavily_client.search(
        query,
        max_results=max_results,
        search_depth="basic",
        include_answer=True,
        include_raw_content=False,
        include_images=False,
    )

    results = response.get("results", [])

    if not results:
        return f"No web search results found for '{query}'"

    # Build natural language summary
    summary_parts = [f"Web search results for '{query}':"]

    # The agent seems to rely on this overview too much
    # answer = response.get("answer", "")
    # summary_parts.append(f"\nAI-generated overview: {answer}\n")

    for i, result in enumerate(results[:max_results], 1):
        title = result.get("title", "No title")
        content = result.get("content", "No content available")
        url = result.get("url", "No URL available")
        score = result.get("score", "No score available")

        summary_parts.append(f"\n{i}. {title} | ")
        summary_parts.append(f"URL: {url} | ")
        summary_parts.append(f"Relevance Score: {score} | ")
        summary_parts.append(f"Content: {content}\n")

    return "\n".join(summary_parts)


@tool_cache(tavily_cache_name)
def extract_web(urls: list[str]) -> str:
    """Extract raw content from a list of URLs.

    Args:
        urls (list[str]): List of URLs to extract content from.

    Returns:
        str: Natural language summary of extracted content from each URL.
    """
    response = tavily_client.extract(urls)

    # Build natural language summary
    summary_parts = [f"Extract web results for '{urls}':\n"]

    results = response.get("results", [])
    for i, result in enumerate(results, 1):
        summary_parts.append(f"{i}. URL: {result.get('url', 'No URL')}")
        summary_parts.append(f"Content: {result.get('raw_content', 'No raw content')}")

    summary_parts.append("\nFailed Results:")
    failed_results = response.get("failed_results", [])
    for i, result in enumerate(failed_results, 1):
        summary_parts.append(f"{i}. URL: {result.get('url', 'No URL')}")

    return "\n".join(summary_parts)


# ============================= PubMed Search =============================

# Initialize rate limiter - PubMed is very strict, and we make 2 API calls per search
pubmed_rate_limiter = FileBasedRateLimiter(
    max_requests=1, time_window=1.0, name="pubmed"
)
pubmed_cache_name = "pubmed"


@tool_cache(pubmed_cache_name)
def search_pubmed_abstracts(
    term: str,
    retmax: int = 5,
    sort: str = "relevance",
    mindate: str = None,
    maxdate: str = None,
) -> str:
    """Search PubMed for scientific articles and return formatted abstracts with key metadata.

    Args:
        term (str): Search query for PubMed. Can include field tags like [MeSH Terms], [Title/Abstract], [Author], etc. Boolean operators (AND, OR, NOT) are supported.
        retmax (int, optional): Number of articles to return (default=5, max=10). Defaults to 5.
        sort (str, optional): Sort method: relevance (default), pub_date (newest first), Author, or JournalName. Defaults to "relevance".
        mindate (str, optional): Start date for publication date filter (YYYY/MM/DD or YYYY). Defaults to None.
        maxdate (str, optional): End date for publication date filter (YYYY/MM/DD or YYYY). Defaults to None.

    Returns:
        str: Readable summary including title, authors, journal, PMID, and abstract excerpt for each article found.
    """

    # If not in cache, make the API call
    result = _fetch_pubmed_data(term, retmax, sort, mindate, maxdate)

    return _format_pubmed_abstracts(result)


@tool_cache(pubmed_cache_name)
def _fetch_pubmed_data(
    term: str,
    retmax: int = 5,
    sort: str = "relevance",
    mindate: str = None,
    maxdate: str = None,
) -> str:
    """Internal function to fetch PubMed data without caching logic."""

    # Apply rate limiting BEFORE starting any API work
    pubmed_rate_limiter.acquire_sync()

    async def _async_fetch():
        async with pubmedclient_client() as client:
            # Build search request
            search_params = {
                "term": term,
                "retmax": retmax,
                "sort": sort,
                "mindate": mindate,
                "maxdate": maxdate,
            }

            # Add API key if available
            try:
                search_params["api_key"] = os.environ["NCBI_API_KEY"]
            except KeyError:
                print(
                    f"NCBI_API_KEY isn't set! Current value is {os.environ.get('NCBI_API_KEY')}"
                )

            search_request = ESearchRequest(db=Db.PUBMED, **search_params)
            search_response = await esearch(client, search_request)
            ids = search_response.esearchresult.idlist

            if not ids:
                return "No results found for the given search terms."

            # Rate limit between the two API calls within this request
            pubmed_rate_limiter.acquire_sync()

            fetch_request = EFetchRequest(
                db=Db.PUBMED,
                id=",".join(ids),
                retmode="text",
                rettype="abstract",
            )
            fetch_response = await efetch(client, fetch_request)
            return fetch_response

    return asyncio.run(_async_fetch())


def _format_pubmed_abstracts(raw_text: str) -> str:
    """Format raw PubMed abstract text into a readable summary, excluding author information and conflict of interest statements."""

    text_blocks = raw_text.split("\n\n")

    for text_block in text_blocks:
        if text_block.startswith("Author information"):
            text_blocks.remove(text_block)
        if text_block.startswith("Conflict of interest statement:"):
            text_blocks.remove(text_block)
        if "©" in text_block:
            text_blocks.remove(text_block)

    return "\n\n".join(text_blocks)


SEARCH_TOOLS = [search_web, extract_web, search_pubmed_abstracts]

for i, fn in enumerate(SEARCH_TOOLS):
    wrapped = ai_summarized_output(fn)
    wrapped.__name__ = "SEARCH__" + wrapped.__name__
    SEARCH_TOOLS[i] = wrapped

if __name__ == "__main__":
    import dotenv

    dotenv.load_dotenv("../../../.env")

    # Test web search
    web_summary = search_web(query="Cardiac fibrosis treatments", max_results=3)
    print(web_summary)

    # print("\n" + "=" * 80 + "\n")

    # # Test extract web
    # urls = [
    #     "https://en.wikipedia.org/wiki/Cardiac_fibrosis",
    #     "https://www.ncbi.nlm.nih.gov/pmc/articles/PMC7924040/",
    # ]
    # extracted = extract_web(urls=urls)
    # print(extracted)

    # print("\n" + "=" * 80 + "\n")

    # # # Test PubMed search
    # pubmed_summary = search_pubmed_abstracts(
    #     term="Luminespib AND (cardiac fibrosis OR myocardial fibrosis)",
    #     retmax=3,
    #     sort="relevance",
    # )
    # print(pubmed_summary)
