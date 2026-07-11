from sentence_transformers import SentenceTransformer
import chromadb

_embedder = None
_client = None

def get_embedder():
    global _embedder
    if _embedder is None:
        _embedder = SentenceTransformer("all-MiniLM-L6-v2")
    return _embedder

def get_client():
    global _client
    if _client is None:
        _client = chromadb.PersistentClient(path="./chroma_db")
    return _client