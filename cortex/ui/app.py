import threading
import webview
from pathlib import Path
import getpass
from collections import deque

import tomllib
import tomlkit
import os
import subprocess
from sys import platform

CONFIG_PATH = "config.toml"
UI_DIR = Path(__file__).parent / "static"

class Api:
    def __init__(self):
        self.llm = None
        self._loading = False
        self._warm_up_lock = threading.Lock()
        self._warm_up_complete = threading.Event()
        self._llm_lock = threading.RLock()
       
        self.chat_history = deque(maxlen=20)

    def whoami(self) -> str:
        return getpass.getuser()

    def _ensure_llm(self):
        if self.llm is None:
            with self._llm_lock:
                if self.llm is None:
                    from cortex.shared.models import LocalLLM
                    self.llm = LocalLLM()
        return self.llm

    def warm_up(self):
        """Load models once without blocking pywebview's UI thread."""
        with self._warm_up_lock:
            if self._loading:
                return
            self._loading = True
            self._warm_up_complete.clear()

        def _load():
            from cortex.shared.models import warm_up_models

            try:
                models = warm_up_models(llm_factory=self._ensure_llm)
                self.llm = models.get("llm")
            finally:
                with self._warm_up_lock:
                    self._loading = False
                    self._warm_up_complete.set()

        threading.Thread(target=_load, daemon=True).start()

    def wait_for_warm_up(self) -> None:
        self._warm_up_complete.wait()

    def _rewrite_search_query(self, query: str) -> str:
        """Resolve conversational shorthand before embedding the query."""
        history = list(self.chat_history)[-6:]
        if history:
            conversation = "\n".join(
                f"{entry['role']}: {entry['content'][-800:]}"
                for entry in history
            )
        else:
            conversation = "(No previous conversation.)"

        prompt = f"""Conversation:
{conversation}

User request: {query}

Standalone retrieval query:"""

        try:
            rewritten = self._ensure_llm().rewrite_query(prompt)
        except Exception:
            return query

        rewritten = " ".join(rewritten.strip().strip('"').split())
        if not rewritten or len(rewritten) > 240:
            return query
        return rewritten

    def rewrite_query(self, query: str) -> str:
        """Public pywebview endpoint for the visible rewrite stage."""
        return self._rewrite_search_query(query)

    def search_rewritten(self, query: str) -> list[dict]:
        """Search an already-normalized retrieval query."""
        from cortex.retrieval.search import search
        from cortex.ingestion.clip import make_thumbnail_base64

        results = search(query, k=5)
        for r in results:
            if r["type"] == "image":
                try:
                    r["thumbnail"] = make_thumbnail_base64(r["file_path"])
                except Exception:
                    r["thumbnail"] = None
        return results

    def search_only(self, query: str) -> list[dict]:
        """Compatibility endpoint for callers that do not render stages."""
        return self.search_rewritten(self._rewrite_search_query(query))

    def _record_exchange(self, query: str, answer: str) -> None:
        self.chat_history.append({"role": "User", "content": query})
        self.chat_history.append({"role": "Cortex", "content": answer})

    def generate_answer(self, query: str, results: list[dict]) -> str:
        from cortex.reasoning.prompt import build_prompt

        self._ensure_llm()
        history_list = list(self.chat_history)
        prompt = build_prompt(query, results, history_list)

        answer = self.llm.generate(prompt)

        self._record_exchange(query, answer)

        return {"answer": answer, "results": results}

    # backwards compatibility for CLI mode
    def ask(self, query: str) -> dict:
        from cortex.retrieval.search import search
        from cortex.reasoning.prompt import build_prompt

        results = search(query, k=5)
        self._ensure_llm()
        history_list = list(self.chat_history)
        prompt = build_prompt(query, results, history_list)
        answer = self.llm.generate(prompt)
        self._record_exchange(query, answer)

        from cortex.ingestion.clip import make_thumbnail_base64
        for r in results:
            if r["type"] == "image":
                try:
                    r["thumbnail"] = make_thumbnail_base64(r["file_path"])
                except Exception:
                    r["thumbnail"] = None

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
    
    def open_file(self, path: str):
        try:
            if platform.startswith("win"):
                os.startfile(path)
            elif platform == "Darwin":
                subprocess.run(["open", path])
            else:
                subprocess.run(["xdg-open", path])
        except Exception as e:
            return {"ok": False, "error": str(e)}
        return {"ok": True}

def start_ui():
    api = Api()
    window = webview.create_window("Cortex", str(UI_DIR / "index.html"), js_api=api, width=900, height=700)
    api.window = window

    observer = None
    observer_lock = threading.Lock()

    def _start_watcher_after_warm_up() -> None:
        nonlocal observer
        # Bulk indexing invokes the same embedding models. Let the dedicated
        # warm-up load weights first instead of competing for disk, CPU, and
        # GPU initialization during application startup.
        api.wait_for_warm_up()
        from cortex.ingestion.watcher import start_watcher

        started_observer = start_watcher()
        with observer_lock:
            observer = started_observer

    def _start_services() -> None:
        # pywebview invokes this function in a worker thread before it creates
        # the native window, so wait for the actual display event first.
        window.events.shown.wait()
        from cortex.shared.models import start_server

        start_server()
        api.warm_up()
        threading.Thread(target=_start_watcher_after_warm_up, daemon=True).start()

    try:
        webview.start(_start_services, gui="qt", private_mode=False)
    finally:
        with observer_lock:
            active_observer = observer
        if active_observer is not None:
            active_observer.stop()
            active_observer.join()

        from cortex.shared.models import stop_server
        stop_server()
