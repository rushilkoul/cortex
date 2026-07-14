from halo import Halo
import signal
import sys
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from cortex.shared.logger import logger
from cortex.reasoning.prompt import build_prompt

def start_shell():
    """Opens cortex in a TUI shell"""
    console = Console()

    with Halo(text="\033[2mloading models...\033[0m", spinner="dots"):
        from cortex.shared.models import start_server, stop_server, get_clip, get_embedder, LocalLLM
        get_embedder()
        get_clip()
        llm = LocalLLM()

    def _handle_exit(signum, frame):
        stop_server()
        sys.exit(0)

    signal.signal(signal.SIGINT, _handle_exit)
    signal.signal(signal.SIGTERM, _handle_exit)
    
    with Halo(text="\033[2mstarting Chroma server\033[0m", spinner="dots"):
        start_server()

    from cortex.ingestion.watcher import start_watcher, stop_watcher
    from cortex.retrieval.search import search
    
    with Halo(text="\033[2mstarting file watcher\033[0m", spinner="dots"):
        observer = start_watcher()

    print("Welcome to Cortex!")
    while True:
        query = input("\033[96m>\033[0m ")
        if query == "/exit":
            stop_watcher(observer)
            stop_server()
            return 0

        with Halo(text="\033[2mPondering...\033[0m", spinner="dots"):
            results = search(query, k=5)
            prompt = build_prompt(query, results)
            answer = llm.generate(prompt)
        console.print(Panel(Markdown(answer), border_style="dim", subtitle="/sources to view sources", subtitle_align="right"))
        print()