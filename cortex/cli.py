import typer
import tomlkit
from cortex.ingestion.chunking import chunk_markdown
from cortex.shared.logger import logger
from cortex.reasoning.prompt import build_prompt

app = typer.Typer()

# main
# def start_shell():
#     """Opens cortex in a TUI shell"""
#     import atexit
#     from halo import Halo
#     from rich.console import Console
#     from rich.markdown import Markdown
#     from rich.panel import Panel

#     console = Console()

#     with Halo(text="\033[2mloading models...\033[0m", spinner="dots"):
#         from cortex.shared.models import start_server, stop_server, get_clip, get_embedder, LocalLLM
#         get_embedder()
#         get_clip()
#         llm = LocalLLM()

#     atexit.register(stop_server)
#     with Halo(text="\033[2mstarting Chroma server\033[0m", spinner="dots"):
#         start_server()

#     from cortex.ingestion.watcher import start_watcher, stop_watcher
#     from cortex.retrieval.search import search
    
#     with Halo(text="\033[2mstarting file watcher\033[0m", spinner="dots"):
#         observer = start_watcher()

#     print("Welcome to Cortex!")
#     while True:
#         query = input("\033[96m>\033[0m ")
#         if query == "/exit":
#             stop_watcher(observer)
#             stop_server()
#             return 0

#         with Halo(text="\033[2mPondering...\033[0m", spinner="dots"):
#             results = search(query, k=5)
#             prompt = build_prompt(query, results)
#             answer = llm.generate(prompt)
#         console.print(Panel(Markdown(answer), border_style="dim", subtitle="/sources to view sources", subtitle_align="right"))
#         print()

# cortex info
@app.command()
def info():
    """Shows info about files & directories being tracked"""
    with open("config.toml", "r") as f:
        data = tomlkit.parse(f.read())
    
    for item in data["tracker"]["directories"]:
        print(item)

# cortex track [PATH]
@app.command()
def track(path: str):
    """Start tracking a directory"""
    with open("config.toml", "r") as f:
        data = tomlkit.parse(f.read())

    with open("config.toml", "w") as f:
        data["tracker"]["directories"].append(path)
        f.write(tomlkit.dumps(data))

    typer.echo(f"Started tracking {path}")

# cortex untrack [PATH]
@app.command()
def untrack(path: str):
    """Stop tracking a directory"""
    with open("config.toml", "r") as f:
        data = tomlkit.parse(f.read())

    with open("config.toml", "w") as f:
        data["tracker"]["directories"].remove(path)
        f.write(tomlkit.dumps(data))
    
    typer.echo(f"Stopped tracking {path}")

@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    download: bool = typer.Option(False, "--download", help="Downloads and caches the required models."),
):
    """Launch the Cortex GUI"""
    if download:
        from cortex.downloader import download_models
        download_models()
        raise typer.Exit()

    if ctx.invoked_subcommand == None:
        
        from cortex.ui.app import start_ui
        start_ui()


@app.command()
def shell():
    from cortex.shell.shell import start_shell
    start_shell()


if __name__ == "__main__":
    app()
