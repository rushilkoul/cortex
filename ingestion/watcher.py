import os
import time
import tomllib
from watchdog import events
from watchdog.observers import Observer

class EventHandler(events.FileSystemEventHandler):
    #def on_any_event(self, event: events.FileSystemEvent) -> None:
        #print("Untracked event occured")

    def on_created(self, event: events.DirCreatedEvent | events.FileCreatedEvent) -> None:
        if event.is_directory:
            print(f"[DIR CREATED] {event.src_path}")
        else:
            print(f"[FILE CREATED] {event.src_path}")

    def on_deleted(self, event: events.DirDeletedEvent | events.FileDeletedEvent) -> None:
        if event.is_directory:
            print(f"[DIR DELETED] {event.src_path}")
        else:
            print(f"[FILE DELETED] {event.src_path}")

    def on_modified(self, event: events.DirModifiedEvent | events.FileModifiedEvent) -> None:
        if event.is_directory:
            print(f"[DIR MODIFIED] {event.src_path}")
        else:
            print(f"[FILE MODIFIED] {event.src_path}")
    
    def on_moved(self, event: events.DirMovedEvent | events.FileMovedEvent) -> None:
        if event.is_directory:
            print(f"[DIR MOVED] {event.src_path} ==> {event.dest_path}")
        else:
            print(f"[FILE MOVED] {event.src_path} ==> {event.dest_path}")
    
event_handler = EventHandler()
observer = Observer()

with open("./config.toml", "rb") as f:
    config = tomllib.load(f)

directories = config["tracker"]["directories"]

for item in directories:
    
    path = os.path.expanduser(item)
    observer.schedule(event_handler, path, recursive=True)

# observer.schedule(event_handler, ".", recursive=True)
# observer.schedule(event_handler, "~/Downloads", recursive=True)
observer.start()

try:
    while True:
        time.sleep(1)
finally:
    observer.stop()
    observer.join()
