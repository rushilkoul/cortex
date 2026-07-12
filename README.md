# Cortex

A local-first semantic search and Q&A assistant for your own files. Cortex watches folders you choose, indexes your notes and images, and turns them into something you can actually search by meaning — all powered by models that run entirely on your machine.

<br>

## Problem
Most of what we "know" is scattered across markdown notes, screenshots, and images on our own computers, and it's nearly impossible to search by meaning instead of exact keywords. Existing AI note-taking tools solve this by sending your files to the cloud, which means giving up privacy just to get decent search.

<br>

## Solution
Cortex runs a full retrieval-augmented generation (RAG) pipeline locally. It watches tracked directories for markdown and image files, embeds their content into a local vector database as they're created or edited, and lets you query that knowledge base in natural language from a simple CLI. Relevant excerpts are retrieved and handed to a local LLM, which answers using only what it found on your system - nothing leaves your machine, and nothing is made up.

<br>

## On-Device AI Usage
Everything in Cortex's pipeline runs locally, with no calls to external APIs:
 
- **Text embeddings** — [`all-MiniLM-L6-v2`](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2) via `sentence-transformers`, used to embed markdown chunks and search queries.
- **Image embeddings** — OpenCLIP `ViT-B-32` (`laion2b_s34b_b79k` weights) via `open_clip_torch`, used to embed images and match them against text queries in the same vector space.
- **Answer generation** — a local GGUF LLM (default: `Qwen2.5-1.5B-Instruct`) served through `llama-cpp-python`, downloaded once via the Hugging Face Hub and cached for fully offline use afterward. Automatically uses GPU offload when a CUDA device is available, and falls back to CPU otherwise.
- **Vector storage** — a local [ChromaDB](https://www.trychroma.com/) instance, spun up as a subprocess and queried over `localhost`.
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
 
# 2. install dependencies (~5GB, includes ML libraries)
uv pip install -r requirements.txt
 
# 3. cache the required models before first run (~1.7GB download)
python downloadmodels.py
```
Once set up, you can run Cortex directly:
 
```bash
python main.py --help
 
python main.py info              # show tracked directories
python main.py track <dir>       # start tracking a directory
python main.py untrack <dir>     # stop tracking a directory
 
python main.py                   # launch the interactive shell
```
 
Or, for convenience, alias it:
 
```bash
alias cortex="python main.py"
cortex
```
 
Inside the shell, type a natural-language question and Cortex will search your indexed files and generate an answer using the local LLM.
 
To test the reasoning module in isolation:
 
```bash
python -m reasoning.test_reasoning
```
<br>

## Demo and Screenshots
 
### **~~demo video aur screenshots idhar lagadena baad me~~**

<br>
 
## License
 
[GNU General Public License v3.0 (GPLv3)](LICENSE)
