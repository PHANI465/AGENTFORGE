"""RAG helpers — embeddings, chunking, and similarity retrieval for an agent's
knowledge base.

Embeddings go through OpenAI's embeddings endpoint directly (api-gateway has
httpx but not litellm, and pulling in litellm just for this would be heavy).
That means RAG needs an OpenAI-compatible key; with any other provider key,
embedding calls fail and are handled gracefully (ingestion errors clearly,
retrieval silently skips so the agent still runs — just without extra context).
Vectors are stored as plain JSON arrays and scored in Python, which is fine at
knowledge-base scale (no pgvector needed).
"""

import math

import httpx

EMBED_MODEL = "text-embedding-3-small"
_OPENAI_EMBED_URL = "https://api.openai.com/v1/embeddings"
_CHUNK_CHARS = 800


def chunk_text(text: str, size: int = _CHUNK_CHARS) -> list[str]:
    """Split text into ~size-char chunks on paragraph/whitespace boundaries."""
    text = text.strip()
    if not text:
        return []
    paras = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks: list[str] = []
    buf = ""
    for p in paras:
        if len(buf) + len(p) + 2 <= size:
            buf = f"{buf}\n\n{p}" if buf else p
        else:
            if buf:
                chunks.append(buf)
            # A single oversized paragraph gets hard-split.
            while len(p) > size:
                chunks.append(p[:size])
                p = p[size:]
            buf = p
    if buf:
        chunks.append(buf)
    return chunks


async def embed_texts(texts: list[str], api_key: str) -> list[list[float]]:
    """Embed a batch of texts. Raises on a non-OpenAI-compatible key."""
    async with httpx.AsyncClient(timeout=httpx.Timeout(30)) as client:
        resp = await client.post(
            _OPENAI_EMBED_URL,
            headers={"Authorization": f"Bearer {api_key}"},
            json={"model": EMBED_MODEL, "input": texts},
        )
        resp.raise_for_status()
        data = sorted(resp.json()["data"], key=lambda d: d["index"])
        return [d["embedding"] for d in data]


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b, strict=False))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else 0.0


def top_k(
    query_vec: list[float],
    chunks: list[tuple[str, list[float]]],
    k: int = 3,
) -> list[str]:
    """Return the contents of the k chunks most similar to query_vec."""
    scored = [(_cosine(query_vec, emb), content) for content, emb in chunks if emb]
    scored.sort(key=lambda s: s[0], reverse=True)
    return [content for _, content in scored[:k]]
