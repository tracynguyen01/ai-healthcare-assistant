import json
import os
from dotenv import load_dotenv
from groq import Groq

from src.hybrid_retrieve import hybrid_retrieve
from src.answer_critic import critic_answer
from src.utils.llm_parse import safe_parse


load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise ValueError("Missing GROQ_API_KEY in .env")

client = Groq(api_key=GROQ_API_KEY)

MODEL_NAME = "llama-3.3-70b-versatile"


def format_context(docs: list[dict]) -> str:
    blocks = []

    for i, doc in enumerate(docs, start=1):
        text = doc.get("text", "").strip()
        short_text = text[:800] if len(text) > 800 else text

        block = (
            f"[Source {i}]\n"
            f"Title: {doc.get('title', 'Unknown title')}\n"
            f"Source: {doc.get('source_name', doc.get('source', 'unknown'))}\n"
            f"URL: {doc.get('url', '')}\n"
            f"Content: {short_text}\n"
        )
        blocks.append(block)

    return "\n\n".join(blocks)


def build_intent_instructions(intent: str) -> str:
    if intent == "definition":
        return (
            "This is a definition query.\n"
            "display_answer should use a clear explanation style.\n"
            "Include a short definition, common examples or causes if useful, simple self-care if appropriate, "
            "and when to seek help if relevant.\n"
        )

    if intent == "comparison":
        return (
            "This is a comparison query.\n"
            "The user is asking for the difference between two concepts or terms.\n"
            "For comparison questions, DO NOT discuss pain, symptoms, injury, treatment, self-care, PRICE therapy, rest, ice, or medical attention unless the user explicitly mentions pain or symptoms.\n"
            "display_answer should use clear sections:\n"
            "### First concept\n"
            "### Second concept\n"
            "### Key difference\n"
            "### Example\n"
            "If the two terms mean almost the same thing, clearly say they are similar or interchangeable.\n"
            "If retrieved sources are weak, incomplete, or biased toward symptoms/pain, ignore irrelevant symptom/pain content and answer the conceptual comparison using careful general knowledge.\n"
        )

    if intent == "triage":
        return (
            "This is a triage or action query.\n"
            "display_answer should focus on what the user should do now, urgency, and warning signs.\n"
        )

    if intent == "symptom_explanation":
        return (
            "This is a symptom explanation query.\n"
            "display_answer should explain possible causes, simple safe steps, and when to get medical help.\n"
        )

    return "Answer directly and helpfully.\n"


def build_messages(query: str, docs: list[dict], intent: str) -> list[dict]:
    context = format_context(docs)
    intent_instructions = build_intent_instructions(intent)

    system_prompt = (
        "You are a healthcare information assistant.\n"
        "You are NOT a doctor and must NOT diagnose.\n\n"

        "Answer quality target:\n"
        "- Make the answer feel like a helpful ChatGPT-style explanation.\n"
        "- Explain in simple language.\n"
        "- Include useful examples when appropriate.\n"
        "- For comparison questions, focus only on definitions, roles, functions, similarities, and differences.\n"
        "- For comparison questions, do NOT include self-care advice, treatment advice, urgency advice, or medical attention advice unless the user explicitly asks about symptoms, pain, treatment, or what to do.\n"
        "- For symptom or triage questions, give safe next steps without sounding scary.\n"
        "- For symptom or triage questions, mention urgent warning signs only when relevant.\n\n"

        "Grounding rules:\n"
        "- Use retrieved sources as the PRIMARY grounding.\n"
        "- If retrieved sources are incomplete, you MAY use careful general medical knowledge to complete the answer.\n"
        "- Do NOT say 'not enough information' unless there is absolutely no relevant information.\n"
        "- If sources contain partially irrelevant symptom content, use only the parts relevant to the user's question.\n\n"

        f"{intent_instructions}\n"

        "Return ONLY valid JSON.\n\n"
        "JSON format:\n"
        "{\n"
        '  "display_answer": "...",\n'
        '  "fast_answer": "...",\n'
        '  "possible_concerns": "...",\n'
        '  "urgency": "Low | Medium | High | Unknown",\n'
        '  "suggested_next_step": "...",\n'
        '  "why": "...",\n'
        '  "reasoning": ["step 1 (Source 1)", "step 2 (general medical knowledge)"],\n'
        '  "confidence": 0.0,\n'
        '  "sources_used": ["source title 1", "source title 2"]\n'
        "}\n\n"

        "Rules:\n"
        "- display_answer is the best formatted answer for the UI.\n"
        "- display_answer may use markdown headings and bullet points.\n"
        "- fast_answer is a plain paragraph fallback.\n"
        "- fast_answer should be around 80 to 220 words when useful.\n"
        "- possible_concerns should be a concise one-sentence summary.\n"
        "- urgency must be one of: Low, Medium, High, Unknown.\n"
        "- suggested_next_step should be helpful and practical only when relevant.\n"
        "- why must explain whether the answer used sources, general medical knowledge, or both.\n"
        "- reasoning must be short and evidence-aware.\n"
        "- If using source evidence, cite it as (Source X).\n"
        "- If using general knowledge, label it as (general medical knowledge).\n"
        "- confidence must be between 0.0 and 1.0.\n"
        "- NO extra text outside JSON."
    )

    user_prompt = (
        f"User question:\n{query}\n\n"
        f"Retrieved context:\n{context}\n\n"
        "Answer using retrieved sources as primary grounding. "
        "If sources are incomplete or irrelevant, use careful general medical knowledge to complete a helpful answer."
    )

    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]


def normalize_sections(parsed: dict) -> dict:
    return {
        "Display answer": parsed.get("display_answer", ""),
        "Fast answer": parsed.get("fast_answer", ""),
        "Possible concerns": parsed.get("possible_concerns", ""),
        "Urgency": parsed.get("urgency", ""),
        "Suggested next step": parsed.get("suggested_next_step", ""),
        "Why": parsed.get("why", ""),
        "Reasoning": parsed.get("reasoning", []),
        "Confidence": parsed.get("confidence", 0.0),
        "Sources used": parsed.get("sources_used", []),
    }


def generate_answer_once(query: str, docs: list[dict], intent: str) -> tuple[dict, str]:
    messages = build_messages(query, docs, intent)

    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=messages,
        temperature=0.35,
    )

    raw_answer = response.choices[0].message.content
    parsed = safe_parse(raw_answer)

    return parsed, raw_answer


def dedupe_docs(docs: list[dict]) -> list[dict]:
    seen = set()
    out = []

    for doc in docs:
        key = (
            doc.get("title", "").strip().lower(),
            doc.get("url", "").strip().lower(),
        )

        if key in seen:
            continue

        seen.add(key)
        out.append(doc)

    return out


def is_structured_answer_weak(answer: dict) -> bool:
    display = answer.get("display_answer", "").lower().strip()
    fast = answer.get("fast_answer", "").lower().strip()
    possible = answer.get("possible_concerns", "").lower()
    why = answer.get("why", "").lower()

    try:
        confidence = float(answer.get("confidence", 0.0))
    except Exception:
        confidence = 0.0

    main_text = display or fast

    weak_markers = [
        "not enough information",
        "could not format",
        "does not mention",
        "do not mention",
        "not addressed",
    ]

    if len(main_text.strip()) < 80:
        return True

    if any(marker in main_text for marker in weak_markers):
        return True

    if any(marker in possible for marker in weak_markers):
        return True

    if any(marker in why for marker in weak_markers):
        return True

    if confidence < 0.45:
        return True

    return False


def choose_better_answer(
    parsed_1: dict,
    raw_1: str,
    docs_1: list[dict],
    critic_1: dict,
    parsed_2: dict,
    raw_2: str,
    docs_2: list[dict],
    critic_2: dict,
):
    pass1_weak = is_structured_answer_weak(parsed_1)
    pass2_weak = is_structured_answer_weak(parsed_2)

    if pass1_weak and not pass2_weak:
        return parsed_2, raw_2, docs_2, critic_2

    if not pass1_weak and pass2_weak:
        return parsed_1, raw_1, docs_1, critic_1

    if critic_2.get("is_good_enough", False) and not critic_1.get("is_good_enough", False):
        return parsed_2, raw_2, docs_2, critic_2

    answer_1 = parsed_1.get("display_answer", "") or parsed_1.get("fast_answer", "")
    answer_2 = parsed_2.get("display_answer", "") or parsed_2.get("fast_answer", "")

    if len(answer_2) > len(answer_1) + 60:
        return parsed_2, raw_2, docs_2, critic_2

    return parsed_1, raw_1, docs_1, critic_1


def agentic_answer(query: str, top_k: int = 4) -> dict:
    retrieval_result_1 = hybrid_retrieve(query, top_k=top_k)
    docs_1 = retrieval_result_1["final_docs"]
    intent = retrieval_result_1["plan"].get("intent", "unknown")

    parsed_1, raw_1 = generate_answer_once(query, docs_1, intent)

    try:
        critic_1 = critic_answer(query, parsed_1, docs_1, intent=intent)
    except TypeError:
        critic_1 = critic_answer(query, parsed_1, docs_1)
    except Exception:
        critic_1 = {
            "is_good_enough": True,
            "problems": [],
            "follow_up_queries": [],
            "reason": "Critic failed; keeping first answer.",
        }

    used_second_pass = False
    final_docs = docs_1
    final_parsed = parsed_1
    final_raw = raw_1
    final_critic = critic_1
    final_retrieval = retrieval_result_1

    should_second_pass = (
        not critic_1.get("is_good_enough", True)
        or is_structured_answer_weak(parsed_1)
    )

    if should_second_pass:
        used_second_pass = True

        extra_queries = critic_1.get("follow_up_queries", [])
        if not extra_queries:
            extra_queries = [query]

        extra_docs = []
        for q in extra_queries[:3]:
            extra_result = hybrid_retrieve(q, top_k=top_k)
            extra_docs.extend(extra_result["final_docs"])

        candidate_docs = dedupe_docs(docs_1 + extra_docs)[: top_k + 2]

        parsed_2, raw_2 = generate_answer_once(query, candidate_docs, intent)

        try:
            critic_2 = critic_answer(query, parsed_2, candidate_docs, intent=intent)
        except TypeError:
            critic_2 = critic_answer(query, parsed_2, candidate_docs)
        except Exception:
            critic_2 = {
                "is_good_enough": True,
                "problems": [],
                "follow_up_queries": [],
                "reason": "Critic failed; judging answer by heuristics.",
            }

        final_parsed, final_raw, final_docs, final_critic = choose_better_answer(
            parsed_1,
            raw_1,
            docs_1,
            critic_1,
            parsed_2,
            raw_2,
            candidate_docs,
            critic_2,
        )

    return {
        "raw_answer": final_raw,
        "structured_answer": final_parsed,
        "sections": normalize_sections(final_parsed),
        "sources": final_docs,
        "used_second_pass": used_second_pass,
        "critic": final_critic,
        "retrieval_plan": final_retrieval["plan"],
        "mismatch_check": final_retrieval["mismatch_check"],
        "used_external": final_retrieval["used_external"],
    }


if __name__ == "__main__":
    result = agentic_answer("what is different between muscle and joint?", top_k=4)

    print("\n=== DISPLAY ANSWER ===\n")
    print(result["structured_answer"].get("display_answer", ""))

    print("\n=== FAST ANSWER ===\n")
    print(result["structured_answer"].get("fast_answer", ""))

    print("\n=== STRUCTURED ANSWER ===\n")
    print(json.dumps(result["structured_answer"], indent=2, ensure_ascii=False))

    print("\n=== CRITIC ===\n")
    print(json.dumps(result["critic"], indent=2, ensure_ascii=False))

    print("\n=== SOURCES ===\n")
    for i, doc in enumerate(result["sources"], start=1):
        print(
            f"{i}. {doc.get('title')} | "
            f"{doc.get('retrieval_source')} | "
            f"{doc.get('url')}"
        )