# Design Document

## Overview

This design extends the existing scraping module to provide a comprehensive video scraping and downloading API that integrates seamlessly with the current FastAPI architecture and agno agent framework. The solution builds upon the existing `CrawlingService`, `MediaDownloader`, and `FirecrawlMCPClient` components while adding new orchestration layers for batch video processing.

The design follows the established patterns in the codebase:
- FastAPI routes with consistent error handling and response formats
- Agno agent integration for programmatic access
- Pydantic models for request/response validation
- Async/await patterns for concurrent operations
- Comprehensive logging and monitoring

## Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    FastAPI Application                          │
├─────────────────────────────────────────────────────────────────┤
│  Video Scraping Router (/api/v1/scraping/videos)               │
│  ├── POST /batch-download                                       │
│  ├── GET /status/{job_id}                                       │
│  ├── GET /progress/{job_id}                                     │
│  └── DELETE /cancel/{job_id}                                    │
├─────────────────────────────────────────────────────────────────┤
│                Video Scraping Service Layer                     │
│  ├── VideoScrapingOrchestrator                                 │
│  ├── VideoLinkExtractor                                        │
│  ├── BatchDownloadManager                                      │
│  └── ProgressTracker                                           │
├─────────────────────────────────────────────────────────────────┤
│              Existing Scraping Components                       │
│  ├── CrawlingService (URL crawling & content extraction)       │
│  ├── MediaDownloader (Video downloading with progress)         │
│  ├── FirecrawlMCPClient (Web scraping via MCP)                │
│  └── URLValidator (URL validation & metadata)                  │
├─────────────────────────────────────────────────────────────────┤
│                   Agno Agent Integration                        │
│  ├── VideoScrapingAgent (Agent tool wrapper)                   │
│  ├── Model Integration (AzureOpenAI, Gemini, Kimi)            │
│  └── Agent Workflow Support                                    │
├─────────────────────────────────────────────────────────────────┤
│                  Storage & Persistence                          │
│  ├── Job Status Storage (In-memory + optional Redis)           │
│  ├── Downloaded Files (Local filesystem)                      │
│  └── Progress Tracking (WebSocket + polling)                   │
└─────────────────────────────────────────────────────────────────┘
```

### Component Interaction Flow

1. **API Request** → Video Scraping Router receives batch download request
2. **Orchestration** → VideoScrapingOrchestrator coordinates the entire process
3. **URL Crawling** → CrawlingService extracts content from the webpage
4. **Link Extraction** → VideoLinkExtractor identifies all video URLs
5. **Batch Download** → BatchDownloadManager handles concurrent downloads
6. **Progress Tracking** → ProgressTracker provides real-time updates
7. **Response** → Structured response with download results and metadata

## Components and Interfaces

### 1. FastAPI Router (`video_scraping_router.py`)

```python
from fastapi import APIRouter, HTTPException, BackgroundTasks, WebSocket
from typing import List, Optional
from pydantic import BaseModel, HttpUrl, Field

class BatchVideoDownloadRequest(BaseModel):
    url: HttpUrl = Field(description="Webpage URL containing video links")
    download_options: Optional[VideoDownloadOptions] = None
    output_directory: Optional[str] = None
    filter_options: Optional[VideoFilterOptions] = None

class VideoDownloadOptions(BaseModel):
    max_file_size_mb: int = 500
    quality_preferences: List[str] = ["1080p", "720p", "480p"]
    max_concurrent_downloads: int = 3
    timeout_seconds: int = 300
    supported_formats: List[str] = [".mp4", ".webm", ".avi", ".mov"]

class VideoFilterOptions(BaseModel):
    min_duration_seconds: Optional[int] = None
    max_duration_seconds: Optional[int] = None
    exclude_platforms: List[str] = []
    include_platforms: List[str] = []

class BatchVideoDownloadResponse(BaseModel):
    success: bool
    job_id: str
    message: str
    total_videos_found: int
    estimated_download_time_minutes: Optional[int]
    download_directory: str
```

### 2. Video Scraping Orchestrator (`video_scraping_orchestrator.py`)

The main service class that coordinates the entire video scraping and downloading process:

```python
class VideoScrapingOrchestrator:
    def __init__(self, 
                 crawling_service: CrawlingService,
                 media_downloader: MediaDownloader,
                 progress_tracker: ProgressTracker):
        self.crawling_service = crawling_service
        self.media_downloader = media_downloader
        self.progress_tracker = progress_tracker
        self.job_manager = JobManager()
    
    async def start_batch_download(self, request: BatchVideoDownloadRequest) -> BatchVideoDownloadJob:
        """Main orchestration method for batch video downloading"""
        
    async def extract_video_links(self, url: str) -> List[VideoLink]:
        """Extract all video links from a webpage"""
        
    async def filter_video_links(self, links: List[VideoLink], filters: VideoFilterOptions) -> List[VideoLink]:
        """Apply filtering criteria to video links"""
        
    async def download_videos_batch(self, links: List[VideoLink], options: VideoDownloadOptions) -> BatchDownloadResult:
        """Download multiple videos concurrently with progress tracking"""
```

### 3. Video Link Extractor (`video_link_extractor.py`)

Specialized component for identifying and extracting video links from crawled content:

```python
class VideoLinkExtractor:
    def __init__(self):
        self.platform_extractors = {
            'youtube': YouTubeExtractor(),
            'vimeo': VimeoExtractor(),
            'direct': DirectVideoExtractor(),
            'embedded': EmbeddedVideoExtractor()
        }
    
    async def extract_all_video_links(self, crawled_content: CrawledContent) -> List[VideoLink]:
        """Extract video links from all supported platforms"""
        
    def detect_video_platform(self, url: str) -> str:
        """Detect which platform a video URL belongs to"""
        
    async def get_video_metadata(self, video_link: VideoLink) -> VideoMetadata:
        """Retrieve metadata for a video link"""
```

### 4. Batch Download Manager (`batch_download_manager.py`)

Manages concurrent video downloads with sophisticated progress tracking:

```python
class BatchDownloadManager:
    def __init__(self, media_downloader: MediaDownloader, max_concurrent: int = 3):
        self.media_downloader = media_downloader
        self.download_semaphore = asyncio.Semaphore(max_concurrent)
        self.active_downloads: Dict[str, DownloadTask] = {}
    
    async def download_videos_concurrently(self, 
                                         video_links: List[VideoLink],
                                         output_dir: Path,
                                         progress_callback: Callable) -> BatchDownloadResult:
        """Download multiple videos with concurrency control"""
        
    async def cancel_download(self, job_id: str) -> bool:
        """Cancel an active download job"""
        
    def get_download_progress(self, job_id: str) -> Optional[BatchDownloadProgress]:
        """Get current progress for a download job"""
```

### 5. Progress Tracker (`progress_tracker.py`)

Provides real-time progress updates via WebSocket and polling endpoints:

```python
class ProgressTracker:
    def __init__(self):
        self.job_progress: Dict[str, JobProgress] = {}
        self.websocket_connections: Dict[str, List[WebSocket]] = {}
    
    async def track_job_progress(self, job_id: str, progress_update: ProgressUpdate):
        """Update progress for a job and notify subscribers"""
        
    async def subscribe_to_progress(self, job_id: str, websocket: WebSocket):
        """Subscribe to progress updates via WebSocket"""
        
    def get_job_status(self, job_id: str) -> Optional[JobStatus]:
        """Get current status of a job"""
```

### 6. Agno Agent Integration (`video_scraping_agent.py`)

Integration with the agno agent framework for programmatic access:

```python
from agno.tools.base import Tool
from agno.models.message import Message

class VideoScrapingTool(Tool):
    name: str = "video_scraping"
    description: str = "Scrape and download videos from webpages"
    
    def __init__(self, orchestrator: VideoScrapingOrchestrator):
        super().__init__()
        self.orchestrator = orchestrator
    
    async def arun(self, url: str, **kwargs) -> str:
        """Run video scraping as an agent tool"""
        
class VideoScrapingAgent:
    def __init__(self, model_id: str):
        self.model = get_model(model_id)
        self.orchestrator = VideoScrapingOrchestrator(...)
        self.tools = [VideoScrapingTool(self.orchestrator)]
    
    async def scrape_videos(self, url: str, instructions: str) -> AgentResponse:
        """Agent method for video scraping with natural language instructions"""
```

## Data Models

### Core Data Models

```python
@dataclass
class VideoLink:
    url: str
    platform: str  # 'youtube', 'vimeo', 'direct', etc.
    title: Optional[str] = None
    thumbnail_url: Optional[str] = None
    duration_seconds: Optional[int] = None
    quality: Optional[str] = None
    file_size_mb: Optional[float] = None
    
@dataclass
class VideoMetadata:
    title: str
    description: str
    duration_seconds: int
    upload_date: Optional[datetime] = None
    uploader: Optional[str] = None
    view_count: Optional[int] = None
    tags: List[str] = field(default_factory=list)
    
@dataclass
class BatchDownloadJob:
    job_id: str
    url: str
    status: JobStatus
    created_at: datetime
    video_links: List[VideoLink]
    download_options: VideoDownloadOptions
    output_directory: str
    progress: BatchDownloadProgress
    
@dataclass
class BatchDownloadProgress:
    total_videos: int
    completed_downloads: int
    failed_downloads: int
    active_downloads: int
    total_size_mb: float
    downloaded_size_mb: float
    estimated_time_remaining_seconds: Optional[int] = None
    current_download_speeds_mbps: List[float] = field(default_factory=list)
    
@dataclass
class BatchDownloadResult:
    job_id: str
    success: bool
    total_videos: int
    successful_downloads: List[DownloadedVideo]
    failed_downloads: List[FailedDownload]
    download_statistics: DownloadStatistics
    output_directory: str
    
@dataclass
class DownloadedVideo:
    original_url: str
    local_file_path: str
    file_size_mb: float
    download_duration_seconds: float
    metadata: VideoMetadata
    
@dataclass
class FailedDownload:
    original_url: str
    error_message: str
    error_type: str
    retry_count: int
```

### API Request/Response Models

```python
class BatchVideoDownloadRequest(BaseModel):
    url: HttpUrl = Field(description="Webpage URL containing video links")
    download_options: Optional[VideoDownloadOptions] = Field(default=None)
    output_directory: Optional[str] = Field(default=None)
    filter_options: Optional[VideoFilterOptions] = Field(default=None)
    webhook_url: Optional[HttpUrl] = Field(default=None, description="URL to notify when job completes")

class BatchVideoDownloadResponse(BaseModel):
    success: bool
    job_id: str = Field(description="Unique identifier for tracking the job")
    message: str
    total_videos_found: int
    estimated_download_time_minutes: Optional[int] = None
    download_directory: str
    status_url: str = Field(description="URL to check job status")
    progress_websocket_url: str = Field(description="WebSocket URL for real-time progress")

class JobStatusResponse(BaseModel):
    job_id: str
    status: JobStatus
    progress: BatchDownloadProgress
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None
    result: Optional[BatchDownloadResult] = None
    error_message: Optional[str] = None

class JobProgressResponse(BaseModel):
    job_id: str
    progress: BatchDownloadProgress
    active_downloads: List[ActiveDownloadInfo]
    recent_completions: List[RecentDownloadInfo]
    timestamp: datetime
```

## Error Handling

### Exception Hierarchy

```python
class VideoScrapingError(Exception):
    """Base exception for video scraping operations"""
    pass

class VideoExtractionError(VideoScrapingError):
    """Raised when video links cannot be extracted from webpage"""
    pass

class BatchDownloadError(VideoScrapingError):
    """Raised when batch download operation fails"""
    pass

class VideoDownloadError(VideoScrapingError):
    """Raised when individual video download fails"""
    pass

class InsufficientStorageError(VideoScrapingError):
    """Raised when there's insufficient storage space"""
    pass

class UnsupportedVideoFormatError(VideoScrapingError):
    """Raised when video format is not supported"""
    pass
```

### Error Response Format

Following the existing API patterns:

```python
class ErrorResponse(BaseModel):
    success: bool = False
    error: str
    error_type: str
    detail: Optional[str] = None
    job_id: Optional[str] = None
    traceback: Optional[str] = None  # Only in debug mode
```

## Testing Strategy

### Unit Tests

1. **Video Link Extraction Tests**
   - Test extraction from various webpage types
   - Test platform-specific extractors
   - Test edge cases (no videos, malformed URLs)

2. **Download Manager Tests**
   - Test concurrent download limits
   - Test progress tracking accuracy
   - Test cancellation and cleanup

3. **API Endpoint Tests**
   - Test request validation
   - Test response formats
   - Test error handling

### Integration Tests

1. **End-to-End Workflow Tests**
   - Test complete scraping and download process
   - Test with real video platforms
   - Test with various webpage structures

2. **Agent Integration Tests**
   - Test agno agent tool functionality
   - Test model integration (AzureOpenAI, Gemini, Kimi)
   - Test agent error handling

### Performance Tests

1. **Concurrent Download Tests**
   - Test with multiple simultaneous jobs
   - Test resource usage under load
   - Test memory management with large files

2. **Scalability Tests**
   - Test with pages containing many videos
   - Test download speed optimization
   - Test storage efficiency

## Security Considerations

### Input Validation

1. **URL Validation**
   - Validate URL format and accessibility
   - Check for malicious or blocked domains
   - Implement rate limiting per domain

2. **File System Security**
   - Sanitize output directory paths
   - Prevent directory traversal attacks
   - Implement disk space quotas

### Access Control

1. **API Authentication**
   - Follow existing authentication patterns
   - Implement per-user download quotas
   - Log all download activities

2. **Resource Limits**
   - Limit concurrent downloads per user
   - Implement file size restrictions
   - Monitor bandwidth usage

## Performance Optimization

### Concurrent Processing

1. **Download Concurrency**
   - Configurable concurrent download limits
   - Intelligent queuing based on file sizes
   - Platform-specific optimization (YouTube-dl for YouTube)

2. **Memory Management**
   - Stream downloads to avoid memory issues
   - Cleanup temporary files promptly
   - Monitor memory usage during operations

### Caching Strategy

1. **Metadata Caching**
   - Cache video metadata to avoid repeated API calls
   - Cache webpage content for repeated processing
   - Implement TTL-based cache expiration

2. **Progress Persistence**
   - Persist job progress to handle server restarts
   - Resume interrupted downloads
   - Maintain download history

## Monitoring and Observability

### Logging Strategy

Following existing logging patterns:

```python
logger = logging.getLogger(__name__)

# Key events to log:
# - Job creation and completion
# - Video extraction results
# - Download progress milestones
# - Error conditions and retries
# - Performance metrics
```

### Metrics Collection

1. **Operational Metrics**
   - Jobs per hour/day
   - Success/failure rates
   - Average download speeds
   - Storage usage trends

2. **Performance Metrics**
   - API response times
   - Download completion times
   - Resource utilization
   - Error rates by type

### Health Checks

1. **Service Health**
   - MCP connection status
   - Storage availability
   - Download service status

2. **Dependency Health**
   - Firecrawl MCP server status
   - External video platform accessibility
   - File system health