import os
from tavily import TavilyClient
from dotenv import load_dotenv

load_dotenv()


def web_search_tool(query: str, max_results: int = 5) -> str:
    """
    Search the internet for current cricket information.
    Returns titles, URLs, and content snippets.
    """

    api_key = os.getenv("TAVILY_API_KEY")

    if not api_key:
        return "Web search is unavailable because TAVILY_API_KEY is missing."

    client = TavilyClient(api_key=api_key)

    response = client.search(
        query=query,
        max_results=max_results,
        search_depth="basic",
        topic="general"
    )

    results = response.get("results", [])

    if not results:
        return "No useful web results were found."

    formatted_results = []

    for i, result in enumerate(results, start=1):
        title = result.get("title", "Untitled")
        url = result.get("url", "")
        content = result.get("content", "")

        formatted_results.append(
            f"[{i}] {title}\n"
            f"URL: {url}\n"
            f"Content: {content}"
        )

    return "\n\n".join(formatted_results)