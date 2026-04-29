from src.query_planner import plan_query
from src.internal_retrieve import internal_search
from src.external_retrieve import external_search


STOPWORDS = {
    "what", "is", "are", "the", "a", "an", "of", "for", "to", "and", "in",
    "my", "i", "have", "am", "between", "different", "difference", "compare",
    "vs", "versus",
}


SYMPTOM_OR_PAIN_TERMS = {
    "pain",
    "ache",
    "aching",
    "symptom",
    "symptoms",
    "injury",
    "injuries",
    "sprain",
    "sprains",
    "strain",
    "strains",
    "sore",
    "soreness",
    "treatment",
    "self-care",
    "price therapy",
    "rest",
    "ice",
    "medical attention",
}


def deduplicate_docs(docs: list[dict]) -> list[dict]:
    seen = set()
    deduped = []

    for doc in docs:
        key = (
            doc.get("title", "").strip().lower(),
            doc.get("url", "").strip().lower(),
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(doc)

    return deduped


def simple_singularize(word: str) -> str:
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


def topical_match_score(query: str, doc: dict) -> float:
    q_words = normalize_words(query)
    title_words = normalize_words(doc.get("title", ""))
    text_words = normalize_words(doc.get("text", "")[:600])

    title_overlap = len(q_words & title_words)
    text_overlap = len(q_words & text_words)

    return 0.60 * title_overlap + 0.10 * text_overlap


def is_symptom_or_pain_biased(doc: dict) -> bool:
    title = doc.get("title", "").lower()
    text = doc.get("text", "").lower()[:1000]
    combined = f"{title} {text}"

    if any(term in title for term in SYMPTOM_OR_PAIN_TERMS):
        return True

    count = sum(term in combined for term in SYMPTOM_OR_PAIN_TERMS)
    return count >= 2


def detect_internal_mismatch(query: str, docs: list[dict]) -> dict:
    if not docs:
        return {
            "use_external": True,
            "reason": "No internal documents retrieved.",
        }

    top_doc = docs[0]
    top_score = top_doc.get("final_score", 0.0)
    top_title_match = top_doc.get("title_match", False)
    top_hub_like = top_doc.get("is_hub_like", False)

    strong_docs = [d for d in docs if d.get("final_score", 0.0) >= 0.75]
    title_matches = [d for d in docs if d.get("title_match", False)]
    hub_docs = [d for d in docs if d.get("is_hub_like", False)]

    reasons = []

    if top_score < 0.55:
        reasons.append(f"Top internal score too low ({top_score:.3f}).")

    if not top_title_match:
        reasons.append("Top internal title does not match query terms.")

    if top_hub_like:
        reasons.append("Top internal result looks like a hub page.")

    if len(strong_docs) == 0:
        reasons.append("No strong internal documents found.")

    if len(title_matches) == 0:
        reasons.append("No internal documents with title-level keyword match.")

    if len(hub_docs) >= 2:
        reasons.append("Too many hub-like internal results.")

    use_external = len(reasons) > 0

    if not reasons:
        reasons.append("Internal retrieval looks strong enough.")

    return {
        "use_external": use_external,
        "reason": " ".join(reasons),
    }


def rerank_merged_docs(query: str, docs: list[dict]) -> list[dict]:
    for d in docs:
        topic_score = topical_match_score(query, d)
        d["topic_score"] = topic_score
        d["rerank_score"] = d.get("final_score", 0.0) + 0.35 * topic_score

    docs.sort(key=lambda x: x.get("rerank_score", 0.0), reverse=True)
    return docs


def filter_relevant_docs(docs: list[dict]) -> list[dict]:
    filtered = []

    for d in docs:
        topic_score = d.get("topic_score", 0.0)
        title_match = d.get("title_match", False)

        if topic_score > 0 or title_match:
            filtered.append(d)

    return filtered


def intent_filter_docs(plan: dict, docs: list[dict]) -> list[dict]:
    """
    Intent-aware hard filter.
    For normal concept comparison, remove symptom/pain/treatment-biased docs.
    """
    if plan.get("intent") != "comparison":
        return docs

    return [
        d for d in docs
        if not is_symptom_or_pain_biased(d)
    ]


def hybrid_retrieve(query: str, top_k: int = 5) -> dict:
    plan = plan_query(query)

    # -------- Internal retrieval --------
    all_internal = []
    for rq in plan.get("rewrite_queries", [query]):
        all_internal.extend(internal_search(rq, top_k=top_k))

    all_internal.sort(key=lambda x: x.get("final_score", 0.0), reverse=True)
    all_internal = deduplicate_docs(all_internal)
    all_internal = intent_filter_docs(plan, all_internal)

    inspect_n = max(top_k, 6)
    mismatch = detect_internal_mismatch(query, all_internal[:inspect_n])

    should_try_external = plan.get("need_external_search", False) or mismatch["use_external"]

    # If comparison internal docs are fully filtered out, definitely try external.
    if plan.get("intent") == "comparison" and len(all_internal) == 0:
        should_try_external = True

    # -------- External retrieval --------
    all_external = []
    if should_try_external:
        for rq in plan.get("rewrite_queries", [query]):
            all_external.extend(
                external_search(
                    query=rq,
                    preferred_sources=plan.get(
                        "preferred_sources",
                        ["nhs", "healthdirect", "medlineplus"],
                    ),
                    max_docs=3,
                )
            )

    all_external = deduplicate_docs(all_external)
    all_external = intent_filter_docs(plan, all_external)

    used_external = len(all_external) > 0

    # -------- Merge + rerank --------
    merged = deduplicate_docs(all_internal[:top_k] + all_external)
    merged = rerank_merged_docs(query, merged)
    merged = intent_filter_docs(plan, merged)

    # Keep topical docs, but do not fallback to pain-biased docs for comparison.
    merged = filter_relevant_docs(merged)

    final_docs = merged[:top_k]

    return {
        "query": query,
        "plan": plan,
        "mismatch_check": mismatch,
        "used_external": used_external,
        "attempted_external": should_try_external,
        "internal_docs": all_internal[:top_k],
        "external_docs": all_external,
        "final_docs": final_docs,
    }


if __name__ == "__main__":
    tests = [
        "what is diferent between muscle and joint?",
        "what is different between nasal spray and nose spray?",
        "difference between headache and migraine",
        "does itchy eyes cause tired eyes?",
    ]

    for q in tests:
        print("\nQUERY:", q)
        result = hybrid_retrieve(q, top_k=5)
        print("PLAN:", result["plan"])
        print("USED EXTERNAL:", result["used_external"])
        print("FINAL DOCS:")
        for d in result["final_docs"]:
            print("-", d.get("title"), "|", d.get("retrieval_source"), "|", d.get("url"))