import requests
from bs4 import BeautifulSoup
from urllib.parse import quote_plus


HEADERS = {
    "User-Agent": "Mozilla/5.0"
}

TRUSTED_SEARCH_SITES = [
    "site:healthdirect.gov.au",
    "site:nhs.uk",
    "site:cdc.gov",
    "site:medlineplus.gov",
]


def build_search_queries(query: str) -> list[str]:
    return [f"{site} {query}" for site in TRUSTED_SEARCH_SITES]


def infer_source_name(url: str) -> str:
    url_l = url.lower()
    if "nhs.uk" in url_l:
        return "nhs"
    if "healthdirect.gov.au" in url_l:
        return "healthdirect"
    if "cdc.gov" in url_l:
        return "cdc"
    if "medlineplus.gov" in url_l:
        return "medlineplus"
    return "external"


def infer_trust_weight(source_name: str) -> float:
    return {
        "healthdirect": 1.0,
        "nhs": 0.95,
        "medlineplus": 0.95,
        "cdc": 0.9,
    }.get(source_name, 0.75)


def duckduckgo_search(query: str, max_results: int = 3) -> list[str]:
    """
    Lightweight search using DuckDuckGo HTML results.
    """
    url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"

    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
        response.raise_for_status()
    except Exception:
        return []

    soup = BeautifulSoup(response.text, "lxml")
    links = []

    for a in soup.select("a.result__a"):
        href = a.get("href")
        if href and href.startswith("http"):
            links.append(href)
        if len(links) >= max_results:
            break

    return links


def fetch_page(url: str):
    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
        response.raise_for_status()
    except Exception:
        return None

    soup = BeautifulSoup(response.text, "lxml")

    title = soup.title.string.strip() if soup.title and soup.title.string else "External source"

    main = soup.find("main")
    paragraphs = main.find_all("p") if main else soup.find_all("p")

    texts = []
    for p in paragraphs:
        text = p.get_text(" ", strip=True)
        if text:
            texts.append(text)

    full_text = " ".join(texts)

    if len(full_text) < 200:
        return None

    return {
        "title": title,
        "text": full_text[:3000],
        "url": url,
    }


def external_fallback_search(query: str, max_docs: int = 3) -> list[dict]:
    """
    Search trusted domains and fetch a few useful external docs.
    """
    all_links = []

    for q in build_search_queries(query):
        links = duckduckgo_search(q, max_results=2)
        all_links.extend(links)

    seen = set()
    unique_links = []
    for link in all_links:
        if link not in seen:
            seen.add(link)
            unique_links.append(link)

    docs = []
    for i, url in enumerate(unique_links[: max_docs * 2], start=1):
        page = fetch_page(url)
        if not page:
            continue

        source_name = infer_source_name(url)
        trust_weight = infer_trust_weight(source_name)

        docs.append(
            {
                "chunk_id": f"external_{i}",
                "doc_id": f"external_{i}",
                "title": page["title"],
                "source": source_name,
                "source_name": source_name,
                "url": page["url"],
                "text": page["text"],
                "score": 0.0,
                "final_score": trust_weight,
                "trust_weight": trust_weight,
                "retrieval_source": "external",
            }
        )

    return docs[:max_docs]