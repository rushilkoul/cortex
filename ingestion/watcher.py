import os
import time
import tomllib
from watchdog import events
from watchdog.observers import Observer
from ingestion.store import needs_indexing, store_chunks
from ingestion.chunking import chunk_markdown
from shared.logger import logger

from pathlib import Path

class EventHandler(events.FileSystemEventHandler):
    #def on_any_event(self, event: events.FileSystemEvent) -> None:
        #print("Untracked event occured")

    def on_created(self, event: events.DirCreatedEvent | events.FileCreatedEvent) -> None:
        if event.is_directory:
            logger.log(f"[DIR CREATED] {event.src_path}")
        else:
            logger.log(f"[FILE CREATED] {event.src_path}")
            if needs_indexing(event.src_path):
                text = Path(event.src_path).read_text(encoding="utf-8")
                chunks = chunk_markdown(text)
                store_chunks(event.src_path, chunks)
            else:
                print("unchanged, skipping", event.src_path)

    def on_deleted(self, event: events.DirDeletedEvent | events.FileDeletedEvent) -> None:
        if event.is_directory:
            logger.log(f"[DIR DELETED] {event.src_path}")
        else:
            logger.log(f"[FILE DELETED] {event.src_path}")

    def on_modified(self, event: events.DirModifiedEvent | events.FileModifiedEvent) -> None:
        if event.is_directory:
            logger.log(f"[DIR MODIFIED] {event.src_path}")
        else:
            logger.log(f"[FILE MODIFIED] {event.src_path}")
            if needs_indexing(event.src_path):
                text = Path(event.src_path).read_text(encoding="utf-8")
                chunks = chunk_markdown(text)
                store_chunks(event.src_path, chunks)
            else:
                print("unchanged, skipping", event.src_path)
    
    # when a file is moved OR *renamed*
    def on_moved(self, event: events.DirMovedEvent | events.FileMovedEvent) -> None:
        if event.is_directory:
            print(f"[DIR MOVED] {event.src_path} ==> {event.dest_path}")
        else:
            print(f"[FILE MOVED] {event.src_path} ==> {event.dest_path}")
    
event_handler = EventHandler()
observer = Observer()

# loading which directories to track from the config file
with open("./config.toml", "rb") as f:
    config = tomllib.load(f)

directories = config["tracker"]["directories"]

for item in directories:
    path = os.path.expanduser(item)
    observer.schedule(event_handler, path, recursive=True)

observer.start()

# this is necessary to keep the program running
try:
    while True:
        time.sleep(1)
finally:
    observer.stop()
    observer.join()
