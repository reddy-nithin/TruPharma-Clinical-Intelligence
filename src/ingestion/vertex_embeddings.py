"""
vertex_embeddings.py · Vertex AI Embedding Wrapper
===================================================
Thin wrapper around Vertex AI text-embedding-004 model.
768-dimensional embeddings with batching and retry logic.
Falls back gracefully when Vertex AI is unavailable.
"""

import time
import warnings
from typing import List, Optional

import numpy as np


def embed_texts(
    texts: List[str],
    model_name: str = "text-embedding-004",
    batch_size: int = 250,
    max_retries: int = 3,
    task_type: str = "RETRIEVAL_DOCUMENT",
) -> Optional[np.ndarray]:
    """Embed a list of texts using Vertex AI text-embedding-004.

    Parameters
    ----------
    texts : list[str]
        Texts to embed.
    model_name : str
        Vertex AI embedding model name.
    batch_size : int
        Max texts per API call (Vertex AI limit is 250).
    max_retries : int
        Number of retries with exponential backoff.
    task_type : str
        Vertex AI task type hint (RETRIEVAL_DOCUMENT or RETRIEVAL_QUERY).

    Returns
    -------
    np.ndarray or None
        Array of shape (len(texts), 768) with L2-normalized embeddings,
        or None if Vertex AI is unavailable.
    """
    if not texts:
        return None

    try:
        from src.config import is_vertex_available
        if not is_vertex_available():
            return None
    except ImportError:
        return None

    try:
        from vertexai.language_models import TextEmbeddingInput, TextEmbeddingModel
    except ImportError:
        warnings.warn("vertexai SDK not installed — cannot generate embeddings")
        return None

    model = TextEmbeddingModel.from_pretrained(model_name)
    all_embeddings = []

    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        inputs = [TextEmbeddingInput(text=t, task_type=task_type) for t in batch]

        for attempt in range(max_retries):
            try:
                embeddings = model.get_embeddings(inputs)
                all_embeddings.extend([e.values for e in embeddings])
                break
            except Exception as exc:
                if attempt < max_retries - 1:
                    wait = 2 ** attempt
                    warnings.warn(f"Vertex AI embedding retry {attempt + 1}/{max_retries}: {exc}")
                    time.sleep(wait)
                else:
                    warnings.warn(f"Vertex AI embedding failed after {max_retries} retries: {exc}")
                    return None

    result = np.array(all_embeddings, dtype=np.float32)
    # L2-normalize for cosine similarity via inner product
    norms = np.linalg.norm(result, axis=1, keepdims=True)
    norms = np.where(norms == 0, 1, norms)
    result = result / norms
    return result


def embed_query(
    text: str,
    model_name: str = "text-embedding-004",
) -> Optional[np.ndarray]:
    """Embed a single query text. Returns shape (1, 768) or None."""
    return embed_texts(
        [text],
        model_name=model_name,
        task_type="RETRIEVAL_QUERY",
    )
