"""Base API client for knowledge graph generation."""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

from core.plan.kg_construction.models.knowledge_graph import KnowledgeGraph


class ApiClientError(Exception):
    """Base exception for API client errors."""
    pass


class ApiAuthenticationError(ApiClientError):
    """Raised when API authentication fails."""
    pass


class ApiResponseError(ApiClientError):
    """Raised when API returns an invalid response."""
    pass


class BaseApiClient(ABC):
    """Abstract base class for API clients."""
    
    @abstractmethod
    async def generate_knowledge_graph(
        self,
        topic: str,
        one_shot_example: Optional[str] = None
    ) -> KnowledgeGraph:
        """Generate a knowledge graph for the given topic.
        
        Args:
            topic: The topic to generate a graph for.
            one_shot_example: Path to a JSON file to use as format example.
            
        Returns:
            A validated KnowledgeGraph instance.
            
        Raises:
            ApiClientError: If the API call fails.
        """
        pass 