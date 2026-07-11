from shared.models import get_embedder, get_client
from shared.logger import logger
import hashlib

def file_hash(path: str) -> str:
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()
    

# TODO: This sometimes returns false when it should be true
def needs_indexing(file_path: str) -> bool:
    current_hash = file_hash(file_path)

    collection = get_client().get_or_create_collection("text_chunks")
    existing = collection.get(where={"file_path": file_path})
    
    if not existing["ids"]:
        return True
    return existing["metadatas"][0]["file_hash"] != current_hash

 
def store_chunks(file_path: str, chunks: list[str]):
    # removing empty chunks
    for i in range(len(chunks)):
        temp = chunks[i].replace(" ", "")
        if temp == "":
            chunks.pop(i)
            logger.log("[LOG] Skipped an empty chunk")
    
    # if every chunk is empty
    if len(chunks) == 0:
        logger.log("[LOG] Cancelled empty chunk storage")
        return

    embedder = get_embedder()
    client = get_client()

    collection = client.get_or_create_collection("text_chunks")

    hash_ = file_hash(file_path)

    # remove old entries for this file if its already been indexed before
    collection.delete(where={"file_path": file_path})

    embeddings = embedder.encode(chunks).tolist()
    ids = [f"{file_path}::{i}" for i in range(len(chunks))]
    metadatas = [{"file_path": file_path, "file_hash": hash_, "chunk_index": i} for i in range(len(chunks))]

    collection.add(
        ids=ids,
        embeddings=embeddings,
        documents=chunks,
        metadatas=metadatas,
    )

    