import tomllib

from cortex.shared.models import get_embedder, get_client, get_clip

import torch
from cortex.ingestion.clip import get_clip


def _get_similarity_threshold(config_path: str = "config.toml") -> float:
    try:
        with open(config_path, "rb") as f:
            config = tomllib.load(f)
        return config.get("retrieval", {}).get("similarity_threshold", 0.7)
    
    except FileNotFoundError:
        return 0.7
    
    """
    reads the similarity threshold from config.toml
    defaults to 0.7 if section/key is missing or file not found
    so that this does not hard crash
    """

def search_text(query: str, k: int = 5, threshold: float | None = None) -> list[dict]:
    if threshold is None:
        threshold = _get_similarity_threshold()

    embedder = get_embedder()
    client = get_client()
    collection = client.get_or_create_collection("text_chunks", metadata={"hnsw:space": "cosine"})

    query_embedding = embedder.encode([query]).tolist()
    results = collection.query(query_embeddings=query_embedding, n_results=k)

    output = []

    if not results["ids"][0]:
        return output
    
    for doc, meta, dist in zip(results["documents"][0], results["metadatas"][0], results["distances"][0]):

        if dist > threshold:
            continue

        output.append({
            "type": "text",
            "content": doc,
            "file_path": meta["file_path"],
            "score": dist,
        })

    return output


def search_image(query: str, k: int = 5, threshold: float | None = None) -> list[dict]:
    if threshold is None:
        threshold = _get_similarity_threshold()

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
        if dist > threshold:
            continue

        output.append({
            "type": "image",
            "file_path": meta["file_path"],
            "score": dist,
        })
    return output


def search(query: str, k: int = 5) -> list[dict]:
    threshold = _get_similarity_threshold()

    text_results = search_text(query, k=k, threshold=threshold)
    image_results = search_image(query, k=k, threshold=threshold)

    combined = text_results + image_results
    combined.sort(key=lambda r: r["score"])
    return combined[:k]