import json
import os
from dotenv import load_dotenv
from groq import Groq


load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise ValueError("Missing GROQ_API_KEY in .env")

client = Groq(api_key=GROQ_API_KEY)

MODEL_NAME = "llama-3.3-70b-versatile"


def extract_json(text: str) -> dict:
    text = text.strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}") + 1
        if start == -1 or end == 0:
            raise ValueError("No valid JSON object found in critic response.")
        return json.loads(text[start:end])


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
    )
    return set(cleaned.split())


def keep_queries_on_topic(original_query: str, follow_up_queries: list[str]) -> list[str]:
    """
    Keep only follow-up queries that still overlap with the original topic.
    This prevents pass-2 retrieval from drifting too far away.
    """
    original_words = normalize_words(original_query)
    filtered = []

    for q in follow_up_queries:
        q_words = normalize_words(q)
        if len(original_words & q_words) >= 1:
            filtered.append(q)

    if not filtered:
        filtered = [original_query]

    return filtered[:3]


def safe_parse_critic(raw: str) -> dict:
    """
    Parse critic response safely.
    If parsing fails, default to 'good enough' to avoid destructive second-pass behavior.
    """
    try:
        critic = extract_json(raw)
    except Exception:
        return {
            "is_good_enough": True,
            "problems": [],
            "follow_up_queries": [],
            "reason": "Critic parsing failed; defaulting to keep first-pass answer.",
        }

    if "is_good_enough" not in critic:
        critic["is_good_enough"] = False
    if "problems" not in critic or not isinstance(critic["problems"], list):
        critic["problems"] = []
    if "follow_up_queries" not in critic or not isinstance(critic["follow_up_queries"], list):
        critic["follow_up_queries"] = []
    if "reason" not in critic:
        critic["reason"] = ""

    return critic


def critic_answer(query: str, answer_json: dict, docs: list[dict], intent: str = "unknown") -> dict:
    source_titles = [doc.get("title", "") for doc in docs]

    system_prompt = (
        "You are an answer quality critic for a healthcare RAG system.\n"
        "You do NOT answer the user's question.\n"
        "You only judge answer quality.\n\n"
        "Return ONLY valid JSON.\n\n"
        "JSON format:\n"
        "{\n"
        '  "is_good_enough": true,\n'
        '  "problems": ["problem 1", "problem 2"],\n'
        '  "follow_up_queries": ["query 1", "query 2"],\n'
        '  "reason": "short explanation"\n'
        "}\n\n"
        "Rules:\n"
        "- Mark is_good_enough=false if the answer is vague, generic, weakly grounded, or misses the direct question.\n"
        "- Mark is_good_enough=false if the answer gives generic advice not clearly supported by the sources.\n"
        "- For definition intent, mark false if the answer does not directly define the topic.\n"
        "- For comparison intent, mark false if the answer does not explicitly compare both items.\n"
        "- For triage intent, mark false if urgency or next step is missing.\n"
        "- follow_up_queries should be short and retrieval-friendly.\n"
        "- No markdown. No extra text."
    )

    user_prompt = (
        f"Intent:\n{intent}\n\n"
        f"User query:\n{query}\n\n"
        f"Answer JSON:\n{json.dumps(answer_json, ensure_ascii=False)}\n\n"
        f"Available source titles:\n{json.dumps(source_titles, ensure_ascii=False)}"
    )

    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.1,
    )

    raw = response.choices[0].message.content
    critic = safe_parse_critic(raw)

    critic["follow_up_queries"] = keep_queries_on_topic(
        query,
        critic.get("follow_up_queries", [])
    )

    return critic