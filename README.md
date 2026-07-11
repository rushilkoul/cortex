# Cortex

```bash
uv venv
source .venv/bin/activate

# this will take a second. also makes the project like 5 gigs right off the bat lmao
uv pip install -r requirements.txt
```

cache required models:

DO THIS PEHLE SE. `test.py` runs in offline mode and will crash if you run it without running this first 
```
python cacheMiniLM.py
``` 
at `~/.cache/huggingface/hub/`

## current state
- `config.toml`: add tracked paths here

kya maza agya. all you gotta do is run one file now
```
python main.py
```
starts the chromadb server, watchdog, and searcher all at the same time. exits cleanly too, even on KeyboardInterrupt and such


###### ~~yeah you need three separate terminals just to get this working ill fix it later shut up~~ NOT ANYMORE MUAHEHEHEHEH