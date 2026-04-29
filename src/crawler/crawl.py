import json
import time
from collections import deque
from pathlib import Path
from urllib.parse import urlparse

from src.crawler.fetch import fetch_html
from src.crawler.parse import parse_html
from src.crawler.domain_rules import DOMAIN_RULES


MAX_PAGES = 60
DELAY_SECONDS = 1


DISALLOWED_EXTENSIONS = (
    ".pdf", ".jpg", ".jpeg", ".png", ".gif", ".svg",
    ".doc", ".docx", ".xls", ".xlsx", ".zip"
)


def load_seed_urls(path: str) -> list[dict]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def get_domain_rule(url: str):
    domain = urlparse(url).netloc
    return DOMAIN_RULES.get(domain)


def is_allowed_url(url: str) -> bool:
    parsed = urlparse(url)
    path = parsed.path.lower()

    rule = get_domain_rule(url)
    if rule is None:
        return False

    if path.endswith(DISALLOWED_EXTENSIONS):
        return False

    if any(blocked in path for blocked in rule["blocked_path_keywords"]):
        return False

    if not any(keyword in path for keyword in rule["allowed_path_keywords"]):
        return False

    return True


def is_useful_document(doc: dict) -> bool:
    text = doc.get("text", "").strip()
    title = doc.get("title", "").strip()

    if len(text) < 250:
        return False

    if len(title) < 3:
        return False

    # simple anti-hub / anti-noise checks
    bad_phrases = [
        "back to top",
        "select another one",
        "sorry, there is no symptom information",
    ]
    lower_text = text.lower()
    if any(p in lower_text for p in bad_phrases):
        return False

    return True


def save_documents(documents: list[dict], output_path: str) -> None:
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(documents, f, indent=2, ensure_ascii=False)

    print(f"\nSaved {len(documents)} documents to {output_path}")


def crawl(seed_file: str, output_file: str, max_pages: int = MAX_PAGES) -> list[dict]:
    seeds = load_seed_urls(seed_file)

    if not seeds:
        print("No seed URLs found.")
        return []

    queue = deque()
    visited = set()
    documents = []

    for item in seeds:
        queue.append((item["source"], item["url"]))

    while queue and len(documents) < max_pages:
        source, current_url = queue.popleft()

        if current_url in visited:
            continue

        visited.add(current_url)

        if not is_allowed_url(current_url):
            print(f"[SKIP] Not allowed: {current_url}")
            continue

        print(f"[CRAWL] {current_url}")

        html = fetch_html(current_url)
        if not html:
            print(f"[SKIP] Failed fetch: {current_url}")
            continue

        parsed = parse_html(html, current_url)
        rule = get_domain_rule(current_url)

        parsed["source"] = source
        parsed["source_name"] = rule["source_name"]
        parsed["country"] = rule["country"]
        parsed["trust_weight"] = rule["trust_weight"]

        if is_useful_document(parsed):
            documents.append(
                {
                    "id": f"doc_{len(documents)+1:03d}",
                    "source": parsed["source"],
                    "source_name": parsed["source_name"],
                    "country": parsed["country"],
                    "trust_weight": parsed["trust_weight"],
                    "content_type": parsed["content_type"],
                    "url": parsed["url"],
                    "title": parsed["title"],
                    "text": parsed["text"],
                }
            )
            print(f"[SAVE] {parsed['title']}")
        else:
            print(f"[SKIP] Low-value page: {current_url}")

        for link in parsed["links"]:
            if link not in visited and is_allowed_url(link):
                queue.append((source, link))

        time.sleep(DELAY_SECONDS)

    save_documents(documents, output_file)
    return documents


if __name__ == "__main__":
    crawl(
        seed_file="data/raw/seed_urls.json",
        output_file="data/processed/documents.json",
        max_pages=60,
    )