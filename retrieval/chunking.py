import re

"""
simple text 500 character chunker
very naive but im going to use it for now
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