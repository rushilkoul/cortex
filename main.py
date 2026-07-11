import atexit
from shared.models import start_server, stop_server
from ingestion.watcher import start_watcher

from retrieval.search import search_text, search_image

atexit.register(stop_server)

start_server()
observer = start_watcher()

print("Welcome to Cortex!")

while True:
    query = input("> ")
    results = search_text(query)

    # need to build a threshold for the score. we eventually want mixed queries 
    # so this is probably not the way. i should be searching for both
    # and then capping at a threshold specific to CLIP or text 
    # (should be present in the search functionsthemselves) 
    if len(results) == 0: results = search_image(query)

    for r in results:
        print(r)
        print("-"*40)
