def build_prompt(query: str, results: list[dict]) -> str:
    if not results:
        return f"""
You are Cortex, an offline semantic memory assistant.

The user asked:

{query}

No relevant files were found.

Tell the user politely that nothing matching their query was found.
Do not invent any information.
""".strip()

    context_parts = []

    for r in results:

        if r["type"] == "text":
            context_parts.append(
                f"""
==========================
TEXT FILE

Path:
{r['file_path']}

Content:
{r['content']}
"""
            )

        elif r["type"] == "image":
            context_parts.append(
                f"""
==========================
IMAGE FILE

Path:
{r['file_path']}

Note:
This image matched the semantic search.
"""
            )

    context = "\n".join(context_parts)

    return f"""
You are Cortex, an offline semantic memory assistant.

Your task is to answer the user's question ONLY using the retrieved context below.

Rules:
- Only use the retrieved context.
- Do not use outside knowledge.
- Never invent file names.
- If the answer cannot be determined, clearly say so.
- Mention relevant file paths whenever helpful.

Retrieved Context:

{context}

==========================

USER QUESTION

{query}

==========================

ANSWER:
""".strip()