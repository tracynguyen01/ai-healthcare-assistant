import json
import xml.etree.ElementTree as ET
from pathlib import Path


def parse_medlineplus_xml(xml_path: str, output_path: str):
    tree = ET.parse(xml_path)
    root = tree.getroot()

    docs = []
    idx = 1

    for topic in root.findall(".//health-topic"):
        title_el = topic.find("title")
        full_summary_el = topic.find("full-summary")
        url_el = topic.find("url")

        title = title_el.text.strip() if title_el is not None and title_el.text else None
        text = full_summary_el.text.strip() if full_summary_el is not None and full_summary_el.text else None
        url = url_el.text.strip() if url_el is not None and url_el.text else ""

        if not title or not text:
            continue

        docs.append(
            {
                "id": f"medline_doc_{idx:04d}",
                "source": "medlineplus",
                "source_name": "medlineplus",
                "country": "US",
                "trust_weight": 0.95,
                "content_type": "health_topic",
                "url": url,
                "title": title,
                "text": text,
            }
        )
        idx += 1

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(docs, f, indent=2, ensure_ascii=False)

    print(f"Saved {len(docs)} MedlinePlus docs to {output_path}")