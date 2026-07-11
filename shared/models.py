# need to do this to always use cached version and not look online every time. saves latency
import os
os.environ["HF_HUB_OFFLINE"] = "1"

import chromadb
import subprocess
import time
from sentence_transformers import SentenceTransformer
from shared.logger import logger


# TODO: If program crashes, server will continue running in background, fix plz!!
# Starting chroma server
def start_server():
    logger.clear_logs()
    
    subprocess.Popen(
        ["chroma", "run", "--path", "./chroma_db"],
        stdout=subprocess.DEVNULL, # stops from printing server outputs
        stderr=subprocess.DEVNULL # stops from printing server errors
    )

    logger.log("[LOG] Started Chroma server.")

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
        # _client = chromadb.PersistentClient(path="./chroma_db",


        # NOTE TO TEAMMATES:
        # I tried running the program once, but I got an error saying server hasnt started, which implied that the other parts of the program(eg. watcher) started running before the server had started.
        # Adding this timer fixed it, However, since then I havn't been able to recreate it
        # V V V V V V V V

        # attempt the server in 0.5 secs intervals 
        i = 0; 
        while True:
            try:                        
                _client = chromadb.HttpClient(host="localhost", port=8000, settings=chromadb.Settings(allow_reset=True))
                logger.log("[LOG] Server started.")
                print(f"Welcome to Cortex!");
                break
            except:
                logger.log(f"[LOG] Failed to start server, retrying ({i})...")
                print(f"Failed to start server, retrying ({i})...")
                i += 1
                time.sleep(0.5)

    return _client
