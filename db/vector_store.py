import os
import uuid
import logging
from typing import List, Dict, Any, Optional

# Constants for Qdrant
QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))
QDRANT_COLLECTION = os.getenv("QDRANT_COLLECTION", "candidates")
VECTOR_SIZE = 384  # Dimension for BGE-small-en-v1.5


class CandidateVectorStore:
    """Enterprise vector database wrapper using Qdrant with singleton embedding model."""

    _model = None  # Class-level singleton for the embedding model

    def __init__(self):
        self.logger = logging.getLogger("vector_store")
        
        # Then proceed with Qdrant
        # Use HTTP interface explicitly to avoid gRPC deadlocks on macOS
        try:
            from qdrant_client import QdrantClient
            self.client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT, prefer_grpc=False)
            self._ensure_collection()
            self.logger.info(f"Initialized Qdrant Vector Store at {QDRANT_HOST}:{QDRANT_PORT}")
        except Exception as e:
            self.logger.error(f"Failed to initialize Qdrant client: {e}")
            # Ensure self.client exists to avoid AttributeErrors later
            self.client = None

    @classmethod
    def _get_model(cls):
        """Lazily load the FastEmbed model (ONNX)."""
        if cls._model is None:
            from fastembed import TextEmbedding
            # This is the ONNX version of BGE-Small-v1.5
            # It defaults to CPU and is thread-safe on macOS
            cls._model = TextEmbedding(model_name="BAAI/bge-small-en-v1.5")
            logging.getLogger("vector_store").info("✅ FastEmbed (ONNX) loaded successfully.")
        return cls._model

    def _ensure_collection(self):
        """Create the collection if it does not exist."""
        if not self.client:
            return
        from qdrant_client.models import Distance, VectorParams
        try:
            collections = [c.name for c in self.client.get_collections().collections]
            if QDRANT_COLLECTION not in collections:
                self.client.create_collection(
                    collection_name=QDRANT_COLLECTION,
                    vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE),
                )
                self.logger.info(f"Created Qdrant collection '{QDRANT_COLLECTION}'")
        except Exception as e:
            self.logger.error(f"Error checking/creating Qdrant collection: {e}")

    def _hash_fallback(self, text: str) -> List[float]:
        """Robust hash-based pseudo-random vector fallback."""
        import hashlib
        import numpy as np
        h = hashlib.sha256(text.encode()).digest()
        seed = int.from_bytes(h[:4], "big")
        np.random.seed(seed)
        return np.random.uniform(-1, 1, VECTOR_SIZE).tolist()

    def _text_to_vector(self, text: str) -> List[float]:
        """Convert text to a vector embedding using FastEmbed or hash fallback."""
        model = self._get_model()
        try:
            # FastEmbed handles the instruction prefix and normalization internally
            # It returns an iterator of numpy arrays
            embeddings = list(model.embed([text]))
            return embeddings[0].tolist()
        except Exception as e:
            self.logger.warning(f"Embedding failed: {e}")
            # Keep your hash fallback here just in case
            return self._hash_fallback(text)

    def add_candidate(self, candidate_id: str, profile_text: str, metadata: Dict[str, Any]):
        """Upsert a candidate profile into the Qdrant vector store."""
        if not self.client:
            self.logger.error("Qdrant client not initialized, skipping upsert.")
            return

        try:
            vector = self._text_to_vector(profile_text)
            point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, str(candidate_id)))
            
            from qdrant_client.models import PointStruct
            self.client.upsert(
                collection_name=QDRANT_COLLECTION,
                points=[
                    PointStruct(
                        id=point_id,
                        vector=vector,
                        payload={**metadata, "candidate_id": str(candidate_id), "profile_text": profile_text},
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
        if not self.client:
            return {"ids": [], "scores": [], "payloads": []}

        try:
            vector = self._text_to_vector(query_text)
            query_filter = None
            if tenant_id:
                from qdrant_client.models import Filter, FieldCondition, MatchValue
                query_filter = Filter(
                    must=[FieldCondition(key="tenant_id", match=MatchValue(value=tenant_id))]
                )
            
            # Use query_points for high-performance retrieval
            results = self.client.query_points(
                collection_name=QDRANT_COLLECTION,
                query=vector,
                limit=n_results,
                query_filter=query_filter,
            ).points
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
        if not self.client:
            return
        try:
            point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, str(candidate_id)))
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
