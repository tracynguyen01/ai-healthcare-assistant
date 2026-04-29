import os
from tavily import TavilyClient

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")

client = TavilyClient(api_key=TAVILY_API_KEY)


def external_search(query: str, preferred_sources=None, max_docs: int = 3) -> list[dict]:
    """
    Use Tavily API instead of DuckDuckGo scraping.
    """

    try:
        response = client.search(
            query=query,
            search_depth="advanced",
            max_results=max_docs,
        )
    except Exception as e:
        print("Tavily search failed:", e)
        return []

    docs = []

    for i, r in enumerate(response.get("results", []), start=1):
        docs.append(
            {
                "chunk_id": f"external_{i}",
                "doc_id": f"external_{i}",
                "title": r.get("title", ""),
                "source": "external",
                "source_name": "external",
                "url": r.get("url", ""),
                "text": r.get("content", ""),  # ⚡ already clean
                "score": 0.0,
                "final_score": 0.0,
                "retrieval_source": "external",
            }
        )

    return docs