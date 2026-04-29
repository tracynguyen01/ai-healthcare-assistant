import json
from src.chunking import chunk_documents


def main():
    with open("data/processed/documents.json", "r", encoding="utf-8") as f:
        documents = json.load(f)

    chunks = chunk_documents(documents)

    print(f"Total documents: {len(documents)}")
    print(f"Total chunks: {len(chunks)}")

    print("\nSample chunk:\n")
    print(chunks[0]["text"][:300])


if __name__ == "__main__":
    main()