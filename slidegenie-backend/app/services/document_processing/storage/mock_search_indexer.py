"""
Mock search indexer for MVP without Elasticsearch.

This provides a simple in-memory search implementation for testing
and MVP purposes when Elasticsearch is not needed.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from uuid import UUID

logger = logging.getLogger(__name__)


class MockSearchIndexer:
    """Mock search indexer that stores data in memory."""
    
    def __init__(self):
        """Initialize mock search indexer."""
        self.documents = {}
        self.initialized = False
        logger.info("MockSearchIndexer initialized")
    
    async def initialize(self) -> None:
        """Initialize the search indexer."""
        self.initialized = True
        logger.info("MockSearchIndexer initialized successfully")
    
    async def index_document(
        self,
        file_id: str,
        content: str,
        filename: str,
        user_id: UUID,
        metadata: Dict[str, Any]
    ) -> bool:
        """Index a document for search."""
        self.documents[file_id] = {
            "file_id": file_id,
            "content": content,
            "filename": filename,
            "user_id": str(user_id),
            "metadata": metadata,
            "indexed_at": datetime.utcnow().isoformat()
        }
        logger.info(f"Indexed document {file_id}")
        return True
    
    async def search(
        self,
        query: str,
        user_id: UUID,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 20,
        offset: int = 0,
        facets: Optional[List[str]] = None,
        sort_by: str = "relevance",
        order: str = "desc"
    ) -> Dict[str, Any]:
        """Search documents with mock implementation."""
        # Filter documents by user
        user_docs = [
            doc for doc in self.documents.values()
            if doc["user_id"] == str(user_id)
        ]
        
        # Simple text search
        results = []
        if query:
            query_lower = query.lower()
            for doc in user_docs:
                if (query_lower in doc["content"].lower() or 
                    query_lower in doc["filename"].lower()):
                    results.append(doc)
        else:
            results = user_docs
        
        # Apply pagination
        total = len(results)
        results = results[offset:offset + limit]
        
        return {
            "total": total,
            "documents": results,
            "facets": {},
            "took_ms": 1
        }
    
    async def delete_document(self, file_id: str) -> bool:
        """Delete a document from the index."""
        if file_id in self.documents:
            del self.documents[file_id]
            logger.info(f"Deleted document {file_id} from index")
            return True
        return False
    
    async def get_metrics(self) -> Dict[str, Any]:
        """Get search indexer metrics."""
        return {
            "total_documents": len(self.documents),
            "index_size_mb": 0.1,  # Mock size
            "search_count_24h": 0,
            "avg_search_time_ms": 1.0,
            "index_health": "healthy"
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check."""
        return {
            "status": "healthy" if self.initialized else "unhealthy",
            "issues": []
        }
    
    async def optimize_index(self) -> Dict[str, Any]:
        """Optimize the search index (no-op for mock)."""
        return {"optimized": True, "time_ms": 1}
    
    async def update_mappings(self) -> bool:
        """Update index mappings (no-op for mock)."""
        return True
    
    async def refresh_index(self, index_name: Optional[str] = None) -> bool:
        """Refresh index (no-op for mock)."""
        return True