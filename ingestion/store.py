import hashlib

from shared.models import get_embedder, get_client
from shared.logger import logger
from ingestion.clip import embed_image
from ingestion.chunking import chunk_markdown
from pathlib import Path 

TEXT_EXTENSIONS = {".md", ".markdown"}
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png"}

def try_index(file_path: str) -> None:
    path = Path(file_path)
    if not path.exists() or path.is_dir():
        return

    suffix = path.suffix.lower()

    if suffix in IMAGE_EXTENSIONS:
        try:
            if needs_indexing(file_path):
                store_image(file_path)
            else:
                logger.log(f"[SKIPPED UNCHANGED] {file_path}")
        except Exception as e:
            logger.log(f"[ERROR indexing image] {file_path}: {e}")
        return

    if suffix not in TEXT_EXTENSIONS:
        return  # not a type we handle

    try:
        text = path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, PermissionError, FileNotFoundError) as e:
        logger.log(f"[SKIPPED UNREADABLE] {file_path}: {e}")
        return

    if not text.strip():
        return

    if needs_indexing(file_path):
        chunks = chunk_markdown(text)
        if chunks:
            store_chunks(file_path, chunks)
    else:
        logger.log(f"[SKIPPED UNCHANGED] {file_path}")

    

# TODO: This sometimes returns false when it should be true

# what?

def needs_indexing(file_path: str) -> bool:
    current_hash = file_hash(file_path)

    collection = get_client().get_or_create_collection("text_chunks")
    existing = collection.get(where={"file_path": file_path})
    
    if not existing["ids"]:
        return True
    return existing["metadatas"][0]["file_hash"] != current_hash

 
def store_chunks(file_path: str, chunks: list[str]):
    chunks = [c for c in chunks if c.replace(" ", "").strip() != ""]
    if not chunks:
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



def store_image(file_path: str):
    embedding = embed_image(file_path)

    client = get_client()
    collection = client.get_or_create_collection("images")
    hash_ = file_hash(file_path)

    collection.delete(where={"file_path": file_path})
    collection.add(
        ids=[file_path],
        embeddings=[embedding],
        metadatas=[{"file_path": file_path, "file_hash": hash_}],
    )


def file_hash(path: str) -> str:
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()
    

