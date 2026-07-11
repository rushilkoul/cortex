from shared.models import get_embedder, get_client, get_clip

import torch
from ingestion.clip import get_clip

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


def search_image(query: str, k: int = 5) -> list[dict]:
    model, _, tokenizer, device = get_clip()

    text_tokens = tokenizer([query]).to(device)
    with torch.no_grad():
        query_embedding = model.encode_text(text_tokens)
        query_embedding = query_embedding / query_embedding.norm(dim=-1, keepdim=True)

    query_embedding = query_embedding.squeeze(0).cpu().tolist()

    client = get_client()
    collection = client.get_or_create_collection("images", metadata={"hnsw:space": "cosine"})
    if collection.count() == 0:
        return []

    results = collection.query(query_embeddings=[query_embedding], n_results=k)

    output = []
    for meta, dist in zip(results["metadatas"][0], results["distances"][0]):
        output.append({
            "type": "image",
            "file_path": meta["file_path"],
            "score": dist,
        })
    return output