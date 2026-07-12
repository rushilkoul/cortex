# reasoning/prompt.py
def build_prompt(query: str, results: list[dict]) -> str:
    if not results:
        return f"""The user asked: "{query}"

No relevant files were found on their system for this query. Politely tell them nothing matching was found, and don't make anything up."""

    context_parts = []
    for r in results:
        if r["type"] == "text":
            context_parts.append(f"File: {r['file_path']}\n{r['content']}")
        elif r["type"] == "image":
            context_parts.append(f"File: {r['file_path']} (an image matched this query)")

    context = "\n\n---\n\n".join(context_parts)

    return f"""You are answering a question using ONLY the file excerpts below from the user's local computer. Do not use outside knowledge. If the excerpts don't contain enough to answer, say so honestly.

{context}

Question: {query}

Answer:"""