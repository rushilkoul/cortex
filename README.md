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
at `~/.cache/huggingface/hub/`. around a 1.7 GB download for 3 models

## current state: CLI

```bash
alias cortex="python main.py"
```
###### ~~(you dont need to do this but it is just so much cooler if you do)~~
otherwise just use python main.py instead, everything else applies:

```bash
cortex --help

cortex info
cortex track <dir>
cortex untrack <dir>

# run the main file
cortex 
```

talk to llm (separate from main pipeline rn):
```bash
python -m reasoning.test_reasoning
```

we need a less censored model. current one is buns.