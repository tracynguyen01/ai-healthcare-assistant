from src.crawler.fetch import fetch_html
from src.crawler.parse import parse_html


def main():
    url = "https://www.nhs.uk/symptoms/"
    html = fetch_html(url)

    if not html:
        print("Fetch failed")
        return

    result = parse_html(html, url)

    print("\n=== TITLE ===")
    print(result["title"])

    print("\n=== TEXT SAMPLE ===")
    print(result["text"][:500])

    print("\n=== NUMBER OF LINKS ===")
    print(len(result["links"]))

    print("\n=== SAMPLE LINKS ===")
    for link in result["links"][:5]:
        print(link)


if __name__ == "__main__":
    main()
