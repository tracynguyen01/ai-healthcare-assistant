import json
from pathlib import Path
from typing import List, Dict

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer


MODEL_NAME = "BAAI/bge-small-en-v1.5"
model = SentenceTransformer(MODEL_NAME)


def build_embeddings(chunks: List[Dict]) -> np.ndarray:
    """
    Build normalized embeddings for all chunks.
    """
    texts = [chunk["text"] for chunk in chunks]
    vectors = model.encode(
        texts,
        normalize_embeddings=True,
        show_progress_bar=True,
    )
    return np.array(vectors, dtype="float32")


def build_faiss_index(vectors: np.ndarray):
    """
    Use inner product on normalized vectors = cosine similarity.
    """
    dim = vectors.shape[1]
    index = faiss.IndexFlatIP(dim)
    index.add(vectors)
    return index


def save_index(
    index,
    chunks,
    index_path="data/vectorstore/index.faiss",
    meta_path="data/vectorstore/metadata.json",
):
    index_file = Path(index_path)
    meta_file = Path(meta_path)

    if index_file.parent.exists() and not index_file.parent.is_dir():
        raise ValueError(f"{index_file.parent} exists but is not a directory.")

    index_file.parent.mkdir(parents=True, exist_ok=True)

    faiss.write_index(index, str(index_file))

    with open(meta_file, "w", encoding="utf-8") as f:
        json.dump(chunks, f, indent=2, ensure_ascii=False)

    print(f"Saved FAISS index to {index_path}")
    print(f"Saved metadata to {meta_path}")


if __name__ == "__main__":
    from src.chunking import chunk_documents

    with open("data/processed/documents.json", "r", encoding="utf-8") as f:
        docs = json.load(f)

    chunks = chunk_documents(docs)
    print(f"Total documents: {len(docs)}")
    print(f"Total chunks: {len(chunks)}")

    vectors = build_embeddings(chunks)
    print(f"Vector shape: {vectors.shape}")

    index = build_faiss_index(vectors)
    save_index(index, chunks)