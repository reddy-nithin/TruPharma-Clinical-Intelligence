"""
vector_store.py · Vector Store Abstraction Layer
=================================================
Protocol-based abstraction with PineconeStore and FaissStore implementations.
Factory function selects based on environment configuration.
"""

import os
import time
import warnings
from typing import Any, Dict, List, Optional, Protocol

import numpy as np


class VectorStore(Protocol):
    """Protocol for vector store implementations."""

    def upsert(self, ids: List[str], vectors: np.ndarray, metadata: List[Dict[str, Any]]) -> None:
        ...

    def query(self, vector: np.ndarray, top_k: int = 10, filter: Optional[Dict] = None) -> List[Dict]:
        ...

    def delete_by_filter(self, filter: Dict) -> None:
        ...

    def list_ids(self, filter: Optional[Dict] = None) -> List[str]:
        ...


class PineconeStore:
    """Pinecone serverless vector store with TTL-based caching."""

    def __init__(
        self,
        api_key: str,
        index_name: str = "trupharma",
        dimension: int = 768,
        metric: str = "cosine",
    ):
        from pinecone import Pinecone, ServerlessSpec

        self._pc = Pinecone(api_key=api_key)
        self._index_name = index_name
        self._dimension = dimension

        # Create index if it doesn't exist
        existing = [idx.name for idx in self._pc.list_indexes()]
        if index_name not in existing:
            self._pc.create_index(
                name=index_name,
                dimension=dimension,
                metric=metric,
                spec=ServerlessSpec(cloud="aws", region="us-east-1"),
            )
            # Wait for index to be ready
            for _ in range(30):
                desc = self._pc.describe_index(index_name)
                if desc.status.get("ready"):
                    break
                time.sleep(1)

        self._index = self._pc.Index(index_name)

    def upsert(self, ids: List[str], vectors: np.ndarray, metadata: List[Dict[str, Any]]) -> None:
        batch_size = 100
        for i in range(0, len(ids), batch_size):
            batch_ids = ids[i : i + batch_size]
            batch_vecs = vectors[i : i + batch_size]
            batch_meta = metadata[i : i + batch_size]
            records = [
                {"id": id_, "values": vec.tolist(), "metadata": meta}
                for id_, vec, meta in zip(batch_ids, batch_vecs, batch_meta)
            ]
            self._index.upsert(vectors=records)

    def query(self, vector: np.ndarray, top_k: int = 10, filter: Optional[Dict] = None) -> List[Dict]:
        vec = vector.flatten().tolist()
        kwargs = {"vector": vec, "top_k": top_k, "include_metadata": True}
        if filter:
            kwargs["filter"] = filter
        results = self._index.query(**kwargs)
        return [
            {
                "id": match.id,
                "score": match.score,
                "metadata": match.metadata or {},
            }
            for match in results.matches
        ]

    def delete_by_filter(self, filter: Dict) -> None:
        try:
            # List vectors matching the filter, then delete by ID
            ids = self.list_ids(filter)
            if ids:
                batch_size = 1000
                for i in range(0, len(ids), batch_size):
                    self._index.delete(ids=ids[i : i + batch_size])
        except Exception as exc:
            warnings.warn(f"Pinecone delete_by_filter failed: {exc}")

    def list_ids(self, filter: Optional[Dict] = None) -> List[str]:
        try:
            # Use a zero vector query to list IDs
            zero_vec = [0.0] * self._dimension
            kwargs = {"vector": zero_vec, "top_k": 10000, "include_metadata": False}
            if filter:
                kwargs["filter"] = filter
            results = self._index.query(**kwargs)
            return [match.id for match in results.matches]
        except Exception:
            return []

    def has_fresh_vectors(self, drug_name: str, max_age_hours: float = 24.0) -> bool:
        """Check if drug has vectors newer than max_age_hours."""
        cutoff = time.time() - (max_age_hours * 3600)
        results = self.query(
            vector=np.zeros(self._dimension, dtype=np.float32),
            top_k=1,
            filter={"drug_name": drug_name, "ingested_at": {"$gt": cutoff}},
        )
        return len(results) > 0

    def get_drug_vectors(self, drug_name: str, query_vector: np.ndarray, top_k: int = 15) -> List[Dict]:
        """Retrieve cached vectors for a specific drug."""
        return self.query(
            vector=query_vector,
            top_k=top_k,
            filter={"drug_name": drug_name},
        )


class FaissStore:
    """Local FAISS-based vector store (fallback when Pinecone unavailable)."""

    def __init__(self, dimension: int = 768):
        import faiss
        self._dimension = dimension
        self._index = faiss.IndexFlatIP(dimension)
        self._metadata: List[Dict[str, Any]] = []
        self._ids: List[str] = []

    def upsert(self, ids: List[str], vectors: np.ndarray, metadata: List[Dict[str, Any]]) -> None:
        import faiss
        # Remove existing entries with same IDs
        existing_ids = set(self._ids)
        new_mask = [id_ not in existing_ids for id_ in ids]
        for i, (id_, meta) in enumerate(zip(ids, metadata)):
            if id_ in existing_ids:
                idx = self._ids.index(id_)
                self._metadata[idx] = meta
            else:
                self._ids.append(id_)
                self._metadata.append(meta)

        # Rebuild index with all vectors
        if vectors is not None and len(vectors) > 0:
            self._index.reset()
            self._index.add(vectors.astype(np.float32))

    def query(self, vector: np.ndarray, top_k: int = 10, filter: Optional[Dict] = None) -> List[Dict]:
        if self._index.ntotal == 0:
            return []
        n = min(top_k, self._index.ntotal)
        qv = vector.reshape(1, -1).astype(np.float32)
        scores, idxs = self._index.search(qv, n)
        results = []
        for score, idx in zip(scores[0], idxs[0]):
            if int(idx) < 0 or int(idx) >= len(self._ids):
                continue
            meta = self._metadata[int(idx)] if int(idx) < len(self._metadata) else {}
            if filter:
                match = all(meta.get(k) == v for k, v in filter.items() if not isinstance(v, dict))
                if not match:
                    continue
            results.append({
                "id": self._ids[int(idx)],
                "score": float(score),
                "metadata": meta,
            })
        return results

    def delete_by_filter(self, filter: Dict) -> None:
        pass  # FAISS doesn't support filtered deletion efficiently

    def list_ids(self, filter: Optional[Dict] = None) -> List[str]:
        if not filter:
            return list(self._ids)
        return [
            id_ for id_, meta in zip(self._ids, self._metadata)
            if all(meta.get(k) == v for k, v in filter.items() if not isinstance(v, dict))
        ]

    def has_fresh_vectors(self, drug_name: str, max_age_hours: float = 24.0) -> bool:
        return False  # FAISS store has no persistence — always cache miss

    def get_drug_vectors(self, drug_name: str, query_vector: np.ndarray, top_k: int = 15) -> List[Dict]:
        return self.query(
            vector=query_vector,
            top_k=top_k,
            filter={"drug_name": drug_name},
        )


def create_vector_store(dimension: int = 768) -> Any:
    """Factory: return PineconeStore if configured, else FaissStore."""
    api_key = os.environ.get("PINECONE_API_KEY", "")

    # Also check Streamlit secrets
    if not api_key:
        try:
            import streamlit as st
            api_key = st.secrets.get("PINECONE_API_KEY", "")
        except Exception:
            pass

    if api_key:
        index_name = os.environ.get("PINECONE_INDEX_NAME", "trupharma")
        try:
            import streamlit as st
            index_name = st.secrets.get("PINECONE_INDEX_NAME", index_name)
        except Exception:
            pass

        try:
            return PineconeStore(
                api_key=api_key,
                index_name=index_name,
                dimension=dimension,
            )
        except Exception as exc:
            warnings.warn(f"Pinecone init failed, falling back to FAISS: {exc}")

    return FaissStore(dimension=dimension)
