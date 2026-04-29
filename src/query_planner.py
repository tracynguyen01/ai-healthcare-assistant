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
            raise ValueError("No valid JSON object found in planner response.")

        return json.loads(text[start:end])


def normalize_query(text: str) -> str:
    cleaned = (
        text.lower()
        .strip()
        .replace("?", "")
        .replace(",", " ")
        .replace(".", " ")
        .replace(":", " ")
        .replace(";", " ")
    )
    return " ".join(cleaned.split())


def unique_keep_order(items: list[str]) -> list[str]:
    return list(dict.fromkeys([x.strip() for x in items if x and x.strip()]))


def split_comparison_entities(q: str) -> tuple[str | None, str | None]:
    q = q.lower().strip()
    q = q.replace("what is different between", "difference between")
    q = q.replace("what is the difference between", "difference between")
    q = q.replace("different between", "difference between")
    q = q.replace("versus", "vs")

    if "difference between" in q and " and " in q:
        try:
            parts = q.split("difference between", 1)[1].strip()
            left, right = parts.split(" and ", 1)
            return left.strip(), right.strip()
        except Exception:
            return None, None

    if " vs " in q:
        try:
            left, right = q.split(" vs ", 1)
            return left.strip(), right.strip()
        except Exception:
            return None, None

    if q.startswith("compare ") and " and " in q:
        try:
            parts = q.replace("compare ", "", 1).strip()
            left, right = parts.split(" and ", 1)
            return left.strip(), right.strip()
        except Exception:
            return None, None

    return None, None


def rule_based_rewrites(query: str) -> dict:
    q = normalize_query(query)

    result = {
        "intent": "unknown",
        "rewrite_queries": [q],
        "need_external_search": False,
        "preferred_sources": ["nhs", "healthdirect", "medlineplus"],
        "reason": "Default planning.",
    }

    # -------------------------
    # Comparison
    # Put this BEFORE definition.
    # Otherwise "what is difference between X and Y" can be treated as definition.
    # -------------------------
    comparison_markers = [
        "difference between",
        "different between",
        "compare",
        " vs ",
        "versus",
    ]

    if any(marker in q for marker in comparison_markers):
        core = q.replace("different between", "difference between").replace("versus", "vs").strip()
        left, right = split_comparison_entities(core)

        extra_queries = [core, q]

        if left and right:
            extra_queries.extend(
             [
               f"{left} definition",
               f"{right} definition",
               f"{left} meaning",
               f"{right} meaning",
               f"difference between {left} and {right}",
               f"{left} vs {right}",
             ]
            )
        else:
            extra_queries.extend(
                [
                    f"{core} definition",
                    f"{core} explanation",
                    f"{core} comparison",
                ]
            )

        result.update(
            {
                "intent": "comparison",
                "rewrite_queries": unique_keep_order(extra_queries),
                "need_external_search": True,
                "preferred_sources": ["medlineplus", "healthdirect", "nhs"],
                "reason": "User is asking for a comparison between concepts.",
            }
        )
        return result
    
    if "between" in q and " and " in q:
      left, right = split_comparison_entities(q)

      if left and right:
        result.update(
            {
                "intent": "comparison",
                "rewrite_queries": unique_keep_order(
                    [
                        f"{left} definition",
                        f"{right} definition",
                        f"{left} meaning",
                        f"{right} meaning",
                        f"difference between {left} and {right}",
                        f"{left} vs {right}",
                    ]
                ),
                "need_external_search": True,
                "preferred_sources": ["medlineplus", "healthdirect", "nhs"],
                "reason": "User is asking for a comparison between two concepts.",
            }
        )
      return result

    # -------------------------
    # Definition
    # Do NOT automatically add symptoms/causes here.
    # Otherwise normal definition queries can drift into symptom pages.
    # -------------------------
    if q.startswith("what is ") or q.startswith("what are "):
        if q.startswith("what is "):
            core = q.replace("what is ", "", 1).strip()
        else:
            core = q.replace("what are ", "", 1).strip()

        result.update(
            {
                "intent": "definition",
                "rewrite_queries": unique_keep_order(
                    [
                        core,
                        f"{core} definition",
                        f"{core} meaning",
                        f"{core} explanation",
                    ]
                ),
                "need_external_search": True,
                "preferred_sources": ["medlineplus", "nhs", "healthdirect"],
                "reason": "User is seeking a definition or explanation.",
            }
        )
        return result

    # -------------------------
    # Triage / action
    # -------------------------
    triage_markers = [
        "what should i do",
        "what do i do",
        "do i need",
        "should i go",
        "urgent",
        "emergency",
        "help now",
        "call ambulance",
        "go to hospital",
    ]

    if any(marker in q for marker in triage_markers):
        result.update(
            {
                "intent": "triage",
                "rewrite_queries": unique_keep_order(
                    [
                        q,
                        f"{q} urgent care",
                        f"{q} when to get help",
                        f"{q} red flags",
                    ]
                ),
                "need_external_search": True,
                "preferred_sources": ["healthdirect", "nhs", "cdc", "medlineplus"],
                "reason": "User is asking for action or urgency guidance.",
            }
        )
        return result

    # -------------------------
    # Symptom explanation
    # -------------------------
    symptom_markers = [
        "i have",
        "i am having",
        "i feel",
        "pain",
        "hurt",
        "ache",
        "headache",
        "cough",
        "fever",
        "shortness of breath",
        "stomach pain",
        "tired",
        "dizzy",
        "nausea",
        "vomiting",
        "diarrhea",
        "diarrhoea",
    ]

    if any(marker in q for marker in symptom_markers):
        result.update(
            {
                "intent": "symptom_explanation",
                "rewrite_queries": unique_keep_order(
                    [
                        q,
                        f"{q} causes",
                        f"{q} symptoms",
                        f"{q} what to do",
                    ]
                ),
                "need_external_search": True,
                "preferred_sources": ["nhs", "healthdirect", "medlineplus"],
                "reason": "User is describing symptoms or asking symptom-related questions.",
            }
        )
        return result

    return result


def llm_plan_query(query: str) -> dict:
    system_prompt = (
        "You are a query planning assistant for a healthcare retrieval system. "
        "Your job is NOT to answer the question. "
        "Your job is to produce a retrieval plan only. "
        "Return STRICTLY valid JSON only.\n\n"
        "Schema:\n"
        "{\n"
        '  "intent": "definition | symptom_explanation | triage | comparison | treatment | unknown",\n'
        '  "rewrite_queries": ["query 1", "query 2", "query 3"],\n'
        '  "need_external_search": true,\n'
        '  "preferred_sources": ["nhs", "healthdirect", "cdc", "medlineplus"],\n'
        '  "reason": "short explanation"\n'
        "}\n\n"
        "Rules:\n"
        "- rewrite_queries should be short and search-friendly.\n"
        "- For comparison queries, generate neutral definition/comparison searches, not pain/symptom searches unless the user explicitly mentions pain.\n"
        "- For definition queries, do not add symptoms/causes unless the query asks about symptoms or causes.\n"
        "- preferred_sources must be selected from: nhs, healthdirect, cdc, medlineplus.\n"
        "- No markdown, no bullet points, no extra commentary."
    )

    user_prompt = f"User query: {query}"

    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.1,
    )

    raw = response.choices[0].message.content
    plan = extract_json(raw)

    if "rewrite_queries" not in plan or not isinstance(plan["rewrite_queries"], list) or not plan["rewrite_queries"]:
        plan["rewrite_queries"] = [query]

    if "preferred_sources" not in plan or not isinstance(plan["preferred_sources"], list):
        plan["preferred_sources"] = ["nhs", "healthdirect", "medlineplus"]

    valid_sources = {"nhs", "healthdirect", "cdc", "medlineplus"}
    plan["preferred_sources"] = [
        s for s in plan["preferred_sources"] if s in valid_sources
    ] or ["nhs", "healthdirect", "medlineplus"]

    if "need_external_search" not in plan:
        plan["need_external_search"] = False

    if "intent" not in plan:
        plan["intent"] = "unknown"

    if "reason" not in plan:
        plan["reason"] = ""

    plan["rewrite_queries"] = unique_keep_order(plan["rewrite_queries"])

    return plan

def correct_query_spelling(query: str) -> str:
    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Correct spelling and grammar. "
                        "Do not change the meaning. "
                        "Do not add medical information. "
                        "Return only the corrected query text."
                    ),
                },
                {"role": "user", "content": query},
            ],
            temperature=0.0,
        )

        corrected = response.choices[0].message.content.strip()
        return corrected if corrected else query

    except Exception:
        return query

def plan_query(query: str) -> dict:
    """
    Correct query first, then apply rule-based planning.
    This prevents typo queries like:
    'what is diferent between muscle and joint'
    from being wrongly classified as definition.
    """
    corrected_query = correct_query_spelling(query)

    rule_plan = rule_based_rewrites(corrected_query)

    if rule_plan["intent"] != "unknown":
        rule_plan["original_query"] = query
        rule_plan["corrected_query"] = corrected_query
        return rule_plan

    try:
        plan = llm_plan_query(corrected_query)
        plan["original_query"] = query
        plan["corrected_query"] = corrected_query
        return plan
    except Exception:
        rule_plan["original_query"] = query
        rule_plan["corrected_query"] = corrected_query
        return rule_plan
    
if __name__ == "__main__":
    tests = [
        "what is headache?",
        "what is different between muscle and joint?",
        "difference between virus and bacteria",
        "i have chest pain and shortness of breath what should i do",
    ]

    for q in tests:
        print("\nQUERY:", q)
        result = plan_query(q)
        print(json.dumps(result, indent=2, ensure_ascii=False))