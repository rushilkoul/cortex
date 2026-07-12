import typer
import tomlkit
from ingestion.chunking import chunk_markdown
from shared.logger import logger
from halo import Halo

from reasoning.prompt import build_prompt

app = typer.Typer()



# main
def start_shell():
    """Opens cortex in a TUI shell"""
    import atexit

    with Halo(text="\033[2mloading models...\033[0m", spinner="dots"):
        from shared.models import start_server, stop_server, get_clip, get_embedder, LocalLLM
        get_embedder()
        get_clip()
        llm = LocalLLM()

    atexit.register(stop_server)
    with Halo(text="\033[2mstarting Chroma server\033[0m", spinner="dots"):
        start_server()

    from ingestion.watcher import start_watcher
    from retrieval.search import search
    
    with Halo(text="\033[2mstarting file watcher\033[0m", spinner="dots"):
        observer = start_watcher()

    print("Welcome to Cortex!")
    while True:
        query = input("\033[96m>\033[0m ")
        with Halo(text="\033[2mPondering...\033[0m", spinner="dots"):
            results = search(query, k=5)
            prompt = build_prompt(query, results)
            answer = llm.generate(prompt)
        print(answer, "\n")
    

        # print("\033[2m")
        # for r in results:
        #     print(r)
        # print("\033[0m")

        


#------------------------------------------------------------------------------------------
#------------------------------------------------------------------------------------------

# cortex info
@app.command()
def info():
    """Shows info about files & directories being tracked"""
    with open("config.toml", "r") as f:
        data = tomlkit.parse(f.read())
    
    print("The following files/directories are being tracked:")
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
def main(ctx: typer.Context):
    if ctx.invoked_subcommand == None:
        start_shell()


if __name__ == "__main__":
    app()
