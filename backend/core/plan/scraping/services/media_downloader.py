"""Media downloader for video files and other learning resources."""

import asyncio
import aiohttp
import aiofiles
import os
import shutil
import logging
from typing import Dict, List, Any, Optional, Callable, Tuple
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlparse, unquote
from datetime import datetime
import hashlib
import mimetypes

from ..models.learning_resource import VideoContent


@dataclass
class DownloadProgress:
    """Represents download progress information."""
    
    url: str
    filename: str
    total_bytes: Optional[int] = None
    downloaded_bytes: int = 0
    percentage: float = 0.0
    speed_mbps: float = 0.0
    eta_seconds: Optional[int] = None
    status: str = "pending"  # pending, downloading, completed, failed, cancelled
    error_message: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'url': self.url,
            'filename': self.filename,
            'total_bytes': self.total_bytes,
            'downloaded_bytes': self.downloaded_bytes,
            'percentage': self.percentage,
            'speed_mbps': self.speed_mbps,
            'eta_seconds': self.eta_seconds,
            'status': self.status,
            'error_message': self.error_message,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None
        }


@dataclass
class DownloadOptions:
    """Configuration options for downloading."""
    
    max_file_size_mb: int = 500  # Maximum file size in MB
    timeout_seconds: int = 300   # 5 minutes timeout
    chunk_size: int = 8192      # Download chunk size in bytes
    max_concurrent_downloads: int = 3
    retry_attempts: int = 3
    retry_delay: float = 1.0
    verify_ssl: bool = True
    user_agent: str = "FirecrawlLearningScraperDownloader/1.0"
    allowed_formats: List[str] = field(default_factory=lambda: [
        '.mp4', '.avi', '.mov', '.wmv', '.flv', '.webm', '.mkv',  # Video
        '.mp3', '.wav', '.aac', '.ogg', '.m4a',  # Audio
        '.pdf', '.epub', '.mobi',  # Documents
        '.zip', '.tar', '.gz', '.rar'  # Archives
    ])
    quality_preferences: List[str] = field(default_factory=lambda: [
        '1080p', '720p', '480p', '360p'
    ])


class DownloadError(Exception):
    """Base exception for download-related errors."""
    pass


class FileTooLargeError(DownloadError):
    """Exception raised when file exceeds size limit."""
    pass


class UnsupportedFormatError(DownloadError):
    """Exception raised for unsupported file formats."""
    pass


class InsufficientSpaceError(DownloadError):
    """Exception raised when there's insufficient disk space."""
    pass


class MediaDownloader:
    """Downloads video files and other media with progress tracking."""
    
    def __init__(self, download_options: Optional[DownloadOptions] = None):
        """Initialize the media downloader.
        
        Args:
            download_options: Download configuration options
        """
        self.options = download_options or DownloadOptions()
        self.logger = logging.getLogger(__name__)
        
        # Progress tracking
        self._active_downloads: Dict[str, DownloadProgress] = {}
        self._download_semaphore = asyncio.Semaphore(self.options.max_concurrent_downloads)
        self._session: Optional[aiohttp.ClientSession] = None
        
        # Statistics
        self._stats = {
            'total_downloads': 0,
            'successful_downloads': 0,
            'failed_downloads': 0,
            'total_bytes_downloaded': 0,
            'total_download_time': 0.0
        }
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self._create_session()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self._close_session()
    
    async def _create_session(self):
        """Create aiohttp session."""
        timeout = aiohttp.ClientTimeout(total=self.options.timeout_seconds)
        connector = aiohttp.TCPConnector(verify_ssl=self.options.verify_ssl)
        
        self._session = aiohttp.ClientSession(
            timeout=timeout,
            connector=connector,
            headers={'User-Agent': self.options.user_agent}
        )
    
    async def _close_session(self):
        """Close aiohttp session."""
        if self._session:
            await self._session.close()
            self._session = None
    
    async def download_video(
        self, 
        video_content: VideoContent, 
        output_dir: Path,
        progress_callback: Optional[Callable[[DownloadProgress], None]] = None
    ) -> Tuple[bool, Optional[str], Dict[str, Any]]:
        """Download a video file with progress tracking.
        
        Args:
            video_content: Video content to download
            output_dir: Directory to save the file
            progress_callback: Optional callback for progress updates
            
        Returns:
            Tuple of (success, file_path, metadata)
        """
        if not self._session:
            await self._create_session()
        
        async with self._download_semaphore:
            return await self._download_single_video(
                video_content, output_dir, progress_callback
            )
    
    async def _download_single_video(
        self,
        video_content: VideoContent,
        output_dir: Path,
        progress_callback: Optional[Callable[[DownloadProgress], None]] = None
    ) -> Tuple[bool, Optional[str], Dict[str, Any]]:
        """Download a single video file."""
        url = video_content.url
        self._stats['total_downloads'] += 1
        
        # Generate filename
        filename = self._generate_filename(video_content, url)
        output_path = output_dir / filename
        
        # Initialize progress tracking
        progress = DownloadProgress(
            url=url,
            filename=filename,
            start_time=datetime.now()
        )
        self._active_downloads[url] = progress
        
        metadata = {
            'original_url': url,
            'video_title': video_content.title,
            'download_start': progress.start_time.isoformat(),
            'filename': filename
        }
        
        try:
            # Validate URL and get file info
            file_info = await self._get_file_info(url)
            if not file_info['success']:
                raise DownloadError(f"Cannot access URL: {file_info['error']}")
            
            # Check file size
            file_size = file_info.get('content_length')
            if file_size and file_size > self.options.max_file_size_mb * 1024 * 1024:
                raise FileTooLargeError(
                    f"File size ({file_size / 1024 / 1024:.1f} MB) exceeds limit "
                    f"({self.options.max_file_size_mb} MB)"
                )
            
            # Check disk space
            if not self._check_disk_space(output_dir, file_size):
                raise InsufficientSpaceError("Insufficient disk space")
            
            # Check file format
            content_type = file_info.get('content_type', '')
            if not self._is_supported_format(filename, content_type):
                raise UnsupportedFormatError(f"Unsupported format: {content_type}")
            
            # Update progress
            progress.total_bytes = file_size
            progress.status = "downloading"
            if progress_callback:
                progress_callback(progress)
            
            # Download the file
            success = await self._download_file_with_progress(
                url, output_path, progress, progress_callback
            )
            
            if success:
                progress.status = "completed"
                progress.end_time = datetime.now()
                progress.percentage = 100.0
                
                # Update statistics
                self._stats['successful_downloads'] += 1
                self._stats['total_bytes_downloaded'] += progress.downloaded_bytes
                if progress.start_time and progress.end_time:
                    download_time = (progress.end_time - progress.start_time).total_seconds()
                    self._stats['total_download_time'] += download_time
                
                # Update metadata
                metadata.update({
                    'file_size_bytes': progress.downloaded_bytes,
                    'download_duration_seconds': download_time,
                    'download_end': progress.end_time.isoformat(),
                    'file_path': str(output_path)
                })
                
                if progress_callback:
                    progress_callback(progress)
                
                self.logger.info(f"Successfully downloaded: {filename}")
                return True, str(output_path), metadata
            else:
                raise DownloadError("Download failed")
                
        except Exception as e:
            progress.status = "failed"
            progress.error_message = str(e)
            progress.end_time = datetime.now()
            
            self._stats['failed_downloads'] += 1
            
            if progress_callback:
                progress_callback(progress)
            
            self.logger.error(f"Download failed for {url}: {e}")
            
            # Clean up partial file
            if output_path.exists():
                try:
                    output_path.unlink()
                except Exception as cleanup_error:
                    self.logger.warning(f"Failed to clean up partial file: {cleanup_error}")
            
            return False, None, metadata
        
        finally:
            # Remove from active downloads
            self._active_downloads.pop(url, None)
    
    async def _get_file_info(self, url: str) -> Dict[str, Any]:
        """Get file information via HEAD request."""
        try:
            async with self._session.head(url) as response:
                if response.status >= 400:
                    return {
                        'success': False,
                        'error': f"HTTP {response.status}"
                    }
                
                return {
                    'success': True,
                    'content_length': int(response.headers.get('content-length', 0)) or None,
                    'content_type': response.headers.get('content-type', ''),
                    'last_modified': response.headers.get('last-modified'),
                    'etag': response.headers.get('etag')
                }
        
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    async def _download_file_with_progress(
        self,
        url: str,
        output_path: Path,
        progress: DownloadProgress,
        progress_callback: Optional[Callable[[DownloadProgress], None]] = None
    ) -> bool:
        """Download file with progress tracking."""
        try:
            # Ensure output directory exists
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            async with self._session.get(url) as response:
                if response.status >= 400:
                    raise DownloadError(f"HTTP {response.status}")
                
                # Update total size if not known
                if not progress.total_bytes:
                    content_length = response.headers.get('content-length')
                    if content_length:
                        progress.total_bytes = int(content_length)
                
                async with aiofiles.open(output_path, 'wb') as file:
                    last_update_time = datetime.now()
                    last_downloaded = 0
                    
                    async for chunk in response.content.iter_chunked(self.options.chunk_size):
                        await file.write(chunk)
                        progress.downloaded_bytes += len(chunk)
                        
                        # Update progress periodically
                        now = datetime.now()
                        if (now - last_update_time).total_seconds() >= 1.0:  # Update every second
                            # Calculate speed
                            time_diff = (now - last_update_time).total_seconds()
                            bytes_diff = progress.downloaded_bytes - last_downloaded
                            speed_bps = bytes_diff / time_diff if time_diff > 0 else 0
                            progress.speed_mbps = speed_bps / (1024 * 1024)  # Convert to MB/s
                            
                            # Calculate percentage and ETA
                            if progress.total_bytes:
                                progress.percentage = (progress.downloaded_bytes / progress.total_bytes) * 100
                                remaining_bytes = progress.total_bytes - progress.downloaded_bytes
                                if speed_bps > 0:
                                    progress.eta_seconds = int(remaining_bytes / speed_bps)
                            
                            # Call progress callback
                            if progress_callback:
                                progress_callback(progress)
                            
                            last_update_time = now
                            last_downloaded = progress.downloaded_bytes
                
                return True
                
        except Exception as e:
            self.logger.error(f"Error downloading {url}: {e}")
            return False
    
    def _generate_filename(self, video_content: VideoContent, url: str) -> str:
        """Generate a safe filename for the video."""
        # Start with video title if available
        if video_content.title and video_content.title != "Video Content":
            base_name = video_content.title
        else:
            # Extract from URL
            parsed_url = urlparse(url)
            base_name = Path(unquote(parsed_url.path)).stem
            if not base_name:
                base_name = "video"
        
        # Clean filename
        base_name = self._sanitize_filename(base_name)
        
        # Determine file extension
        extension = self._get_file_extension(url, video_content)
        
        # Add timestamp to avoid conflicts
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Combine parts
        filename = f"{base_name}_{timestamp}{extension}"
        
        # Ensure filename isn't too long
        if len(filename) > 255:
            # Truncate base name
            max_base_length = 255 - len(f"_{timestamp}{extension}")
            base_name = base_name[:max_base_length]
            filename = f"{base_name}_{timestamp}{extension}"
        
        return filename
    
    def _sanitize_filename(self, filename: str) -> str:
        """Sanitize filename for filesystem compatibility."""
        # Remove or replace invalid characters
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            filename = filename.replace(char, '_')
        
        # Remove control characters
        filename = ''.join(char for char in filename if ord(char) >= 32)
        
        # Remove leading/trailing spaces and dots
        filename = filename.strip(' .')
        
        # Ensure it's not empty
        if not filename:
            filename = "untitled"
        
        return filename
    
    def _get_file_extension(self, url: str, video_content: VideoContent) -> str:
        """Determine appropriate file extension."""
        # Try to get extension from URL
        parsed_url = urlparse(url)
        url_path = unquote(parsed_url.path)
        
        if url_path:
            _, ext = os.path.splitext(url_path)
            if ext and ext.lower() in self.options.allowed_formats:
                return ext.lower()
        
        # Default based on platform
        if 'youtube' in url.lower():
            return '.mp4'
        elif 'vimeo' in url.lower():
            return '.mp4'
        elif 'dailymotion' in url.lower():
            return '.mp4'
        
        # Default extension
        return '.mp4'
    
    def _is_supported_format(self, filename: str, content_type: str) -> bool:
        """Check if file format is supported."""
        # Check by file extension
        _, ext = os.path.splitext(filename.lower())
        if ext in self.options.allowed_formats:
            return True
        
        # Check by MIME type
        if content_type:
            if content_type.startswith(('video/', 'audio/')):
                return True
            if content_type in ['application/pdf', 'application/zip']:
                return True
        
        return False
    
    def _check_disk_space(self, output_dir: Path, required_bytes: Optional[int]) -> bool:
        """Check if there's sufficient disk space."""
        if not required_bytes:
            return True  # Can't check without size info
        
        try:
            # Get free space
            statvfs = os.statvfs(output_dir)
            free_bytes = statvfs.f_bavail * statvfs.f_frsize
            
            # Add 10% buffer
            required_with_buffer = required_bytes * 1.1
            
            return free_bytes >= required_with_buffer
            
        except Exception as e:
            self.logger.warning(f"Could not check disk space: {e}")
            return True  # Assume OK if we can't check
    
    async def download_multiple_videos(
        self,
        video_contents: List[VideoContent],
        output_dir: Path,
        progress_callback: Optional[Callable[[str, DownloadProgress], None]] = None
    ) -> Dict[str, Tuple[bool, Optional[str], Dict[str, Any]]]:
        """Download multiple videos concurrently.
        
        Args:
            video_contents: List of video contents to download
            output_dir: Directory to save files
            progress_callback: Optional callback for progress updates (url, progress)
            
        Returns:
            Dictionary mapping URLs to download results
        """
        if not self._session:
            await self._create_session()
        
        # Create individual progress callbacks
        def create_callback(url: str):
            if progress_callback:
                return lambda progress: progress_callback(url, progress)
            return None
        
        # Create download tasks
        tasks = []
        for video_content in video_contents:
            callback = create_callback(video_content.url)
            task = self.download_video(video_content, output_dir, callback)
            tasks.append((video_content.url, task))
        
        # Execute downloads
        results = {}
        for url, task in tasks:
            try:
                result = await task
                results[url] = result
            except Exception as e:
                self.logger.error(f"Download task failed for {url}: {e}")
                results[url] = (False, None, {'error': str(e)})
        
        return results
    
    def get_download_progress(self, url: str) -> Optional[DownloadProgress]:
        """Get current download progress for a URL."""
        return self._active_downloads.get(url)
    
    def get_active_downloads(self) -> Dict[str, DownloadProgress]:
        """Get all active downloads."""
        return self._active_downloads.copy()
    
    def cancel_download(self, url: str) -> bool:
        """Cancel an active download."""
        progress = self._active_downloads.get(url)
        if progress and progress.status == "downloading":
            progress.status = "cancelled"
            progress.end_time = datetime.now()
            return True
        return False
    
    def get_download_statistics(self) -> Dict[str, Any]:
        """Get download statistics."""
        stats = self._stats.copy()
        
        if stats['successful_downloads'] > 0:
            stats['average_download_time'] = stats['total_download_time'] / stats['successful_downloads']
            stats['average_file_size_mb'] = (stats['total_bytes_downloaded'] / (1024 * 1024)) / stats['successful_downloads']
        else:
            stats['average_download_time'] = 0.0
            stats['average_file_size_mb'] = 0.0
        
        if stats['total_downloads'] > 0:
            stats['success_rate'] = stats['successful_downloads'] / stats['total_downloads']
        else:
            stats['success_rate'] = 0.0
        
        stats['total_size_downloaded_mb'] = stats['total_bytes_downloaded'] / (1024 * 1024)
        
        return stats
    
    def reset_statistics(self):
        """Reset download statistics."""
        self._stats = {
            'total_downloads': 0,
            'successful_downloads': 0,
            'failed_downloads': 0,
            'total_bytes_downloaded': 0,
            'total_download_time': 0.0
        }


class YouTubeDownloader:
    """Specialized downloader for YouTube videos using yt-dlp."""
    
    def __init__(self, download_options: Optional[DownloadOptions] = None):
        """Initialize YouTube downloader.
        
        Args:
            download_options: Download configuration options
        """
        self.options = download_options or DownloadOptions()
        self.logger = logging.getLogger(__name__)
    
    async def download_youtube_video(
        self,
        video_url: str,
        output_dir: Path,
        progress_callback: Optional[Callable[[DownloadProgress], None]] = None
    ) -> Tuple[bool, Optional[str], Dict[str, Any]]:
        """Download YouTube video using yt-dlp.
        
        Args:
            video_url: YouTube video URL
            output_dir: Directory to save the file
            progress_callback: Optional callback for progress updates
            
        Returns:
            Tuple of (success, file_path, metadata)
        """
        try:
            # Try to import yt-dlp
            import yt_dlp
        except ImportError:
            self.logger.error("yt-dlp not installed. Please install with: pip install yt-dlp")
            return False, None, {'error': 'yt-dlp not installed'}
        
        # Ensure output directory exists
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Configure yt-dlp options
        ydl_opts = {
            'outtmpl': str(output_dir / '%(title)s_%(id)s.%(ext)s'),
            'format': self._get_format_selector(),
            'writeinfojson': True,
            'writethumbnail': True,
            'writesubtitles': True,
            'writeautomaticsub': True,
            'ignoreerrors': False,
        }
        
        # Add progress hook if callback provided
        if progress_callback:
            ydl_opts['progress_hooks'] = [self._create_progress_hook(progress_callback)]
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # Extract info first
                info = ydl.extract_info(video_url, download=False)
                
                # Check file size
                if info.get('filesize') and info['filesize'] > self.options.max_file_size_mb * 1024 * 1024:
                    raise FileTooLargeError(
                        f"Video size ({info['filesize'] / 1024 / 1024:.1f} MB) exceeds limit"
                    )
                
                # Download the video
                ydl.download([video_url])
                
                # Find downloaded file
                downloaded_file = self._find_downloaded_file(output_dir, info.get('id', ''))
                
                metadata = {
                    'title': info.get('title'),
                    'duration': info.get('duration'),
                    'uploader': info.get('uploader'),
                    'upload_date': info.get('upload_date'),
                    'view_count': info.get('view_count'),
                    'like_count': info.get('like_count'),
                    'description': info.get('description'),
                    'tags': info.get('tags', []),
                    'categories': info.get('categories', []),
                    'thumbnail': info.get('thumbnail'),
                    'webpage_url': info.get('webpage_url'),
                    'video_id': info.get('id')
                }
                
                return True, downloaded_file, metadata
                
        except Exception as e:
            self.logger.error(f"YouTube download failed: {e}")
            return False, None, {'error': str(e)}
    
    def _get_format_selector(self) -> str:
        """Get format selector based on quality preferences."""
        formats = []
        for quality in self.options.quality_preferences:
            if quality == '1080p':
                formats.append('best[height<=1080]')
            elif quality == '720p':
                formats.append('best[height<=720]')
            elif quality == '480p':
                formats.append('best[height<=480]')
            elif quality == '360p':
                formats.append('best[height<=360]')
        
        # Fallback to best available
        formats.append('best')
        
        return '/'.join(formats)
    
    def _create_progress_hook(self, progress_callback: Callable[[DownloadProgress], None]):
        """Create progress hook for yt-dlp."""
        def hook(d):
            if d['status'] == 'downloading':
                progress = DownloadProgress(
                    url=d.get('info_dict', {}).get('webpage_url', ''),
                    filename=d.get('filename', ''),
                    total_bytes=d.get('total_bytes'),
                    downloaded_bytes=d.get('downloaded_bytes', 0),
                    percentage=d.get('_percent_str', '0%').rstrip('%'),
                    speed_mbps=(d.get('speed', 0) or 0) / (1024 * 1024),
                    eta_seconds=d.get('eta'),
                    status='downloading'
                )
                progress_callback(progress)
            elif d['status'] == 'finished':
                progress = DownloadProgress(
                    url=d.get('info_dict', {}).get('webpage_url', ''),
                    filename=d.get('filename', ''),
                    percentage=100.0,
                    status='completed'
                )
                progress_callback(progress)
        
        return hook
    
    def _find_downloaded_file(self, output_dir: Path, video_id: str) -> Optional[str]:
        """Find the downloaded video file."""
        # Look for files containing the video ID
        for file_path in output_dir.glob('*'):
            if file_path.is_file() and video_id in file_path.name:
                # Return the main video file (not .info.json or .jpg)
                if file_path.suffix in ['.mp4', '.webm', '.mkv', '.avi']:
                    return str(file_path)
        
        return None