"""File service for reading and processing files."""

import json
import logging
from pathlib import Path
from typing import Optional, List

from core.plan.kg_construction.config.settings import Settings
from core.plan.kg_construction.models.knowledge_graph import KnowledgeGraph

logger = logging.getLogger(__name__)


class FileServiceError(Exception):
    """Base exception for file service errors."""
    pass


class FileService:
    """Service for file I/O operations following Google ADK patterns."""
    
    def __init__(self, settings: Optional[Settings] = None):
        """Initialize the file service.
        
        Args:
            settings: Application settings (optional).
        """
        self._settings = settings or Settings.get_default()
        
        logger.info("FileService initialized")
    
    def _resolve_output_path(
        self,
        filename: str,
        output_dir: Optional[str] = None
    ) -> Path:
        """Resolve the full output path.
        
        Args:
            filename: The filename to save to.
            output_dir: Output directory (defaults to data directory).
            
        Returns:
            Resolved Path instance.
        """
        if output_dir:
            output_path = Path(output_dir)
        else:
            output_path = Path(self._settings.data_dir)
        
        output_path.mkdir(parents=True, exist_ok=True)
        return output_path / filename
    
    def _resolve_input_path(
        self,
        filename: str,
        input_dir: Optional[str] = None
    ) -> Path:
        """Resolve the full input path.
        
        Args:
            filename: The filename to load from.
            input_dir: Input directory (defaults to data directory).
            
        Returns:
            Resolved Path instance.
        """
        if input_dir:
            input_path = Path(input_dir)
        else:
            input_path = Path(self._settings.data_dir)
        
        return input_path / filename
    
    async def save_knowledge_graph(
        self,
        graph: KnowledgeGraph,
        filename: str,
        output_dir: Optional[str] = None
    ) -> None:
        """Save a knowledge graph to a JSON file.
        
        Args:
            graph: The graph to save.
            filename: The filename to save to.
            output_dir: Output directory (defaults to data directory).
            
        Raises:
            FileServiceError: If saving fails.
        """
        try:
            output_path = self._resolve_output_path(filename, output_dir)
            
            with open(
                output_path,
                'w',
                encoding=self._settings.default_output_encoding
            ) as f:
                json.dump(
                    graph.model_dump(),
                    f,
                    indent=2,
                    ensure_ascii=False
                )
            
            logger.info(f"Knowledge graph saved to {output_path}")
            
        except Exception as e:
            logger.error(f"Failed to save knowledge graph to {filename}: {e}")
            raise FileServiceError(f"Failed to save file: {e}")
    
    async def load_knowledge_graph(
        self,
        filename: str,
        input_dir: Optional[str] = None
    ) -> KnowledgeGraph:
        """Load a knowledge graph from a JSON file.
        
        Args:
            filename: The filename to load from.
            input_dir: Input directory (defaults to data directory).
            
        Returns:
            The loaded KnowledgeGraph instance.
            
        Raises:
            FileServiceError: If loading fails.
        """
        try:
            input_path = self._resolve_input_path(filename, input_dir)
            
            if not input_path.exists():
                raise FileServiceError(f"File not found: {input_path}")
            
            with open(
                input_path,
                'r',
                encoding=self._settings.default_output_encoding
            ) as f:
                graph_data = json.load(f)
            
            graph = KnowledgeGraph.model_validate(graph_data)
            logger.info(f"Knowledge graph loaded from {input_path}")
            return graph
            
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in file {filename}: {e}")
            raise FileServiceError(f"Invalid JSON format: {e}")
        except Exception as e:
            logger.error(f"Failed to load knowledge graph from {filename}: {e}")
            raise FileServiceError(f"Failed to load knowledge graph: {e}")
    
    async def list_graph_files(self, directory: Optional[str] = None) -> List[str]:
        """List all knowledge graph files in a directory.
        
        Args:
            directory: Directory to search in (defaults to data directory).
            
        Returns:
            List of graph filenames.
        """
        try:
            search_dir = Path(directory or self._settings.data_dir)
            if not search_dir.exists():
                return []
            
            # 确保返回字符串列表而不是 Path 对象列表
            files = [
                str(f.name) for f in search_dir.glob("*_graph.json")
                if f.is_file()
            ]
            logger.debug(f"Found {len(files)} graph files in {search_dir}")
            return files
            
        except Exception as e:
            logger.error(f"Failed to list graph files: {e}")
            return [] 