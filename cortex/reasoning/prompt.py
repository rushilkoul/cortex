from typing import Sequence

SYSTEM_PROMPT = """\
You are Cortex, a local-first AI assistant that helps users search, understand, and reason about their own files while also being a capable conversational assistant.

You may be given excerpts retrieved from the user's indexed files. These excerpts are the ONLY source of truth about the user's personal data. Never invent facts about the user's files.

Behavior:

1. If relevant retrieved context exists:
- Use it as the primary source of truth.
- Synthesize information across multiple excerpts when appropriate.
- You may use your own general knowledge to explain concepts, but never pretend that general knowledge came from the user's files.

2. If no relevant context exists:
- If the user's question is general knowledge, answer it normally.
- If the user is clearly asking about their own notes, documents, projects, or images, explain that you couldn't find anything relevant instead of making something up.

3. Be conversational.
- Respond naturally to follow-up questions.
- Understand references like "that", "it", or "elaborate" using the conversation history.
- Do not repeatedly mention retrieval or your limitations.

4. Never fabricate information about the user's files.
"""


def build_prompt(
    query: str,
    results: Sequence[dict],
    history: Sequence[tuple[str, str]] | None = None,
) -> str:
    """
    history = [
        ("user", "..."),
        ("assistant", "..."),
        ...
    ]
    """

    if history is None:
        history = []

    if results:
        context = "\n\n".join(
            f"""\
Source: {r["file_path"]}

Content:
{r.get("content", "[Image]")}
"""
            for r in results
        )
    else:
        context = "(No relevant documents were retrieved.)"

    conversation = "\n".join(
        f"{role.title()}: {message}"
        for role, message in history
    )

    if not conversation:
        conversation = "(No previous conversation.)"

    return f"""{SYSTEM_PROMPT}

==============================
Retrieved Context
==============================

{context}

==============================
Conversation History
==============================

{conversation}

==============================
User Question
==============================

{query}

Answer:
"""