# need to do this to always use cached version and not look online every time. saves latency
import os
os.environ["HF_HUB_OFFLINE"] = "1"

import chromadb
import subprocess
import time

from cortex.shared.logger import logger

_server_process = None

def start_server():
    global _server_process
    logger.clear_logs()
    _server_process = subprocess.Popen(
        ["chroma", "run", "--path", "./chroma_db"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )
    logger.log("[LOG] Started Chroma server.")

def stop_server():
    if _server_process:
        _server_process.terminate()
        _server_process.wait()

_embedder = None
_client = None

def get_embedder():
    from sentence_transformers import SentenceTransformer
    global _embedder
    if _embedder is None:
        _embedder = SentenceTransformer("all-MiniLM-L6-v2")
    return _embedder

def get_client():
    global _client
    if _client is None:
        i = 0; 
        while i < 50:
            try:                        
                _client = chromadb.HttpClient(host="localhost", port=8000)
                _client.heartbeat()
                logger.log("[LOG] Server started.")
                break
            except (ConnectionError, Exception) as e:
                i += 1
                logger.log(f"[LOG] Server not ready yet: {e}")
                print(f"Failed to start server, retrying ({i}/50)...")
                time.sleep(0.5)

    return _client

_model = None
_preprocess = None
_tokenizer = None
_device = None

def get_clip():

    import open_clip
    import torch

    global _model, _preprocess, _tokenizer, _device
    if _model is None:
        # prefer NVIDIA GPU if available, else fallback to CPU
        _device = "cuda" if torch.cuda.is_available() else "cpu"

        _model, _, _preprocess = open_clip.create_model_and_transforms(
            "ViT-B-32", 
            pretrained="laion2b_s34b_b79k"
        )

        # ignore second argument since we dont need to train the model, 
        # we just need the pretrained weights for inference.
        _tokenizer = open_clip.get_tokenizer("ViT-B-32")
        
        _model = _model.to(_device)
        _model.eval() #set to inference mode, not training mode
    
    return _model, _preprocess, _tokenizer, _device

import tomllib
from huggingface_hub import hf_hub_download
from llama_cpp import Llama
from halo import Halo

class LocalLLM:
    def __init__(self, config_path: str = "config.toml"):
        with open(config_path, "rb") as f:
            config = tomllib.load(f)

        repo_id = config["models"]["llm_repo"]
        filename = config["models"]["llm_filename"]

        model_path = hf_hub_download(repo_id=repo_id, filename=filename)
            
        # ^ resolves from local cache without listing the repo, if already downloaded.
        # why doesnt it work normally like it does with the others? I dont know.

        try:
            with Halo(text="\033[2mloading model (GPU)\033[0m", spinner="dots"):
                self.model = Llama(
                    model_path=model_path,
                    n_ctx=4096,
                    n_gpu_layers=-1,
                    verbose=False,
                )
            print("Ready!")

        except Exception as e:
            print(f"GPU load failed, falling back to CPU...")
            logger.log(f"[ERROR] GPU load failed: {e}")
            with Halo(text="\033[2mloading model (CPU)\033[0m", spinner="dots"):
                self.model = Llama(
                    model_path=model_path,
                    n_ctx=4096,
                    n_gpu_layers=0,
                    verbose=False,
                )
            print("Ready! (CPU)")

    def generate(self, prompt: str) -> str:
        response = self.model.create_chat_completion(
            messages=[{"role": "user", "content": prompt}]
        )
        return response["choices"][0]["message"]["content"]