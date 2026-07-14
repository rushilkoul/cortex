import threading
import webview
from pathlib import Path
import getpass
from collections import deque

UI_DIR = Path(__file__).parent / "static"

class Api:
    def __init__(self):
        self.llm = None
        self._loading = False
       
        self.chat_history = deque(maxlen=10)

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

def start_ui():
    from cortex.shared.models import start_server, stop_server
    from cortex.ingestion.watcher import start_watcher

    start_server()
    observer = start_watcher()
    import signal
    import sys

    def _handle_exit(signum, frame):
        stop_server()
        sys.exit(0)

    signal.signal(signal.SIGINT, _handle_exit)
    signal.signal(signal.SIGTERM, _handle_exit)

    api = Api()
    webview.create_window("Cortex", str(UI_DIR / "index.html"), js_api=api, width=900, height=700)
    try:
        webview.start(gui="qt")
    finally:
        observer.stop()
        observer.join()
        stop_server()