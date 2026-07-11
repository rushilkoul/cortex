from shared.models import get_embedder, get_client

def search_text(query: str, k: int = 5) -> list[dict]:
    embedder = get_embedder()
    client = get_client()
    collection = client.get_or_create_collection("text_chunks")

    query_embedding = embedder.encode([query]).tolist()
    results = collection.query(query_embeddings=query_embedding, n_results=k)

    output = []
    
    for doc, meta, dist in zip(results["documents"][0], results["metadatas"][0], results["distances"][0]):
        output.append({
            "type": "text",
            "content": doc,
            "file_path": meta["file_path"],
            "score": dist,
        })

    return output