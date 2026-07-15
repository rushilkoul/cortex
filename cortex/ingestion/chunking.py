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

from tree_sitter import Parser, Language
from tree_sitter_python import language as py_language
from tree_sitter_cpp import language as cpp_language


# Node types we treat as chunkable "units" per language.
# Keep this simple: top-level functions/methods and classes.
LANGUAGE_NODE_TYPES = {
    "python": {"function_definition", "class_definition"},
    "cpp": {"function_definition", "class_specifier", "struct_specifier"},
}

LANGUAGE_BUILDERS = {
    "python": Language(py_language()),
    "cpp": Language(cpp_language()),
}

EXTENSION_TO_LANGUAGE = {
    ".py": "python",
    ".cpp": "cpp",
    ".hpp": "cpp", 
    ".h": "cpp",
}


def get_parser(language_name: str) -> Parser:
    parser = Parser(LANGUAGE_BUILDERS[language_name])
    return parser


def extract_units(code: str, language_name: str) -> list[str]:
    """
    Parses code and extracts top-level chunkable units (functions/classes)
    as raw source text. Falls back to the whole file as one unit if
    no recognizable nodes are found.
    """
    parser = get_parser(language_name)
    tree = parser.parse(code.encode("utf-8"))
    wanted_types = LANGUAGE_NODE_TYPES[language_name]

    units = []

    def walk(node):
        if node.type in wanted_types:
            units.append(code[node.start_byte:node.end_byte])
            return  # don't descend into it further (keep it as one unit)
        for child in node.children:
            walk(child)

    walk(tree.root_node)

    if not units:
        units = [code]  # fallback: whole file as one unit

    return units


def chunk_code(code: str, file_extension: str) -> list[str]:
    with open("./config.toml", "rb") as f:
        config = tomllib.load(f)
    
    tokens_per_chunk = config["chunker"]["tokens_per_chunk"]
    chunk_overlap = config["chunker"]["chunk_overlap"]
    """
    Chunks a code file into pieces of up to `tokens_per_chunk` tokens,
    keeping functions/classes whole where possible. Packs small units
    together; splits oversized units at the token level as a fallback.
    """
    language_name = EXTENSION_TO_LANGUAGE.get(file_extension.lower())
    if language_name is None:
        units = [code]  # unsupported language: treat whole file as one unit
    else:
        units = extract_units(code, language_name)

    chunks = []
    current_parts = []
    current_count = 0

    def flush():
        if current_parts:
            chunks.append("\n\n".join(current_parts))

    for unit in units:
        unit_tokens = tokenize(unit)
        unit_len = len(unit_tokens)

        # Oversized unit: token-slice it as a last resort.
        if unit_len > tokens_per_chunk:
            flush()
            current_parts.clear()
            current_count = 0
            for i in range(0, unit_len, tokens_per_chunk):
                chunks.append(detokenize(unit_tokens[i:i + tokens_per_chunk]))
            continue

        if current_count + unit_len > tokens_per_chunk and current_parts:
            flush()
            current_parts = []
            current_count = 0

        current_parts.append(unit)
        current_count += unit_len

    flush()
    return chunks
