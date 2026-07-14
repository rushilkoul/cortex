import threading
import webview
from pathlib import Path
import getpass
from collections import deque

import tomllib
import tomlkit
import os

CONFIG_PATH = "config.toml"
UI_DIR = Path(__file__).parent / "static"

class Api:
    def __init__(self):
        self.llm = None
        self._loading = False
       
        self.chat_history = deque(maxlen=20)

    def whoami(self) -> str:
        return getpass.getuser()

    def _ensure_llm(self):
        if self.llm is None:
            from cortex.shared.models import LocalLLM
            self.llm = LocalLLM()

    def warm_up(self):
        """called once when the window opens, loads all models in the background."""
        if self._loading:
            return
        self._loading = True

        def _load():
            from cortex.shared.models import get_embedder, get_clip, get_client
            get_client()
            get_embedder()
            get_clip()
            self._ensure_llm()
            self._loading = False

        threading.Thread(target=_load, daemon=True).start()

    def ask(self, query: str) -> dict:
        from cortex.retrieval.search import search
        from cortex.reasoning.prompt import build_prompt

        self._ensure_llm()
        results = search(query, k=5)
        
        
        history_list = list(self.chat_history)
        prompt = build_prompt(query, results, history_list)
        
        answer = self.llm.generate(prompt)
        
        
        self.chat_history.append({"role": "User", "content": query})
        self.chat_history.append({"role": "Cortex", "content": answer})
        
        return {"answer": answer, "results": results}
    
    def list_directories(self) -> list[str]:
        with open(CONFIG_PATH, "rb") as f:
            config = tomllib.load(f)
        return config["tracker"]["directories"]

    def add_directory(self, path: str) -> dict:
        expanded = os.path.expanduser(path)
        if not os.path.isdir(expanded):
            return {"ok": False, "error": f"'{path}' is not a valid directory."}

        doc = tomlkit.parse(open(CONFIG_PATH).read())
        dirs = doc["tracker"]["directories"]

        if path in dirs:
            return {"ok": False, "error": f"Already tracking {path}"}

        dirs.append(path)
        with open(CONFIG_PATH, "w") as f:
            f.write(tomlkit.dumps(doc))

        # start watching it live, without requiring a restart
        from cortex.ingestion.watcher import add_watch_path
        add_watch_path(expanded)

        return {"ok": True, "path": path}

    def remove_directory(self, path: str) -> dict:
        doc = tomlkit.parse(open(CONFIG_PATH).read())
        dirs = doc["tracker"]["directories"]

        if path not in dirs:
            return {"ok": False, "error": f"Not currently tracking {path}"}

        dirs.remove(path)
        with open(CONFIG_PATH, "w") as f:
            f.write(tomlkit.dumps(doc))

        return {"ok": True, "path": path}
    
    def pick_folder(self) -> str | None:
        result = self.window.create_file_dialog(webview.FileDialog.FOLDER)
        if result and len(result) > 0:
            return result[0]
        return None

def start_ui():
    from cortex.shared.models import start_server, stop_server
    from cortex.ingestion.watcher import start_watcher

    start_server()
    observer = start_watcher()

    api = Api()
    window = webview.create_window("Cortex", str(UI_DIR / "index.html"), js_api=api, width=900, height=700)
    api.window = window 
    try:
        webview.start(gui="qt")
    finally:
        observer.stop()
        observer.join()
        stop_server()