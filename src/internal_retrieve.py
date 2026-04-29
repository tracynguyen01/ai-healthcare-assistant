import json
import faiss
import numpy as np
import streamlit as st
from sentence_transformers import SentenceTransformer

MODEL_NAME = "BAAI/bge-small-en-v1.5"

STOPWORDS = {
    "what", "is", "are", "the", "a", "an", "of", "for", "to", "and", "in"
}


@st.cache_resource
def load_embedding_model():
    return SentenceTransformer(MODEL_NAME)


@st.cache_resource
def load_index(index_path="data/vectorstore/index.faiss"):
    return faiss.read_index(index_path)


@st.cache_data
def load_metadata(meta_path="data/vectorstore/metadata.json"):
    with open(meta_path, "r", encoding="utf-8") as f:
        return json.load(f)


def embed_query(text: str):
    model = load_embedding_model()
    vec = model.encode(
        [text],
        normalize_embeddings=True,
        show_progress_bar=False,
    )
    return np.array(vec, dtype="float32")


def simple_singularize(word: str) -> str:
    """
    Very lightweight singularization for retrieval matching.
    Good enough for cases like headache <-> headaches.
    """
    if len(word) > 4 and word.endswith("ies"):
        return word[:-3] + "y"
    if len(word) > 3 and word.endswith("es"):
        return word[:-2]
    if len(word) > 3 and word.endswith("s"):
        return word[:-1]
    return word


def normalize_words(text: str) -> set[str]:
    cleaned = (
        text.lower()
        .replace("?", "")
        .replace(",", " ")
        .replace(".", " ")
        .replace(":", " ")
        .replace(";", " ")
        .replace("/", " ")
        .replace("-", " ")
        .replace("(", " ")
        .replace(")", " ")
    )

    words = []
    for w in cleaned.split():
        if w in STOPWORDS:
            continue
        words.append(simple_singularize(w))

    return set(words)


def keyword_overlap_score(query: str, title: str, text: str) -> float:
    q_words = normalize_words(query)
    title_words = normalize_words(title)
    text_words = normalize_words(text[:600])

    title_overlap = len(q_words & title_words)
    text_overlap = len(q_words & text_words)

    return 0.35 * title_overlap + 0.05 * text_overlap


def exact_title_match(query: str, title: str) -> bool:
    q_words = normalize_words(query)
    title_words = normalize_words(title)
    return len(q_words & title_words) >= 1


def is_hub_like(doc: dict) -> bool:
    title = doc.get("title", "").lower().strip()
    url = doc.get("url", "").lower().strip()

    bad_titles = {
        "symptoms a to z - nhs",
        "conditions a to z - nhs",
        "health a to z - nhs",
        "symptoms a to z",
        "conditions a to z",
        "health a to z",
        "health topics",
    }

    bad_exact_urls = {
        "https://www.nhs.uk/symptoms/",
        "https://www.nhs.uk/conditions/",
        "https://www.nhs.uk/health-a-to-z/",
        "https://www.healthdirect.gov.au/health-topics",
        "https://www.healthdirect.gov.au/health-topics/symptoms",
    }

    if title in bad_titles:
        return True
    if url in bad_exact_urls:
        return True
    return False


def internal_search(query: str, top_k: int = 5):
    index = load_index()
    metadata = load_metadata()

    query_vec = embed_query(query)
    scores, indices = index.search(query_vec, top_k * 8)

    seen_docs = set()
    reranked = []

    for rank, i in enumerate(indices[0]):
        if i == -1:
            continue

        item = metadata[i]
        if item["doc_id"] in seen_docs:
            continue
        seen_docs.add(item["doc_id"])

        similarity = float(scores[0][rank])
        trust_weight = float(item.get("trust_weight", 0.8))
        keyword_score = keyword_overlap_score(query, item["title"], item["text"])

        hub_penalty = -0.25 if is_hub_like(item) else 0.0

        final_score = (
            0.60 * similarity
            + 0.20 * trust_weight
            + 0.20 * keyword_score
            + hub_penalty
        )

        result = item.copy()
        result["score"] = similarity
        result["keyword_score"] = keyword_score
        result["final_score"] = final_score
        result["title_match"] = exact_title_match(query, item["title"])
        result["is_hub_like"] = is_hub_like(item)
        result["retrieval_source"] = "internal"
        reranked.append(result)

    reranked.sort(key=lambda x: x["final_score"], reverse=True)
    return reranked[:top_k]


if __name__ == "__main__":
    results = internal_search("what is headache?", top_k=5)
    for r in results:
        print("\n---")
        print(r["title"])
        print("score:", r["score"])
        print("keyword_score:", r["keyword_score"])
        print("final_score:", r["final_score"])
        print("title_match:", r["title_match"])
        print("hub_like:", r["is_hub_like"])