"""Main Firecrawl Learning Scraper Application with dependency injection and workflow orchestration."""

import asyncio
import logging
import uuid
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from pathlib import Path
from datetime import datetime, timezone

from .config.firecrawl_config import FirecrawlConfig
from .clients.firecrawl_mcp_client import FirecrawlMCPClient
from .services.natural_language_service import NaturalLanguageService
from .services.search_service import SearchService, SearchOptions
from .services.crawling_service import CrawlingService, CrawlingOptions
from .services.content_extractor import ContentExtractor
from .services.media_downloader import MediaDownloader, DownloadOptions
from .services.file_storage_service import FileStorageService, StorageConfig
from .services.content_processor import ContentProcessorService, ProcessingOptions
from .services.summary_report_service import SummaryReportService
from .models.learning_resource import ParsedCommand, CommandIntent, LearningResource, CrawledContent


@dataclass
class ApplicationConfig:
    """Configuration for the Firecrawl Scraper Application."""
    
    # Storage configuration
    storage_base_path: Path = field(default_factory=lambda: Path.cwd() / "scraped_content")
    
    # Processing options
    auto_download_videos: bool = True
    auto_generate_reports: bool = True
    enable_duplicate_detection: bool = True
    
    # Workflow options
    max_concurrent_operations: int = 3
    enable_progress_callbacks: bool = True
    save_intermediate_results: bool = True
    
    # Output options
    export_formats: List[str] = field(default_factory=lambda: ["markdown", "json"])
    generate_summary_after_session: bool = True
    
    def __post_init__(self):
        """Ensure paths are Path objects."""
        if isinstance(self.storage_base_path, str):
            self.storage_base_path = Path(self.storage_base_path)


@dataclass
class OperationResult:
    """Result of a scraping operation."""
    
    success: bool
    operation_type: str  # search, crawl, process
    session_id: str
    results: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    duration_seconds: float = 0.0
    items_processed: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'success': self.success,
            'operation_type': self.operation_type,
            'session_id': self.session_id,
            'results': self.results,
            'errors': self.errors,
            'warnings': self.warnings,
            'duration_seconds': self.duration_seconds,
            'items_processed': self.items_processed
        }


class FirecrawlScraperApplication:
    """Main application class that orchestrates all scraping workflows."""
    
    def __init__(
        self,
        firecrawl_config: FirecrawlConfig,
        app_config: Optional[ApplicationConfig] = None
    ):
        """Initialize the Firecrawl Scraper Application.
        
        Args:
            firecrawl_config: Configuration for Firecrawl MCP client
            app_config: Application-specific configuration
        """
        self.firecrawl_config = firecrawl_config
        self.app_config = app_config or ApplicationConfig()
        self.logger = logging.getLogger(__name__)
        
        # Initialize services
        self._initialize_services()
        
        # Session management
        self._current_session_id: Optional[str] = None
        self._session_data: Dict[str, Any] = {}
        self._operation_history: List[OperationResult] = []
        
        # Progress callbacks
        self._progress_callbacks: List[Callable[[str, Dict[str, Any]], None]] = []
        
        self.logger.info("FirecrawlScraperApplication initialized")
    
    def _initialize_services(self):
        """Initialize all services with dependency injection."""
        # Core MCP client
        self.mcp_client = FirecrawlMCPClient(self.firecrawl_config)
        
        # NLP service
        self.nlp_service = NaturalLanguageService()
        
        # Search service
        self.search_service = SearchService(self.mcp_client)
        
        # Crawling service
        self.crawling_service = CrawlingService(self.mcp_client)
        
        # Content extraction service
        self.content_extractor = ContentExtractor()
        
        # Media downloader
        download_options = DownloadOptions(
            max_concurrent_downloads=self.app_config.max_concurrent_operations
        )
        self.media_downloader = MediaDownloader(download_options)
        
        # File storage service
        storage_config = StorageConfig(
            base_storage_path=self.app_config.storage_base_path,
            organize_by_topic=True,
            organize_by_source=True,
            create_index_files=True
        )
        self.storage_service = FileStorageService(storage_config)
        
        # Content processor
        processing_options = ProcessingOptions(
            convert_to_markdown=True,
            generate_table_of_contents=True,
            add_metadata_headers=True
        )
        self.content_processor = ContentProcessorService(processing_options)
        
        # Summary and reporting service
        self.report_service = SummaryReportService()
        
        self.logger.info("All services initialized successfully")
    
    def add_progress_callback(self, callback: Callable[[str, Dict[str, Any]], None]):
        """Add progress callback for operation updates.
        
        Args:
            callback: Function to call with progress updates (operation_type, progress_data)
        """
        self._progress_callbacks.append(callback)
    
    def _notify_progress(self, operation_type: str, progress_data: Dict[str, Any]):
        """Notify all progress callbacks of operation progress."""
        if self.app_config.enable_progress_callbacks:
            for callback in self._progress_callbacks:
                try:
                    callback(operation_type, progress_data)
                except Exception as e:
                    self.logger.warning(f"Progress callback failed: {e}")
    
    async def start_session(self) -> str:
        """Start a new scraping session.
        
        Returns:
            Session ID
        """
        self._current_session_id = str(uuid.uuid4())
        self._session_data = {
            'session_id': self._current_session_id,
            'start_time': datetime.now(timezone.utc),
            'operations': [],
            'total_items_found': 0,
            'total_items_stored': 0,
            'errors': [],
            'warnings': []
        }
        
        # Connect to MCP server
        await self.mcp_client.connect()
        
        self.logger.info(f"Started scraping session: {self._current_session_id}")
        self._notify_progress('session', {'status': 'started', 'session_id': self._current_session_id})
        
        return self._current_session_id
    
    async def end_session(self) -> Dict[str, Any]:
        """End the current scraping session and generate summary.
        
        Returns:
            Session summary
        """
        if not self._current_session_id:
            raise RuntimeError("No active session to end")
        
        # Close MCP connection
        await self.mcp_client.disconnect()
        
        # Finalize session data
        self._session_data['end_time'] = datetime.now(timezone.utc)
        duration = self._session_data['end_time'] - self._session_data['start_time']
        self._session_data['duration_seconds'] = duration.total_seconds()
        
        # Generate session summary
        if self.app_config.generate_summary_after_session:
            stored_items = self.storage_service.search_stored_content()
            session_summary = self.report_service.generate_session_summary(
                self._session_data, stored_items
            )
            self._session_data['summary'] = session_summary
        
        session_data = self._session_data.copy()
        
        # Clean up session state
        self._current_session_id = None
        self._session_data = {}
        
        self.logger.info(f"Ended scraping session: {session_data['session_id']}")
        self._notify_progress('session', {'status': 'ended', 'summary': session_data})
        
        return session_data
    
    async def process_natural_language_command(self, user_input: str) -> OperationResult:
        """Process a natural language command and execute appropriate workflow.
        
        Args:
            user_input: Natural language command from user
            
        Returns:
            Operation result
        """
        if not self._current_session_id:
            await self.start_session()
        
        start_time = datetime.now()
        operation_result = OperationResult(
            success=False,
            operation_type="command_processing",
            session_id=self._current_session_id
        )
        
        try:
            self._notify_progress('command', {'status': 'parsing', 'input': user_input})
            
            # Parse the natural language command
            parsed_command = await self.nlp_service.parse_command(user_input)
            
            # Check if command needs clarification
            if parsed_command.needs_clarification():
                operation_result.errors.append("Command needs clarification")
                operation_result.results['clarification_questions'] = parsed_command.get_clarification_questions()
                operation_result.results['parsed_command'] = parsed_command.to_dict()
                return operation_result
            
            # Execute appropriate workflow based on intent
            if parsed_command.intent == CommandIntent.TOPIC_SEARCH:
                result = await self.execute_topic_search_workflow(parsed_command.topic)
                
            elif parsed_command.intent == CommandIntent.URL_CRAWL:
                result = await self.execute_url_crawl_workflow(parsed_command.url)
                
            else:
                operation_result.errors.append(f"Unsupported command intent: {parsed_command.intent}")
                return operation_result
            
            # Merge results
            operation_result.success = result.success
            operation_result.results.update(result.results)
            operation_result.errors.extend(result.errors)
            operation_result.warnings.extend(result.warnings)
            operation_result.items_processed = result.items_processed
            
        except Exception as e:
            self.logger.error(f"Command processing failed: {e}")
            operation_result.errors.append(str(e))
        
        finally:
            # Calculate duration
            operation_result.duration_seconds = (datetime.now() - start_time).total_seconds()
            
            # Add to session and operation history
            self._session_data['operations'].append(operation_result.to_dict())
            self._operation_history.append(operation_result)
            
            self._notify_progress('command', {
                'status': 'completed',
                'success': operation_result.success,
                'duration': operation_result.duration_seconds
            })
        
        return operation_result
    
    async def execute_topic_search_workflow(self, topic: str) -> OperationResult:
        """Execute complete workflow for topic-based search.
        
        Args:
            topic: Topic to search for
            
        Returns:
            Operation result
        """
        start_time = datetime.now()
        operation_result = OperationResult(
            success=False,
            operation_type="topic_search",
            session_id=self._current_session_id
        )
        
        try:
            self._notify_progress('search', {'status': 'starting', 'topic': topic})
            
            # Step 1: Search for learning resources
            search_options = SearchOptions(max_results=10)
            learning_resources, search_metadata = await self.search_service.search_learning_resources(
                topic, search_options
            )
            
            if not learning_resources:
                operation_result.warnings.append(f"No learning resources found for topic: {topic}")
                operation_result.results['search_metadata'] = search_metadata
                return operation_result
            
            self._notify_progress('search', {
                'status': 'found_resources',
                'count': len(learning_resources),
                'topic': topic
            })
            
            # Step 2: Process found resources
            processed_results = []
            
            for i, resource in enumerate(learning_resources):
                try:
                    self._notify_progress('crawl', {
                        'status': 'processing',
                        'current': i + 1,
                        'total': len(learning_resources),
                        'url': resource.url
                    })
                    
                    # Crawl the resource
                    crawled_content, crawl_metadata = await self.crawling_service.crawl_url(resource.url)
                    
                    # Process and store content
                    result = await self._process_and_store_content(
                        crawled_content, topic, resource.url
                    )
                    
                    processed_results.append({
                        'resource': resource.to_dict(),
                        'crawl_metadata': crawl_metadata,
                        'processing_result': result
                    })
                    
                except Exception as e:
                    error_msg = f"Failed to process resource {resource.url}: {e}"
                    operation_result.errors.append(error_msg)
                    self.logger.error(error_msg)
            
            # Update results
            operation_result.success = len(processed_results) > 0
            operation_result.results = {
                'topic': topic,
                'search_metadata': search_metadata,
                'resources_found': len(learning_resources),
                'resources_processed': len(processed_results),
                'processed_results': processed_results
            }
            operation_result.items_processed = len(processed_results)
            
            # Update session totals
            self._session_data['total_items_found'] += len(learning_resources)
            self._session_data['total_items_stored'] += len(processed_results)
            
        except Exception as e:
            error_msg = f"Topic search workflow failed: {e}"
            operation_result.errors.append(error_msg)
            self.logger.error(error_msg)
        
        finally:
            operation_result.duration_seconds = (datetime.now() - start_time).total_seconds()
            
            self._notify_progress('search', {
                'status': 'completed',
                'success': operation_result.success,
                'items_processed': operation_result.items_processed
            })
        
        return operation_result
    
    async def execute_url_crawl_workflow(self, url: str) -> OperationResult:
        """Execute complete workflow for URL crawling.
        
        Args:
            url: URL to crawl
            
        Returns:
            Operation result
        """
        start_time = datetime.now()
        operation_result = OperationResult(
            success=False,
            operation_type="url_crawl",
            session_id=self._current_session_id
        )
        
        try:
            self._notify_progress('crawl', {'status': 'starting', 'url': url})
            
            # Step 1: Crawl the URL
            crawled_content, crawl_metadata = await self.crawling_service.crawl_url(url)
            
            # Step 2: Determine topic (use domain or extract from content)
            topic = self._extract_topic_from_content(crawled_content, url)
            
            # Step 3: Process and store content
            processing_result = await self._process_and_store_content(
                crawled_content, topic, url
            )
            
            operation_result.success = True
            operation_result.results = {
                'url': url,
                'topic': topic,
                'crawl_metadata': crawl_metadata,
                'processing_result': processing_result
            }
            operation_result.items_processed = 1
            
            # Update session totals
            self._session_data['total_items_found'] += 1
            self._session_data['total_items_stored'] += 1
            
        except Exception as e:
            error_msg = f"URL crawl workflow failed: {e}"
            operation_result.errors.append(error_msg)
            self.logger.error(error_msg)
        
        finally:
            operation_result.duration_seconds = (datetime.now() - start_time).total_seconds()
            
            self._notify_progress('crawl', {
                'status': 'completed',
                'success': operation_result.success,
                'url': url
            })
        
        return operation_result
    
    async def _process_and_store_content(
        self,
        crawled_content: CrawledContent,
        topic: str,
        source_url: str
    ) -> Dict[str, Any]:
        """Process crawled content and store it organized by topic.
        
        Args:
            crawled_content: The crawled content to process
            topic: Topic category for organization
            source_url: Original source URL
            
        Returns:
            Processing result dictionary
        """
        result = {
            'content_extracted': {},
            'files_downloaded': {},
            'content_processed': {},
            'content_stored': {},
            'errors': [],
            'warnings': []
        }
        
        try:
            # Step 1: Extract structured content
            self._notify_progress('extract', {'status': 'extracting', 'url': source_url})
            
            extraction_results = self.content_extractor.extract_all_content(
                {'html': '', 'markdown': '', 'title': crawled_content.title},
                source_url
            )
            
            result['content_extracted'] = {
                content_type: len(results) for content_type, results in extraction_results.items()
            }
            
            # Step 2: Download media files if enabled
            downloaded_files = {}
            if self.app_config.auto_download_videos and crawled_content.videos:
                self._notify_progress('download', {
                    'status': 'downloading',
                    'count': len(crawled_content.videos)
                })
                
                download_dir = self.app_config.storage_base_path / "downloads" / "videos"
                
                async with self.media_downloader:
                    for video in crawled_content.videos:
                        try:
                            success, file_path, metadata = await self.media_downloader.download_video(
                                video, download_dir
                            )
                            if success:
                                downloaded_files[video.url] = file_path
                        except Exception as e:
                            result['warnings'].append(f"Failed to download video {video.url}: {e}")
            
            result['files_downloaded'] = downloaded_files
            
            # Step 3: Process content with formatting
            self._notify_progress('process', {'status': 'processing', 'url': source_url})
            
            processed_content = self.content_processor.process_crawled_content(crawled_content)
            
            result['content_processed'] = {
                content_type: len(items) for content_type, items in processed_content.items()
            }
            
            # Step 4: Store organized content
            self._notify_progress('store', {'status': 'storing', 'topic': topic})
            
            stored_items = self.storage_service.store_crawled_content(
                crawled_content, topic, downloaded_files
            )
            
            result['content_stored'] = {
                'items_stored': len(stored_items),
                'storage_path': str(self.app_config.storage_base_path),
                'topic': topic
            }
            
            # Step 5: Export processed content in requested formats
            if self.app_config.export_formats and processed_content:
                export_results = {}
                
                for content_type, items in processed_content.items():
                    for i, item in enumerate(items):
                        for format_type in self.app_config.export_formats:
                            try:
                                export_filename = f"{topic}_{content_type}_{i}.{format_type}"
                                export_path = self.app_config.storage_base_path / "exports" / export_filename
                                
                                success = self.content_processor.export_processed_content(
                                    item, export_path, format_type
                                )
                                
                                if success:
                                    export_results[f"{content_type}_{i}_{format_type}"] = str(export_path)
                                    
                            except Exception as e:
                                result['warnings'].append(f"Export failed for {format_type}: {e}")
                
                result['exports'] = export_results
            
        except Exception as e:
            error_msg = f"Content processing failed: {e}"
            result['errors'].append(error_msg)
            self.logger.error(error_msg)
        
        return result
    
    def _extract_topic_from_content(self, crawled_content: CrawledContent, url: str) -> str:
        """Extract topic from crawled content or URL.
        
        Args:
            crawled_content: Crawled content to analyze
            url: Source URL
            
        Returns:
            Extracted or inferred topic
        """
        # Try to extract from title
        title = crawled_content.title.lower()
        
        # Common programming/tech topics
        tech_topics = {
            'python': ['python', 'django', 'flask', 'pandas'],
            'javascript': ['javascript', 'js', 'node', 'react', 'vue', 'angular'],
            'web_development': ['html', 'css', 'web', 'frontend', 'backend'],
            'data_science': ['data', 'science', 'analytics', 'machine learning', 'ai'],
            'devops': ['docker', 'kubernetes', 'devops', 'ci/cd', 'deployment'],
            'mobile': ['mobile', 'android', 'ios', 'flutter', 'react native']
        }
        
        for topic, keywords in tech_topics.items():
            if any(keyword in title for keyword in keywords):
                return topic
        
        # Fallback to domain-based topic
        from urllib.parse import urlparse
        domain = urlparse(url).netloc.lower()
        
        if 'stackoverflow' in domain:
            return 'programming_qa'
        elif 'github' in domain:
            return 'code_repository'
        elif 'youtube' in domain:
            return 'video_tutorial'
        elif 'medium' in domain:
            return 'tech_article'
        
        return 'general'
    
    async def generate_comprehensive_report(self, output_dir: Optional[Path] = None) -> Dict[str, str]:
        """Generate comprehensive report of all processed content.
        
        Args:
            output_dir: Directory to save reports (default: storage_base_path/reports)
            
        Returns:
            Dictionary mapping report types to file paths
        """
        if output_dir is None:
            output_dir = self.app_config.storage_base_path / "reports"
        
        # Get all stored items
        stored_items = self.storage_service.search_stored_content()
        
        # Get processing statistics from services
        processing_stats = {
            'search_service': {},  # Would need to be implemented in search service
            'crawling_service': self.crawling_service.get_crawling_statistics(),
            'content_processor': self.content_processor.get_processing_statistics(),
            'media_downloader': {},  # Would need to be implemented
            'storage_service': self.storage_service.get_storage_statistics()
        }
        
        # Generate and export reports
        exported_files = self.report_service.export_comprehensive_report(
            stored_items=stored_items,
            output_dir=output_dir,
            include_duplicates=self.app_config.enable_duplicate_detection,
            processing_stats=processing_stats
        )
        
        self.logger.info(f"Generated comprehensive reports: {list(exported_files.keys())}")
        
        return exported_files
    
    def get_session_status(self) -> Dict[str, Any]:
        """Get current session status and statistics.
        
        Returns:
            Session status dictionary
        """
        if not self._current_session_id:
            return {'status': 'no_active_session'}
        
        return {
            'status': 'active',
            'session_id': self._current_session_id,
            'start_time': self._session_data['start_time'].isoformat(),
            'operations_count': len(self._session_data['operations']),
            'total_items_found': self._session_data['total_items_found'],
            'total_items_stored': self._session_data['total_items_stored'],
            'errors_count': len(self._session_data['errors']),
            'warnings_count': len(self._session_data['warnings'])
        }
    
    def get_operation_history(self) -> List[Dict[str, Any]]:
        """Get history of all operations performed.
        
        Returns:
            List of operation results
        """
        return [op.to_dict() for op in self._operation_history]
    
    def search_stored_content(
        self,
        query: str = "",
        content_type: Optional[str] = None,
        topic: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Search stored content with various filters.
        
        Args:
            query: Text query to search
            content_type: Filter by content type
            topic: Filter by topic
            
        Returns:
            List of matching stored items
        """
        stored_items = self.storage_service.search_stored_content(
            query=query,
            content_type=content_type,
            topic=topic
        )
        
        return [item.to_dict() for item in stored_items]
    
    async def cleanup_duplicates(self, dry_run: bool = True) -> Dict[str, Any]:
        """Identify and optionally remove duplicate content.
        
        Args:
            dry_run: If True, only identify duplicates without removing
            
        Returns:
            Cleanup report
        """
        stored_items = self.storage_service.search_stored_content()
        
        # Generate duplicate report
        duplicate_report = self.report_service.detect_and_report_duplicates(stored_items)
        
        if not dry_run and duplicate_report['duplicate_groups']:
            # TODO: Implement actual duplicate removal
            # This would involve carefully selecting which items to keep
            # and removing the others from storage
            duplicate_report['cleanup_performed'] = False
            duplicate_report['cleanup_note'] = "Automatic duplicate removal not yet implemented"
        
        return duplicate_report
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self._current_session_id:
            await self.end_session()