from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse


def infer_content_type(url: str) -> str:
    url = url.lower()

    if "/symptom" in url or "/signs-symptoms" in url or "/feelings-symptoms" in url:
        return "symptom_guidance"
    if "/conditions/" in url:
        return "condition_overview"
    if "/health-topics" in url or "/health-a-to-z/" in url:
        return "health_topic"
    return "general_health"


def extract_main_text(soup: BeautifulSoup) -> str:
    main = soup.find("main")

    if main:
        paragraphs = main.find_all("p")
    else:
        paragraphs = soup.find_all("p")

    texts = []
    for p in paragraphs:
        text = p.get_text(" ", strip=True)
        if text:
            texts.append(text)

    return " ".join(texts)


def extract_internal_links(soup: BeautifulSoup, base_url: str) -> list[str]:
    links = set()
    base_domain = urlparse(base_url).netloc

    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if not href:
            continue

        full_url = urljoin(base_url, href)
        parsed = urlparse(full_url)

        if parsed.scheme in {"http", "https"} and parsed.netloc == base_domain:
            clean_url = parsed._replace(fragment="", query="").geturl()
            links.add(clean_url)

    return list(links)


def parse_html(html: str, base_url: str) -> dict:
    soup = BeautifulSoup(html, "lxml")

    if soup.title and soup.title.string:
        title = soup.title.string.strip()
    else:
        title = "No Title"

    text = extract_main_text(soup)
    links = extract_internal_links(soup, base_url)

    return {
        "url": base_url,
        "title": title,
        "text": text,
        "links": links,
        "content_type": infer_content_type(base_url),
    }