import subprocess
from pathlib import Path
from ingestion.chunking import chunk_markdown
from ingestion.store import needs_indexing, store_chunks
from ingestion.watcher import start_watcher
from retrieval.search import search_text
from shared.logger import logger
from shared.models import start_server

# file_path = "/home/rushil/Desktop/Projects/velvet/docs/widgets.md"

# if needs_indexing(file_path):
#     text = Path(file_path).read_text(encoding="utf-8")
#     chunks = chunk_markdown(text) # OR use chunk_text if youre pointing to text. extension basis par choose karna later

#     # # present for debugging. not always needed
#     # print(f"Split into {len(chunks)} chunks")
#     # for i, c in enumerate(chunks):
#     #     print(f"--- chunk {i} ({len(c)} chars) ---")
#     #     print(c[:100], "...")

#     store_chunks(file_path, chunks)
# else:
#     print("unchanged, skipping", file_path)



# starting the chroma server in a subprocess

start_server()
observer = start_watcher()

while True:
    query = input("")
    results = search_text(query)
    for r in results:
        print(r["content"])

    print("-"*80)
