# Cortex

A local-first semantic search and Q&A assistant for your own files. Cortex watches folders you choose, indexes your notes and images, and turns them into something you can actually search by meaning: all powered by models that run entirely on your machine.

<br>

## Contents
- [Problem](#problem)
- [Solution](#solution)
- [On-Device AI Usage](#on-device-ai-usage)
- [Tech Stack](#tech-stack)
- [Setup and Usage](#setup-and-usage)
- [Demo and Screenshots](#demo-and-screenshots)
- [License](#license)
- [Known Limitations and Roadmap](#known-limitations-and-roadmap)

<br>

## Problem
Most of what we "know" is scattered across markdown notes, screenshots, and images on our own computers, and it's nearly impossible to search by meaning instead of exact keywords. Existing AI note-taking tools solve this by sending your files to the cloud, which means giving up privacy just to get decent search.

<br>

## Solution
Cortex runs a full retrieval-augmented generation (RAG) pipeline locally. It watches tracked directories for your files, embeds their content into a local vector database as they're created or edited, and lets you query that knowledge base in natural language from a simple CLI. Relevant excerpts are retrieved and handed to a local LLM, which answers using only what it found on your system - nothing leaves your machine, and nothing is made up.

<br>

## On-Device AI Usage
Everything in Cortex's pipeline runs locally, with no calls to external APIs:
 
- **Text embeddings** — [`all-MiniLM-L6-v2`](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2) via `sentence-transformers`, used to embed markdown chunks and search queries.
- **Image embeddings** — OpenCLIP `ViT-B-32` (`laion2b_s34b_b79k` weights) via `open_clip_torch`, used to embed images and match them against text queries in the same vector space.
- **Answer generation** — a local GGUF LLM (default: `Qwen2.5-1.5B-Instruct`) served through `llama-cpp-python`. Automatically uses GPU offload when a CUDA device is available, and falls back to CPU otherwise.
- **Vector storage** — a local [ChromaDB](https://www.trychroma.com/) instance, spun up as a subprocess and queried over `localhost`.
- **Relevance filtering** — retrieved results are filtered against a calibrated cosine-distance threshold before ever reaching the LLM, so an unrelated query correctly returns "nothing relevant found" instead of forcing irrelevant sources into the answer. Text (`similarity_threshold = 0.7`) and images (`image_similarity_threshold = 0.75`) use separate thresholds — CLIP's image-text similarity runs lower than text-text similarity even for correct matches (the "modality gap"), so a looser cutoff is needed for images. Both were calibrated empirically against labeled relevant/irrelevant test queries; see `calibrate.py` for the methodology.
The LLM, filename, and repo can be swapped by editing `config.toml`.
 
<br>

## Tech Stack
 
| Category | Tools |
|---|---|
| Language | Python |
| CLI | [Typer](https://typer.tiangolo.com/) |
| File watching | [watchdog](https://pypi.org/project/watchdog/) |
| Vector DB | [ChromaDB](https://www.trychroma.com/) |
| Embeddings (text) | `sentence-transformers` (`all-MiniLM-L6-v2`) |
| Embeddings (image) | `open_clip_torch` (`ViT-B-32`) |
| LLM inference | `llama-cpp-python` (GGUF, Qwen2.5-1.5B-Instruct by default) |
| Config | TOML (`tomlkit`) |
 
<br>

## Setup and Usage
```bash
# 1. create and activate a virtual environment
uv venv
source .venv/bin/activate
 
# 2. install dependencies (~5GB) and cortex
uv sync
 
# 3. cache the required models before first run
cortex --download
```
Once set up, you can run Cortex directly:
 
```bash
cortex --help

cortex info              # show tracked directories
cortex track <dir>       # start tracking a directory
cortex untrack <dir>     # stop tracking a directory
 
cortex shell             # launch the interactive shell
cortex                   # launch the super cool GUI
```
 
Inside the shell, type a natural-language question and Cortex will search your indexed files and generate an answer using the local LLM.


### Running the model on CUDA
By complete default, the program may be running on your CPU.
check logs.txt, which whether the CPU or GPU is being used. 
If you have an NVIDIA GPU:

ensure CUDA toolkit and `nvcc` are installed and added to path.

run:
```
CMAKE_ARGS="-DGGML_CUDA=on" \
uv pip install \
  --python .venv/bin/python \
  --reinstall-package llama-cpp-python \
  --no-cache \
  llama-cpp-python
```

compiling `llama-cpp-python` for CUDA. you should see immense performance improvements with the LLM.

<br>

## Demo and Screenshots
 
<div>
 <h1><b>RUSHIL IDHAR DEMO VIDEOS AUR SCREENSHOTS</b></h1>
</div>

<br>
 
## License
 
[GNU General Public License v3.0 (GPLv3)](LICENSE)

<br>

## Known Limitations and Roadmap
### Completed
- Desktop GUI (light and dark mode)
- Source citations
- Image indexing and search (CLIP)
- Relevance threshold filtering (separately tuned for text and image results)
- Bulk re-index of pre-existing files on startup
- PDF, DOCX, and TXT document support
  
### Known Limitations
<div>
 <h1><b>RUSHIL IDHAR LIMITATIONS LIKH DENA YAAD SE</b></h1>
</div>

### Planned
- Model selector
- Additional document types
