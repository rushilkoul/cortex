import typer
import tomlkit


app = typer.Typer()


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
