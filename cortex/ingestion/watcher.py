import ctypes
import os
import time
import tomllib
from watchdog import events
from watchdog.observers import Observer
from cortex.ingestion.store import try_index
from cortex.shared.logger import logger
from pathlib import Path

class EventHandler(events.FileSystemEventHandler):

    def dispatch(self, event):
        # making sure the file isn't hidden OR isn't inside a hidden directory
        path = Path(event.src_path)

        # skipping dot files (linux and windows both)
        for part in path.parts:
            if part.startswith("."):
                logger.log(f"[SKIPPED DOTFILE] {path}")
                return

        # FOR WINDOWS SPECIFICALLY - skipping "hidden" files !!!
        # NOTE: GetFileAttributesW makes a system call in every loop iteration, which isn't very performative
        # we might want to fix this later by caching known hidden directories
        # P.S idfk what this code does or what im doing
        if os.name == "nt":
            FILE_ATTRIBUTE_HIDDEN = 0x2
            current = path
            while current.parent != current:  # never check the drive root itself
                attrs = ctypes.windll.kernel32.GetFileAttributesW(str(current))
                if attrs != -1 and attrs & FILE_ATTRIBUTE_HIDDEN:
                    logger.log(f"[SKIPPED HIDDEN FILE (Windows)] {path}")
                    return
                current = current.parent

        super().dispatch(event)

    def on_created(self, event: events.DirCreatedEvent | events.FileCreatedEvent) -> None:
        if event.is_directory:
            logger.log(f"[DIR CREATED] {event.src_path}")
        else:
            logger.log(f"[FILE CREATED] {event.src_path}")

            try_index(event.src_path)

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
            try_index(event.src_path)
    
    # when a file is moved OR *renamed*
    def on_moved(self, event: events.DirMovedEvent | events.FileMovedEvent) -> None:
        if event.is_directory:
            logger.log(f"[DIR MOVED] {event.src_path} ==> {event.dest_path}")
        else:
            logger.log(f"[FILE MOVED] {event.src_path} ==> {event.dest_path}")

# starts tracking files
def start_watcher():
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
    logger.log("[LOG] Watcher started.")
    return observer

# in case we want to run this file separately (For testing)
# python -m ingestion.watcher
if __name__ == "__main__":
    observer = start_watcher()

    # this is necessary to keep the program running
    try:
        while True:
            time.sleep(1)
    finally:
        observer.stop()
        observer.join()
