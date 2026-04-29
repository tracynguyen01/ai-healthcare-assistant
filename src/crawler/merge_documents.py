import json


def load_json(path: str):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(data, path: str):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def merge_documents(paths: list[str], output_path: str):
    merged = []
    seen = set()

    for path in paths:
        docs = load_json(path)
        for doc in docs:
            key = (doc["title"].strip().lower(), doc["url"].strip().lower())
            if key in seen:
                continue
            seen.add(key)
            merged.append(doc)

    save_json(merged, output_path)
    print(f"Merged {len(merged)} documents into {output_path}")


if __name__ == "__main__":
    merge_documents(
        [
            "data/processed/documents_crawled.json",
            "data/processed/documents_medlineplus.json",
        ],
        "data/processed/documents.json",
    )