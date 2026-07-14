from halo import Halo
import sys
import tomllib

with open("./config.toml", "rb") as f:
    config = tomllib.load(f)

llm_repo = config["models"]["llm_repo"]
llm_filename = config["models"]["llm_filename"]


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
            "text": f"Caching LLM ({llm_repo})...",
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
        repo_id=llm_repo,
        filename=llm_filename,
        n_ctx=4096,
        n_gpu_layers=-1,
        verbose=False,
    )


if __name__ == "__main__":
    download_models()