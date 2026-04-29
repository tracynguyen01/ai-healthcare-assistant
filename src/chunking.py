from typing import List, Dict


def chunk_text(text: str, chunk_size: int = 800, overlap: int = 100) -> List[str]:
    """
    Split text into overlapping character-based chunks.
    """
    chunks = []
    start = 0
    text_length = len(text)

    while start < text_length:
        end = start + chunk_size
        chunk = text[start:end].strip()

        if chunk:
            chunks.append(chunk)

        start += chunk_size - overlap

    return chunks


def chunk_documents(documents: List[Dict]) -> List[Dict]:
    """
    Convert documents into chunk-level records.
    """
    chunked_data = []

    for doc in documents:
        text = doc["text"]
        chunks = chunk_text(text)

        for i, chunk in enumerate(chunks):
            chunked_data.append(
                {
                    "chunk_id": f"{doc['id']}_chunk_{i}",
                    "doc_id": doc["id"],
                    "title": doc["title"],
                    "source": doc["source"],
                    "url": doc["url"],
                    "text": chunk,
                }
            )

    return chunked_data