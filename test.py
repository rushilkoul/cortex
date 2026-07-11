# need to do this to always use cached version and not look online every time. saves latency
import os
os.environ["HF_HUB_OFFLINE"] = "1"

from pathlib import Path
from retrieval.chunking import chunk_markdown # kavya ke merge ke baad move this into ingestion.chunking
from retrieval.store import needs_indexing, store_chunks
from retrieval.search import search_text

file_path = "/home/rushil/Desktop/Projects/velvet/docs/widgets.md"

if needs_indexing(file_path):
    text = Path(file_path).read_text(encoding="utf-8")
    chunks = chunk_markdown(text) # OR use chunk_text if youre pointing to text. extension basis par choose karna later

    # # present for debugging. not always needed
    # print(f"Split into {len(chunks)} chunks")
    # for i, c in enumerate(chunks):
    #     print(f"--- chunk {i} ({len(c)} chars) ---")
    #     print(c[:100], "...")

    store_chunks(file_path, chunks)
else:
    print("unchanged, skipping", file_path)

results = search_text("how do i add images")
for r in results:
    print(r["content"])