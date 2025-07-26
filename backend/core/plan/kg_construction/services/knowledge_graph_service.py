"""Knowledge graph service for managing graph operations."""

import logging
from typing import Dict, Any, Optional, List

from core.plan.kg_construction.clients.base_client import BaseApiClient, ApiClientError
from core.plan.kg_construction.config.api_config import ApiConfig
from core.plan.kg_construction.config.settings import Settings
from core.plan.kg_construction.models.knowledge_graph import KnowledgeGraph
from core.plan.kg_construction.services.file_service import FileService

logger = logging.getLogger(__name__)


class KnowledgeGraphServiceError(Exception):
    """Base exception for knowledge graph service errors."""
    pass


class KnowledgeGraphService:
    """High-level service for knowledge graph operations.
    
    This service orchestrates the interaction between API clients,
    file operations, and business logic following Google ADK patterns
    for service layer design.
    """
    
    def __init__(
        self,
        api_client: BaseApiClient,
        file_service: Optional[FileService] = None,
        settings: Optional[Settings] = None
    ):
        """Initialize the knowledge graph service.
        
        Args:
            api_client: API client for generating knowledge graphs.
            file_service: Service for file operations (optional).
            settings: Application settings (optional).
        """
        self._api_client = api_client
        self._file_service = file_service or FileService()
        self._settings = settings or Settings.get_default()
        
        logger.info("KnowledgeGraphService initialized")
    
    async def create_knowledge_graph(
        self,
        topic: str,
        save_to_file: bool = True,
        output_filename: Optional[str] = None,
        one_shot_example: Optional[str] = None
    ) -> KnowledgeGraph:
        """Create a knowledge graph for the given topic.
        
        Args:
            topic: The topic to create a knowledge graph for.
            save_to_file: Whether to save the graph to a file.
            output_filename: Custom filename for output (optional).
            one_shot_example: Path to a JSON file to use as format example.
            
        Returns:
            The generated KnowledgeGraph instance.
            
        Raises:
            KnowledgeGraphServiceError: If graph creation fails.
        """
        try:
            logger.info(f"Creating knowledge graph for topic: {topic}")
            
            # Generate the knowledge graph using the API client
            knowledge_graph = await self._api_client.generate_knowledge_graph(
                topic,
                one_shot_example=one_shot_example
            )
            
            # Validate the generated graph
            self._validate_knowledge_graph(knowledge_graph)
            
            # Save to file if requested
            if save_to_file:
                filename = output_filename or self._generate_filename(topic)
                await self._save_graph(knowledge_graph, filename)
            
            logger.info(
                f"Successfully created knowledge graph with "
                f"{knowledge_graph.get_node_count()} nodes and "
                f"{knowledge_graph.get_edge_count()} edges"
            )
            
            return knowledge_graph
            
        except ApiClientError as e:
            logger.error(f"API client error: {e}")
            raise KnowledgeGraphServiceError(f"Failed to generate knowledge graph: {e}")
        except Exception as e:
            logger.error(f"Unexpected error in knowledge graph creation: {e}")
            raise KnowledgeGraphServiceError(f"Knowledge graph creation failed: {e}")
    
    def _validate_knowledge_graph(self, graph: KnowledgeGraph) -> None:
        """Validate the knowledge graph structure and content.
        
        Args:
            graph: The graph to validate.
            
        Raises:
            KnowledgeGraphServiceError: If validation fails.
        """
        validation_errors = graph.validate_graph_integrity()
        
        if validation_errors:
            error_msg = f"Graph validation failed: {'; '.join(validation_errors)}"
            logger.error(error_msg)
            raise KnowledgeGraphServiceError(error_msg)
        
        if graph.get_node_count() == 0:
            raise KnowledgeGraphServiceError("Generated graph has no nodes")
        
        logger.debug(f"Graph validation passed for {graph.topic}")
    
    def _generate_filename(self, topic: str) -> str:
        """Generate a filename based on the topic.
        
        Args:
            topic: The topic to generate a filename for.
            
        Returns:
            Generated filename.
        """
        safe_topic = topic.lower().replace(" ", "_").replace("-", "_")
        # Remove any non-alphanumeric characters except underscores
        safe_topic = ''.join(c for c in safe_topic if c.isalnum() or c == '_')
        return f"{safe_topic}_graph.json"
    
    async def _save_graph(self, graph: KnowledgeGraph, filename: str) -> None:
        """Save the knowledge graph to a file.
        
        Args:
            graph: The graph to save.
            filename: The filename to save to.
            
        Raises:
            KnowledgeGraphServiceError: If saving fails.
        """
        try:
            await self._file_service.save_knowledge_graph(graph, filename)
            logger.info(f"Knowledge graph saved to {filename}")
        except Exception as e:
            logger.error(f"Failed to save knowledge graph: {e}")
            raise KnowledgeGraphServiceError(f"Failed to save graph to file: {e}") 

    async def list_graph_files(self, directory: Optional[str] = None) -> list[str]:
        """列出所有已生成的知识图谱文件。

        Args:
            directory: 可选，指定目录

        Returns:
            包含所有知识图谱文件名的列表。

        Raises:
            KnowledgeGraphServiceError: 如果列出文件失败。
        """
        try:
            files = await self._file_service.list_graph_files(directory)
            logger.debug(f"Found {len(files)} graph files")
            return files
        except Exception as e:
            logger.error(f"Failed to list knowledge graph files: {e}")
            raise KnowledgeGraphServiceError(f"Failed to list graph files: {e}") 