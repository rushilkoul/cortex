from pathlib import Path 

import hashlib
import os
import threading
import tomllib 
import mammoth
import pymupdf4llm

from cortex.shared.models import get_embedder, get_client
from cortex.shared.logger import logger
from cortex.ingestion.clip import embed_image
from cortex.ingestion.chunking import chunk_markdown, chunk_text

TEXT_EXTENSIONS = {".md", ".markdown", ".txt", ".docx", ".pdf"}
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png"}

_INDEX_LOCK = threading.RLock()

def file_metadata(path: str) -> dict:
    stat = os.stat(path)
    p = Path(path)
    return {
        "file_path": str(p),
        "file_name": p.name,
        "extension": p.suffix.lower(),
        "mtime": stat.st_mtime,       # last modified
        "ctime": stat.st_ctime,       # created/metadata-changed
        "size_bytes": stat.st_size,
    }

def try_index(file_path: str) -> None:
    # logger.log(f"!!!!!!!!! index function called: {file_path}")
    with _INDEX_LOCK:
        path = Path(file_path)
        if not path.exists() or path.is_dir():
            return

        suffix = path.suffix.lower()
        # logger.log(f"!!!!!!!!! trying to index {file_path}")

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
            return

        try:
            if suffix == ".md" or suffix == ".markdown" or suffix == ".txt":
                text = path.read_text(encoding="utf-8")
                #text = md.convert(path).text_content
            elif suffix == ".docx":
                # converting a doc to markdown
                with open(path, "rb") as f:
                    result = mammoth.convert_to_markdown(f)
                    text = result.value
            elif suffix == ".pdf":
                text = pymupdf4llm.to_markdown(path)
            else:
                pass
        except (UnicodeDecodeError, PermissionError, FileNotFoundError) as e:
            logger.log(f"[SKIPPED UNREADABLE] {file_path}: {e}")
            return

        if not text.strip():
            return

        try:
            if needs_indexing(file_path):
                chunks = chunk_text(text)
                if chunks:
                    store_chunks(file_path, chunks)
            else:
                logger.log(f"[SKIPPED UNCHANGED] {file_path}")
        except Exception as e:
            logger.log(f"[ERROR indexing] {file_path}: {e}")


def delete_file(file_path: str):
    with _INDEX_LOCK:
        client = get_client()
        client.get_or_create_collection("text_chunks", metadata={"hnsw:space": "cosine"}).delete(where={"file_path": file_path})
        client.get_or_create_collection("images", metadata={"hnsw:space": "cosine"}).delete(where={"file_path": file_path})
    

# todo FIXED! Images werent being considered.
def needs_indexing(file_path: str) -> bool:
    with _INDEX_LOCK:
        current_hash = file_hash(file_path)

        collection = get_client().get_or_create_collection("text_chunks", metadata={"hnsw:space": "cosine"})
        existing = collection.get(where={"file_path": file_path})
        
        if not existing["ids"]:
            img_collection = get_client().get_or_create_collection("images", metadata={"hnsw:space": "cosine"})
            existing_img = img_collection.get(where={"file_path": file_path})
            if not existing_img["ids"]:
                return True
            return existing_img["metadatas"][0]["file_hash"] != current_hash
        return existing["metadatas"][0]["file_hash"] != current_hash

 
def store_chunks(file_path: str, chunks: list[str]):
    with _INDEX_LOCK:
        chunks = [c for c in chunks if c.replace(" ", "").strip() != ""]
        if not chunks:
            logger.log("[LOG] Cancelled empty chunk storage")
            return

        embedder = get_embedder()
        client = get_client()

        collection = client.get_or_create_collection("text_chunks", metadata={"hnsw:space": "cosine"})

        hash_ = file_hash(file_path)
        meta_base = file_metadata(file_path)

        # remove old entries for this file if its already been indexed before
        collection.delete(where={"file_path": file_path})

        embeddings = embedder.encode(chunks).tolist()
        ids = [f"{file_path}::{i}" for i in range(len(chunks))]
        metadatas = [
            {**meta_base, "file_hash": hash_, "chunk_index": i}
            for i in range(len(chunks))
        ]

        collection.add(ids=ids, embeddings=embeddings, documents=chunks, metadatas=metadatas)



def store_image(file_path: str):
    with _INDEX_LOCK:
        embedding = embed_image(file_path)

        client = get_client()
        collection = client.get_or_create_collection("images", metadata={"hnsw:space": "cosine"})
        hash_ = file_hash(file_path)
        meta_base = file_metadata(file_path)

        collection.delete(where={"file_path": file_path})
        collection.add(
            ids=[file_path],
            embeddings=[embedding],
            metadatas=[{**meta_base, "file_hash": hash_}],
            
        )


def file_hash(path: str) -> str:
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()
    



def bulk_index_directory(directory: str) -> int:
    root = Path(os.path.expanduser(directory))
    if not root.exists():
        logger.log(f"[BULK] Skipping missing directory: {directory}")
        return 0

    count = 0
    for path in root.rglob("*"):
        if path.is_dir():
            continue
        if any(part.startswith(".") for part in path.parts):
            continue
        try_index(str(path))
        count += 1

    logger.log(f"[BULK] Scanned {directory}: {count} files checked")
    return count


def bulk_index_all(config_path: str = "config.toml") -> None:
    with open(config_path, "rb") as f:
        config = tomllib.load(f)

    for directory in config["tracker"]["directories"]:
        bulk_index_directory(directory)

    logger.log("[BULK] Initial scan complete.")