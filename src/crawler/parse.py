from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse


def parse_html(html: str, base_url: str):
    """
    Parse HTML to extract:
    - title
    - main text
    - internal links
    """

    soup = BeautifulSoup(html, "lxml")

    # 1. Title
    title = soup.title.string.strip() if soup.title else "No Title"

    # 2. Main text (simple version first)
    paragraphs = soup.find_all("p")
    text = " ".join([p.get_text(strip=True) for p in paragraphs])

    # 3. Extract internal links
    links = set()
    base_domain = urlparse(base_url).netloc

    for a in soup.find_all("a", href=True):
        href = a["href"]
        full_url = urljoin(base_url, href)

        parsed = urlparse(full_url)

        # keep only same domain
        if parsed.netloc == base_domain:
            links.add(full_url)

    return {
        "title": title,
        "text": text,
        "links": list(links)
    }
