RED_FLAG_KEYWORDS = [
    "chest pain",
    "shortness of breath",
    "difficulty breathing",
    "severe bleeding",
    "loss of consciousness",
    "stroke",
    "seizure",
    "suicidal",
    "fainting",
]

def detect_risk(query: str) -> str:
    q = query.lower()
    for kw in RED_FLAG_KEYWORDS:
        if kw in q:
            return "high"
    return "normal"
