"""Firecrawl configuration management for learning scraper."""

import os
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from dotenv import load_dotenv


@dataclass(frozen=True)
class FirecrawlConfig:
    """Configuration for Firecrawl MCP integration.
    
    This class follows Google ADK patterns for configuration management
    with proper separation of concerns and immutability.
    """
    
    mcp_server_url: str = "http://localhost:3000"
    api_key: Optional[str] = None
    rate_limit_per_minute: int = 60
    timeout_seconds: int = 30
    max_retries: int = 3
    retry_delay: float = 1.0
    backoff_factor: float = 2.0
    
    @classmethod
    def from_environment(cls) -> 'FirecrawlConfig':
        """Create configuration from environment variables.
        
        Returns:
            FirecrawlConfig instance with values from environment.
        """
        load_dotenv()
        
        return cls(
            mcp_server_url=os.getenv("FIRECRAWL_MCP_URL", "http://localhost:3000"),
            api_key=os.getenv("FIRECRAWL_API_KEY"),
            rate_limit_per_minute=int(os.getenv("FIRECRAWL_RATE_LIMIT", "60")),
            timeout_seconds=int(os.getenv("FIRECRAWL_TIMEOUT", "30")),
            max_retries=int(os.getenv("FIRECRAWL_MAX_RETRIES", "3")),
            retry_delay=float(os.getenv("FIRECRAWL_RETRY_DELAY", "1.0")),
            backoff_factor=float(os.getenv("FIRECRAWL_BACKOFF_FACTOR", "2.0"))
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return {
            'mcp_server_url': self.mcp_server_url,
            'api_key': self.api_key,
            'rate_limit_per_minute': self.rate_limit_per_minute,
            'timeout_seconds': self.timeout_seconds,
            'max_retries': self.max_retries,
            'retry_delay': self.retry_delay,
            'backoff_factor': self.backoff_factor
        }


@dataclass(frozen=True)
class ScrapingConfig:
    """Configuration for content scraping operations."""
    
    max_search_results: int = 3
    content_types: List[str] = field(default_factory=lambda: ["video", "tutorial", "discussion"])
    download_directory: str = "downloads"
    max_file_size_mb: int = 500
    organize_by_topic: bool = True
    create_index_files: bool = True
    supported_video_formats: List[str] = field(default_factory=lambda: ["mp4", "webm", "avi", "mov"])
    max_concurrent_downloads: int = 3
    
    @classmethod
    def from_environment(cls) -> 'ScrapingConfig':
        """Create configuration from environment variables.
        
        Returns:
            ScrapingConfig instance with values from environment.
        """
        load_dotenv()
        
        content_types = os.getenv("SCRAPING_CONTENT_TYPES", "video,tutorial,discussion").split(",")
        video_formats = os.getenv("SCRAPING_VIDEO_FORMATS", "mp4,webm,avi,mov").split(",")
        
        return cls(
            max_search_results=int(os.getenv("SCRAPING_MAX_RESULTS", "3")),
            content_types=[ct.strip() for ct in content_types],
            download_directory=os.getenv("SCRAPING_DOWNLOAD_DIR", "downloads"),
            max_file_size_mb=int(os.getenv("SCRAPING_MAX_FILE_SIZE_MB", "500")),
            organize_by_topic=os.getenv("SCRAPING_ORGANIZE_BY_TOPIC", "True").upper() == "TRUE",
            create_index_files=os.getenv("SCRAPING_CREATE_INDEX", "True").upper() == "TRUE",
            supported_video_formats=[fmt.strip() for fmt in video_formats],
            max_concurrent_downloads=int(os.getenv("SCRAPING_MAX_CONCURRENT", "3"))
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return {
            'max_search_results': self.max_search_results,
            'content_types': self.content_types,
            'download_directory': self.download_directory,
            'max_file_size_mb': self.max_file_size_mb,
            'organize_by_topic': self.organize_by_topic,
            'create_index_files': self.create_index_files,
            'supported_video_formats': self.supported_video_formats,
            'max_concurrent_downloads': self.max_concurrent_downloads
        }
    
    def validate(self) -> None:
        """Validate configuration values.
        
        Raises:
            ValueError: If configuration values are invalid.
        """
        if self.max_search_results <= 0:
            raise ValueError("max_search_results must be positive")
        
        if self.max_file_size_mb <= 0:
            raise ValueError("max_file_size_mb must be positive")
        
        if self.max_concurrent_downloads <= 0:
            raise ValueError("max_concurrent_downloads must be positive")
        
        if not self.content_types:
            raise ValueError("content_types cannot be empty")
        
        valid_content_types = {"video", "tutorial", "discussion"}
        invalid_types = set(self.content_types) - valid_content_types
        if invalid_types:
            raise ValueError(f"Invalid content types: {invalid_types}")