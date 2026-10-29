from langchain.tools import tool
import os
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from tavily import TavilyClient

from url_safety import validate_public_http_url

load_dotenv()

tavily = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))
MAX_REDIRECTS = 3


@tool
def web_search(query: str) -> str:
    """Search the web for recent and reliable information on a topic. Returns titles, URLs and snippets."""
    # Defaults match the original behaviour; the app's advanced options change them per run.
    max_results = int(os.getenv("SEARCH_MAX_RESULTS", "5"))
    depth = os.getenv("SEARCH_DEPTH", "basic")
    results = tavily.search(query=query, max_results=max_results, search_depth=depth)

    out = []
    for result in results["results"]:
        out.append(
            f"Title: {result['title']}\nURL: {result['url']}\nSnippet: {result['content'][:300]}\n"
        )
    return "\n----\n".join(out)


@tool
def scrape_url(url: str) -> str:
    """Scrape public HTTP(S) pages only; private-network destinations and unsafe redirects are rejected."""
    try:
        current_url = validate_public_http_url(url)
        response = None
        for redirect_count in range(MAX_REDIRECTS + 1):
            response = requests.get(
                current_url,
                timeout=8,
                headers={"User-Agent": "Mozilla/5.0"},
                allow_redirects=False,
            )
            if response.status_code not in (301, 302, 303, 307, 308):
                break
            location = response.headers.get("Location")
            response.close()
            if not location:
                raise ValueError("The page returned a redirect without a destination.")
            if redirect_count == MAX_REDIRECTS:
                raise ValueError("The page redirected too many times.")
            current_url = validate_public_http_url(urljoin(current_url, location))

        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        for tag in soup(["script", "style", "nav", "footer"]):
            tag.decompose()
        return soup.get_text(separator=" ", strip=True)[:3000]
    except Exception as exc:  # noqa: BLE001 - returned as a tool result for the agent
        return f"Could not scrape URL: {type(exc).__name__}: {exc}"
