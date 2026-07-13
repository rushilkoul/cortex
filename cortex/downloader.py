from halo import Halo
import sys


def download_models():
    models = [
        {
            "name": "MiniLM",
            "text": "Caching MiniLM...",
            "fn": _download_minilm,
        },
        {
            "name": "OpenCLIP",
            "text": "Caching OpenCLIP model...",
            "fn": _download_openclip,
        },
        {
            "name": "LLM",
            "text": "Caching LLM (Qwen2.5-1.5B)...",
            "fn": _download_llm,
        },
    ]

    for model in models:
        spinner = Halo(text=model["text"], spinner="dots", color="cyan")
        spinner.start()
        try:
            model["fn"]()
            spinner.succeed(f"{model['name']} cached")
        except Exception as e:
            spinner.fail(f"{model['name']} failed: {e}")
            print(f"\nStopped after failure caching {model['name']}.", file=sys.stderr)
            sys.exit(1)

    print("\nAll models downloaded and cached successfully.")


def _download_minilm():
    from sentence_transformers import SentenceTransformer

    SentenceTransformer("all-MiniLM-L6-v2")


def _download_openclip():
    import open_clip

    open_clip.create_model_and_transforms(
        "ViT-B-32", pretrained="laion2b_s34b_b79k"
    )


def _download_llm():
    from llama_cpp import Llama

    Llama.from_pretrained(
        repo_id="Qwen/Qwen2.5-1.5B-Instruct-GGUF",
        filename="*q4_k_m.gguf",
        n_ctx=4096,
        n_gpu_layers=-1,
        verbose=False,
    )


if __name__ == "__main__":
    download_models()