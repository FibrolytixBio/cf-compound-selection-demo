#!/usr/bin/env python3
"""
Search Tools - Refactored with focused outputs and natural language summaries
"""

from typing import Optional
import os
import asyncio

from tavily import TavilyClient
from pydantic import BaseModel, Field
from pubmedclient.models import Db, EFetchRequest, ESearchRequest
from pubmedclient.sdk import efetch, esearch, pubmedclient_client

from .tool_utils import FileBasedRateLimiter


# ============================= Web Search =============================


class WebSearchRequest(BaseModel):
    query: str = Field(
        description="The search string used to query the web, such as a topic, question, or keyword."
    )
    max_results: int = Field(
        default=5,
        ge=1,
        le=10,
        description="Maximum number of search results to return (1-10).",
    )


def search_web(request: WebSearchRequest) -> str:
    """Search the web and return a natural language summary of the most relevant results."""
    api_key = os.environ.get("TAVILY_API_KEY")

    if not api_key:
        return "Error: TAVILY_API_KEY environment variable not set"

    tavily_client = TavilyClient(api_key=api_key)
    response = tavily_client.search(
        request.query,
        max_results=request.max_results,
        search_depth="basic",
        include_answer=False,
        include_raw_content=False,
        include_images=False,
    )

    results = response.get("results", [])

    if not results:
        return f"No web search results found for '{request.query}'"

    # Build natural language summary
    summary_parts = [f"Web search results for '{request.query}':"]

    for i, result in enumerate(results[: request.max_results], 1):
        title = result.get("title", "No title")
        snippet = result.get("content", "No content available")
        url = result.get("url", "")

        # Clean up snippet - remove excessive whitespace
        snippet = " ".join(snippet.split())
        if len(snippet) > 200:
            snippet = snippet[:197] + "..."

        # Format as natural language
        summary_parts.append(f"\n{i}. {title}")
        summary_parts.append(f"   {snippet}")
        if url:
            # Show domain for context
            domain = url.split("/")[2] if len(url.split("/")) > 2 else url
            summary_parts.append(f"   Source: {domain}")

    return "\n".join(summary_parts)


# ============================= PubMed Search =============================

# Initialize rate limiter - PubMed is very strict, and we make 2 API calls per search
pubmed_rate_limiter = FileBasedRateLimiter(
    max_requests=1, time_window=1.0, name="pubmed"
)


class SearchPubmedAbstractsRequest(BaseModel):
    term: str = Field(
        ...,
        description="""Search query for PubMed. Can include field tags like [MeSH Terms], 
        [Title/Abstract], [Author], etc. Boolean operators (AND, OR, NOT) are supported.""",
    )
    retmax: Optional[int] = Field(
        5,
        description="""Number of articles to return (default=5, max=10).""",
    )
    sort: Optional[str] = Field(
        "relevance",
        description="""Sort method: relevance (default), pub_date (newest first), 
        Author, or JournalName.""",
    )
    mindate: Optional[str] = Field(
        None,
        description="""Start date for publication date filter (YYYY/MM/DD or YYYY).""",
    )
    maxdate: Optional[str] = Field(
        None,
        description="""End date for publication date filter (YYYY/MM/DD or YYYY).""",
    )


def search_pubmed_abstracts(request: SearchPubmedAbstractsRequest) -> str:
    """Search PubMed for scientific articles and return formatted abstracts with key metadata.

    Returns a readable summary including title, authors, journal, PMID, and abstract excerpt
    for each article found.
    """

    # If not in cache, make the API call
    result = _fetch_pubmed_data(request)

    return _format_pubmed_abstracts(result, request.term)


def _fetch_pubmed_data(request: SearchPubmedAbstractsRequest) -> str:
    """Internal function to fetch PubMed data without caching logic."""

    # Apply rate limiting BEFORE starting any API work
    pubmed_rate_limiter.acquire_sync()

    async def _async_fetch():
        async with pubmedclient_client() as client:
            # Build search request
            search_params = request.model_dump()

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


def _format_pubmed_abstracts(raw_text: str, query: str) -> str:
    """Format raw PubMed abstract text into a readable summary."""
    if not raw_text or not raw_text.strip():
        return f"No abstracts retrieved for '{query}'"

    # Split into individual articles
    articles = raw_text.strip().split("\n\n\n")

    summary_parts = [f"PubMed search results for '{query}' ({len(articles)} articles):"]

    for i, article_text in enumerate(articles, 1):
        lines = article_text.strip().split("\n")

        # Extract key information
        pmid = None
        title = None
        authors = None
        journal = None
        abstract_lines = []
        in_abstract = False

        for line in lines:
            line = line.strip()

            # PMID
            if line.startswith("PMID:"):
                pmid = line.replace("PMID:", "").strip()

            # Title (usually follows a numbered line like "1. ")
            elif i == 1 and line.startswith(f"{i}. "):
                title = line[3:].strip()

            # Authors (contains multiple names with commas)
            elif (
                not authors and line.count(",") > 2 and not line.startswith("Abstract")
            ):
                authors = line

            # Journal info (contains year in parentheses)
            elif (
                not journal
                and "(" in line
                and ")" in line
                and any(year in line for year in ["202", "201", "200"])
            ):
                journal = line

            # Abstract
            elif line.startswith("Abstract") or in_abstract:
                if line.startswith("Abstract"):
                    in_abstract = True
                    continue
                if in_abstract and line:
                    abstract_lines.append(line)

        # Build article summary
        article_parts = [f"\n{i}. {title or 'Title not found'}"]

        if authors:
            # Show first 3 authors
            author_list = authors.split(",")[:3]
            author_str = ", ".join(author_list)
            if len(authors.split(",")) > 3:
                author_str += " et al."
            article_parts.append(f"   Authors: {author_str}")

        if journal:
            article_parts.append(f"   Journal: {journal}")

        if pmid:
            article_parts.append(f"   PMID: {pmid}")

        # Add abstract summary (first 150 words)
        if abstract_lines:
            abstract_text = " ".join(abstract_lines)
            words = abstract_text.split()
            if len(words) > 150:
                abstract_summary = " ".join(words[:150]) + "..."
            else:
                abstract_summary = abstract_text
            article_parts.append(f"   Abstract: {abstract_summary}")

        summary_parts.extend(article_parts)

    return "\n".join(summary_parts)


SEARCH_TOOLS = [search_web, search_pubmed_abstracts]
