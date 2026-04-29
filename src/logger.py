from datetime import datetime
import json
from pathlib import Path

def log_query(query: str, answer: str):
    log_path = Path("data/processed/query_logs.jsonl")
    log_path.parent.mkdir(parents=True, exist_ok=True)

    record = {
        "timestamp": datetime.utcnow().isoformat(),
        "query": query,
        "answer_preview": answer[:200]
    }

    with open(log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")