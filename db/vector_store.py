"""
Qdrant-backed vector store for candidate semantic search.

Replaces the local ChromaDB implementation with a self-hosted Qdrant instance
for enterprise-grade scalability and multi-tenant metadata filtering.

Environment variables:
    QDRANT_HOST – Qdrant server hostname (default: localhost)
    QDRANT_PORT – Qdrant gRPC port (default: 6333)
    QDRANT_COLLECTION – Collection name (default: candidates)
"""

import os
import uuid
import logging
from typing import List, Dict, Any, Optional

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
    PointStruct,
    Filter,
    FieldCondition,
    MatchValue,
)

QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))
QDRANT_COLLECTION = os.getenv("QDRANT_COLLECTION", "candidates")
VECTOR_SIZE = 384  # Default for sentence-transformers/all-MiniLM-L6-v2


class CandidateVectorStore:
    """Enterprise vector database wrapper using Qdrant."""

    def __init__(self):
        self.logger = logging.getLogger("vector_store")
        self.client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
        self._ensure_collection()
        self.logger.info(f"Initialized Qdrant Vector Store at {QDRANT_HOST}:{QDRANT_PORT}")

    def _ensure_collection(self):
        """Create the collection if it does not exist."""
        collections = [c.name for c in self.client.get_collections().collections]
        if QDRANT_COLLECTION not in collections:
            self.client.create_collection(
                collection_name=QDRANT_COLLECTION,
                vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE),
            )
            self.logger.info(f"Created Qdrant collection '{QDRANT_COLLECTION}'")

    def _text_to_vector(self, text: str) -> List[float]:
        """
        Convert text to a vector embedding.
        Uses sentence-transformers for local, free embedding generation.
        Falls back to a simple hash-based vector if the library is not installed.
        """
        try:
            from sentence_transformers import SentenceTransformer
            model = SentenceTransformer("all-MiniLM-L6-v2")
            return model.encode(text).tolist()
        except ImportError:
            self.logger.warning("sentence-transformers not installed, using hash-based fallback")
            import hashlib
            h = hashlib.sha384(text.encode()).digest()
            return [float(b) / 255.0 for b in h]

    def add_candidate(self, candidate_id: str, profile_text: str, metadata: Dict[str, Any]):
        """Upsert a candidate profile into the Qdrant vector store."""
        try:
            vector = self._text_to_vector(profile_text)
            point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, candidate_id))
            self.client.upsert(
                collection_name=QDRANT_COLLECTION,
                points=[
                    PointStruct(
                        id=point_id,
                        vector=vector,
                        payload={**metadata, "candidate_id": candidate_id, "profile_text": profile_text},
                    )
                ],
            )
            self.logger.info(f"Upserted candidate {candidate_id} in Qdrant")
        except Exception as e:
            self.logger.error(f"Error adding candidate to Qdrant: {str(e)}")

    def query_similar(
        self,
        query_text: str,
        n_results: int = 5,
        tenant_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Find semantically similar candidates, optionally filtered by tenant."""
        try:
            vector = self._text_to_vector(query_text)
            query_filter = None
            if tenant_id:
                query_filter = Filter(
                    must=[FieldCondition(key="tenant_id", match=MatchValue(value=tenant_id))]
                )
            results = self.client.search(
                collection_name=QDRANT_COLLECTION,
                query_vector=vector,
                limit=n_results,
                query_filter=query_filter,
            )
            return {
                "ids": [r.id for r in results],
                "scores": [r.score for r in results],
                "payloads": [r.payload for r in results],
            }
        except Exception as e:
            self.logger.error(f"Error querying Qdrant: {str(e)}")
            return {"ids": [], "scores": [], "payloads": []}

    def delete_candidate(self, candidate_id: str):
        """Remove a candidate from the store."""
        try:
            point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, candidate_id))
            self.client.delete(
                collection_name=QDRANT_COLLECTION,
                points_selector=[point_id],
            )
        except Exception as e:
            self.logger.error(f"Error deleting candidate from Qdrant: {str(e)}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    store = CandidateVectorStore()
    store.add_candidate("test_1", "Senior React Developer with Python experience", {"name": "Test Candidate"})
    results = store.query_similar("Frontend developer with Node.js")
    print(f"Query Results: {results['ids']}")
