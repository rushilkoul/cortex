import re
import tomllib
from cortex.shared.models import get_embedder

# takes text as input and returns list of tokens

def tokenize(text: str) -> list[int]:
    model = get_embedder()
    tokenizer = model.tokenizer

    return tokenizer.encode(text, add_special_tokens=False)

def detokenize(tokens: list[int]) -> str:
    model = get_embedder()
    tokenizer = model.tokenizer

    return tokenizer.decode(tokens, skip_special_tokens=True)


def split_into_units(text: str) -> list[dict]:
    """Splits text into {"type": "code"|"text", "content": str} units.
    Code = fenced code blocks (kept whole). Text = paragraphs (split on blank lines)."""
    pattern = re.compile(r"```.*?```", re.DOTALL)
    units = []
    last_end = 0
    for match in pattern.finditer(text):
        before = text[last_end:match.start()]
        for para in [p.strip() for p in before.split("\n\n") if p.strip()]:
            units.append({"type": "text", "content": para})
        units.append({"type": "code", "content": match.group(0)})
        last_end = match.end()
    for para in [p.strip() for p in text[last_end:].split("\n\n") if p.strip()]:
        units.append({"type": "text", "content": para})
    return units


def chunk_text(text: str,) -> list[str]:
    """
    Packs paragraphs greedily into ~tokens_per_chunk-token chunks, with
    chunk_overlap tokens carried forward between chunks. Code blocks are
    atomic (never split, and overlap is skipped after one).
    """
    with open("./config.toml", "rb") as f:
        config = tomllib.load(f)
    
    tokens_per_chunk = config["chunker"]["tokens_per_chunk"]
    chunk_overlap = config["chunker"]["chunk_overlap"]

    units = split_into_units(text)
    step = tokens_per_chunk - chunk_overlap

    chunks = []
    current_parts = []
    current_count = 0
    last_was_code = False

    def flush(carry_overlap=True):
        nonlocal current_parts, current_count
        if not current_parts:
            return
        chunks.append("\n\n".join(current_parts))

        if not carry_overlap or last_was_code:
            current_parts, current_count = [], 0
            return

        body_tokens = tokenize(chunks[-1])
        if len(body_tokens) <= chunk_overlap:
            current_parts, current_count = [], 0
            return

        tail_tokens = body_tokens[-chunk_overlap:]
        tail_text = detokenize(tail_tokens)
        current_parts = [tail_text]
        current_count = len(tail_tokens)

    for unit in units:
        unit_tokens = tokenize(unit["content"])
        unit_len = len(unit_tokens)

        if unit["type"] == "code":
            if current_count + unit_len > tokens_per_chunk and current_parts:
                flush()
            current_parts.append(unit["content"])
            current_count += unit_len
            last_was_code = True
            if unit_len > tokens_per_chunk:
                flush(carry_overlap=False)  # oversized code: its own chunk, no overlap after
            continue

        last_was_code = False

        # Paragraph too big on its own: slide a token window across it.
        if unit_len > tokens_per_chunk:
            flush()
            for i in range(0, unit_len, step):
                piece = unit_tokens[i:i + tokens_per_chunk]
                chunks.append(detokenize(piece))
                if i + tokens_per_chunk >= unit_len:
                    break
            continue

        if current_count + unit_len > tokens_per_chunk and current_parts:
            flush()

        current_parts.append(unit["content"])
        current_count += unit_len

    flush(carry_overlap=False)  # nothing to carry into once we're done
    return chunks

"""
simple text 500 character chunker
very naive but im going to use it for now
"""
"""
def chunk_text(text: str, max_chars: int = 500) -> list[str]:
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks = []
    current = ""

    for p in paragraphs:
        if len(current) + len(p) <= max_chars:
            current += ("\n\n" if current else "") + p
        else:
            if current:
                chunks.append(current)
            current = p

    if current:
        chunks.append(current)

    return chunks
"""

# leaving a note for my teammates here:
# Its a good idea to chunk different kinds of files differently.
# structure matters. if the chunking is ass then the retrieval will be ass
# and if thats ass then what we feed the LLM is ass, therefore the output is ass
# garbage in, garbage out.

# this markdown chunker performs infinitely better than the 500 character chunker because its designed
# to specifically work with markdown structure.
# (should probably improve this to also parse markdown tables)
# whatever file types we end up adding support for, even if plain text encoded,
# its a good idea to write a specialized chunker for it.



"""
Splits markdown on headers (#, ##, ###), keeping each header
together with its content as one semantic chunk. falls back to 
paragraph splitting for any section thats still too big
"""
def chunk_markdown(text: str, max_chars: int = 300) -> list[str]:
    sections = re.split(r'(?=^#{1,3}\s)', text, flags=re.MULTILINE)

    chunks = []
    for section in sections:
        section = section.strip()
        if not section:
            continue

        if len(section) <= max_chars:
            chunks.append(section)
        else:
            # big section (e.g. a long "## how it works") — 
            # keep the header as its own mini-chunk for context,
            # then paragraph-split the rest
            lines = section.split("\n", 1)
            header = lines[0].strip()
            body = lines[1].strip() if len(lines) > 1 else ""

            if body:
                sub_chunks = chunk_text(body, max_chars)
                # prepend header to first sub-chunk so context isn't lost
                # (!!!!!!!!!!!!!!!!!!!)
                if sub_chunks:
                    sub_chunks[0] = f"{header}\n\n{sub_chunks[0]}"
                    chunks.extend(sub_chunks)
                else:
                    chunks.append(header)
            else:
                chunks.append(header)

    return chunks
