# need to do this to always use cached version and not look online every time. saves latency
import os
import threading
os.environ["HF_HUB_OFFLINE"] = "1"

from concurrent.futures import ThreadPoolExecutor, as_completed
from chromadb.config import Settings

import chromadb
import subprocess
import time

from cortex.shared.logger import logger

_server_process = None
_embedder_lock = threading.RLock()
_client_lock = threading.RLock()
_clip_lock = threading.RLock()

def start_server():
    global _server_process

    try:
        test_client = chromadb.HttpClient(host="localhost", port=8000)
        test_client.heartbeat()
        logger.log("[LOG] Reusing already-running Chroma server.")
        return
    except Exception:
        pass  # nothing running, safe to start one

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
        with _embedder_lock:
            if _embedder is None:
                _embedder = SentenceTransformer("all-MiniLM-L6-v2")
    return _embedder

def get_client():
    global _client
    if _client is None:
        with _client_lock:
            if _client is None:
                i = 0; 
                while i < 50:
                    try:                        
                        _client = chromadb.HttpClient(host="localhost", port=8000, settings=Settings(anonymized_telemetry=False))
                        _client.heartbeat()
                        logger.log("[LOG] Client instantiated.")
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
        with _clip_lock:
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
from llama_cpp import Llama, llama_print_system_info, llama_supports_gpu_offload
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

        # `n_gpu_layers=-1` is only meaningful when the installed llama.cpp
        # binary was compiled with a GPU backend.  It otherwise quietly runs on
        # CPU, so report the backend before loading anything.
        system_info = llama_print_system_info().decode("utf-8", errors="replace")
        gpu_offload_supported = bool(llama_supports_gpu_offload())
        try:
            import torch
            torch_cuda_available = torch.cuda.is_available()
        except Exception:
            torch_cuda_available = False

        backend = "GPU" if gpu_offload_supported else "CPU"
        diagnostic = (
            "[LLM DEBUG] "
            f"llama.cpp backend={backend}; "
            f"gpu_offload_supported={gpu_offload_supported}; "
            f"torch_cuda_available={torch_cuda_available}; "
            f"system_info={system_info}"
        )
        print(diagnostic)
        logger.log(diagnostic)

        requested_gpu_layers = -1 if gpu_offload_supported else 0

        try:
            with Halo(text=f"\033[2mloading model ({backend})\033[0m", spinner="dots"):
                self.model = Llama(
                    model_path=model_path,
                    n_ctx=4096,
                    n_gpu_layers=requested_gpu_layers,
                    verbose=False,
                )
            load_diagnostic = (
                "[LLM DEBUG] "
                f"loaded backend={backend}; "
                f"requested_gpu_layers={requested_gpu_layers}"
            )
            print(load_diagnostic)
            logger.log(load_diagnostic)
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


def warm_up_models(
    include_llm: bool = True, llm_factory=None
) -> dict[str, object | None]:
    """
    load independent runtime resources concurrently
    """
    tasks = {
        "client": get_client,
        "embedder": get_embedder,
        "clip": get_clip,
    }

    if include_llm:
        tasks["llm"] = llm_factory or LocalLLM

    results: dict[str, object | None] = {}
    started_at = time.perf_counter()

    with ThreadPoolExecutor(max_workers=len(tasks)) as executor:
        future_to_name = {executor.submit(fn): name for name, fn in tasks.items()}

        for future in as_completed(future_to_name):
            name = future_to_name[future]
            try:
                results[name] = future.result()
                logger.log(
                    f"[LOG] Warm-up {name} finished in "
                    f"{time.perf_counter() - started_at:.2f}s."
                )
            except Exception as exc:
                logger.log(f"[ERROR] warm_up {name} failed: {exc}")
                results[name] = None

    return results
