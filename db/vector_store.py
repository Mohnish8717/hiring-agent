import chromadb
import uuid
import logging
from typing import List, Dict, Any, Optional

class CandidateVectorStore:
    """Vector database wrapper for storing and querying candidate profiles semantically."""
    
    def __init__(self, db_path: str = "db/ats_vector_store"):
        self.logger = logging.getLogger("vector_store")
        # Initialize persistent client
        self.client = chromadb.PersistentClient(path=db_path)
        # Get or create collection
        self.collection = self.client.get_or_create_collection(
            name="candidates",
            metadata={"hnsw:space": "cosine"}
        )
        self.logger.info(f"Initialized Vector Store at {db_path}")

    def add_candidate(self, candidate_id: str, profile_text: str, metadata: Dict[str, Any]):
        """Upsert a candidate profile into the vector store."""
        try:
            self.collection.upsert(
                documents=[profile_text],
                metadatas=[metadata],
                ids=[candidate_id]
            )
            self.logger.info(f"Successfully added/updated candidate {candidate_id} in vector store.")
        except Exception as e:
            self.logger.error(f"Error adding candidate to vector store: {str(e)}")

    def query_similar(self, query_text: str, n_results: int = 5) -> Dict[str, Any]:
        """Find most semantically similar candidates to a query string."""
        try:
            results = self.collection.query(
                query_texts=[query_text],
                n_results=n_results
            )
            return results
        except Exception as e:
            self.logger.error(f"Error querying vector store: {str(e)}")
            return {"ids": [], "documents": [], "metadatas": [], "distances": []}

    def delete_candidate(self, candidate_id: str):
        """Remove a candidate from the store."""
        try:
            self.collection.delete(ids=[candidate_id])
        except Exception as e:
            self.logger.error(f"Error deleting candidate: {str(e)}")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    store = CandidateVectorStore()
    store.add_candidate("test_1", "Senior React Developer with Python experience", {"name": "Test Candidate"})
    results = store.query_similar("Frontend developer with Node.js")
    print(f"Query Results: {results['ids']}")
