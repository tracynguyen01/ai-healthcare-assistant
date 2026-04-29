import json


def extract_json(text: str) -> dict:
    text = text.strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}") + 1

        if start == -1 or end == 0:
            raise ValueError("No valid JSON object found.")

        return json.loads(text[start:end])


def safe_parse(raw_text: str) -> dict:
    try:
        data = extract_json(raw_text)

        display_answer = str(
            data.get(
                "display_answer",
                data.get("fast_answer", data.get("possible_concerns", "")),
            )
        ).strip()

        fast_answer = str(data.get("fast_answer", "")).strip()

        if not fast_answer:
            fast_answer = str(data.get("possible_concerns", "")).strip()

        if not fast_answer:
            fast_answer = display_answer

        if not fast_answer:
            fast_answer = (
                "I could not find a clear answer, but you can check the sources tab "
                "for more details."
            )

        if not display_answer:
            display_answer = fast_answer

        return {
            "display_answer": display_answer,
            "fast_answer": fast_answer,
            "possible_concerns": str(
                data.get("possible_concerns", fast_answer)
            ).strip(),
            "urgency": str(data.get("urgency", "Unknown")).strip(),
            "suggested_next_step": str(
                data.get(
                    "suggested_next_step",
                    "Monitor your symptoms and seek medical advice if they are severe, persistent, or worsening.",
                )
            ).strip(),
            "why": str(
                data.get(
                    "why",
                    "This answer is based on retrieved sources and general medical knowledge.",
                )
            ).strip(),
            "reasoning": data.get("reasoning", [])
            if isinstance(data.get("reasoning", []), list)
            else [],
            "confidence": float(data.get("confidence", 0.7))
            if str(data.get("confidence", "")).strip()
            else 0.7,
            "sources_used": data.get("sources_used", [])
            if isinstance(data.get("sources_used", []), list)
            else [],
        }

    except Exception:
        return {
            "display_answer": "Sorry, I couldn't properly generate an answer. Please try asking in a slightly different way.",
            "fast_answer": "Sorry, I couldn't properly generate an answer. Please try asking in a slightly different way.",
            "possible_concerns": "Unable to determine from available data.",
            "urgency": "Unknown",
            "suggested_next_step": "Please consult a healthcare professional if you are concerned about your symptoms.",
            "why": "The system could not parse the model response into structured format.",
            "reasoning": [],
            "confidence": 0.0,
            "sources_used": [],
        }