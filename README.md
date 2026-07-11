# Cortex

```bash
uv venv
source .venv/bin/activate

# this will take a second. also makes the project like 5 gigs right off the bat lmao
uv pip install -r requirements.txt
```

download MiniLM model:

DO THIS PEHLE SE. `test.py` runs in offline mode and will crash if you run it without running this first 
```
python cacheMiniLM.py
``` 
at `~/.cache/huggingface/hub/`

update paths, run:
```
python test.py
```