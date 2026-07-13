from halo import Halo

def download_models():
    with Halo(text="\033[2mCaching MiniLM...\033[0m", spinner="dots"):
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer("all-MiniLM-L6-v2")

    with Halo(text="\033[2mCaching OpenCLIP model...\033[0m", spinner="dots"):
        import open_clip

        model, _, preprocess = open_clip.create_model_and_transforms(
            "ViT-B-32",
            pretrained="laion2b_s34b_b79k"
        )

    with Halo(text="\033[2mCaching LLM...\033[0m", spinner="dots"):
        from llama_cpp import Llama

        llm = Llama.from_pretrained(
            repo_id="Qwen/Qwen2.5-1.5B-Instruct-GGUF",
            filename="*q4_k_m.gguf",
            n_ctx=4096,
            n_gpu_layers=-1,
            verbose=False,
        )
    
    print("Successfully downloaded and cached the models.")

if __name__ == "__main__":
    download_models()
