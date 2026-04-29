from src.internal_retrieve import internal_search


def search(query: str, top_k: int = 5):
    return internal_search(query, top_k=top_k)


if __name__ == "__main__":
    query = "I have chest pain and shortness of breath"
    results = search(query, top_k=5)

    for r in results:
        print("\n---")
        print(r["title"])
        print(r["source"])
        print(r["url"])
        print(r["text"][:300])
        print("score:", r["score"])
        print("final_score:", r["final_score"])