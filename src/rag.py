from src.safety import detect_risk
from src.hybrid_retrieve import hybrid_retrieve
from src.agentic_rag import agentic_answer, generate_answer_once, normalize_sections


FAST_INTENTS = {"definition", "comparison", "symptom_explanation"}


def ask_rag(query: str, top_k: int = 3) -> dict:
    retrieval_result = hybrid_retrieve(query, top_k=top_k)
    intent = retrieval_result["plan"].get("intent", "unknown")
    risk = detect_risk(query)

    if intent in FAST_INTENTS and risk != "high":
        docs = retrieval_result["final_docs"]
        parsed, raw_answer = generate_answer_once(query, docs, intent)

        return {
            "query": query,
            "answer": raw_answer,
            "structured_answer": parsed,
            "sections": normalize_sections(parsed),
            "sources": docs,
            "risk": risk,
            "used_fallback": retrieval_result.get("used_external", False),
            "retrieval_plan": retrieval_result.get("plan", {}),
            "mismatch_check": retrieval_result.get("mismatch_check", {}),
            "used_second_pass": False,
        }

    result = agentic_answer(query, top_k=top_k)

    return {
        "query": query,
        "answer": result.get("raw_answer", ""),
        "structured_answer": result.get("structured_answer", {}),
        "sections": result.get("sections", {}),
        "sources": result.get("sources", []),
        "risk": risk,
        "used_fallback": result.get("used_external", False),
        "retrieval_plan": result.get("retrieval_plan", {}),
        "mismatch_check": result.get("mismatch_check", {}),
        "critic": result.get("critic", {}),
        "used_second_pass": result.get("used_second_pass", False),
    }