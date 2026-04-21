from src.crawler.fetch import fetch_html


def main():
    url = "https://www.nhs.uk/symptoms/"
    html = fetch_html(url)

    if html:
        print("Fetch successful!")
        print(f"HTML length: {len(html)}")
        print("\nFirst 500 characters:\n")
        print(html[:500])
    else:
        print("Fetch failed.")


if __name__ == "__main__":
    main()
