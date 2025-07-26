"""Pydantic schemas for video processing API."""

from datetime import datetime
from typing import List, Optional, Dict, Any, Literal, Union
from pydantic import BaseModel, Field, HttpUrl, validator, root_validator, model_validator
from enum import Enum
import re
from urllib.parse import urlparse


class JobStatus(str, Enum):
    """Enumeration of job statuses."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class VideoFormat(str, Enum):
    """Supported video output formats."""
    MP4 = "mp4"
    WEBM = "webm"
    AVI = "avi"
    MOV = "mov"


class VideoQuality(str, Enum):
    """Video quality options."""
    LOW = "480p"
    MEDIUM = "720p"
    HIGH = "1080p"
    ULTRA = "1440p"


class TranscriptEntry(BaseModel):
    """Individual transcript entry with timestamp and knowledge point."""
    
    start_time: str = Field(
        description="Start time in format HH:MM:SS.mmm or MM:SS.mmm",
        example="00:01:23.456"
    )
    end_time: str = Field(
        description="End time in format HH:MM:SS.mmm or MM:SS.mmm", 
        example="00:02:45.789"
    )
    text: str = Field(
        description="Transcript text for this time segment",
        min_length=1
    )
    knowledge_point: Optional[str] = Field(
        None,
        description="Knowledge point or topic covered in this segment"
    )
    importance_level: int = Field(
        default=3,
        ge=1,
        le=5,
        description="Importance level from 1 (low) to 5 (high)"
    )
    keywords: List[str] = Field(
        default_factory=list,
        description="Keywords associated with this segment"
    )

    @validator('start_time', 'end_time')
    def validate_time_format(cls, v):
        """Validate time format (HH:MM:SS.mmm or MM:SS.mmm)."""
        time_pattern = r'^(?:(\d{1,2}):)?(\d{1,2}):(\d{1,2})(?:\.(\d{1,3}))?$'
        if not re.match(time_pattern, v):
            raise ValueError(f'Invalid time format: {v}. Expected HH:MM:SS.mmm or MM:SS.mmm')
        return v

    @model_validator(mode='before')
    @classmethod
    def validate_time_order(cls, values):
        """Validate that start_time is before end_time."""
        if isinstance(values, dict):
            start_time = values.get('start_time')
            end_time = values.get('end_time')
            
            if start_time and end_time:
                start_seconds = cls._time_to_seconds(start_time)
                end_seconds = cls._time_to_seconds(end_time)
                
                if start_seconds >= end_seconds:
                    raise ValueError('start_time must be before end_time')
        
        return values

    @staticmethod
    def _time_to_seconds(time_str: str) -> float:
        """Convert time string to seconds."""
        parts = time_str.split(':')
        if len(parts) == 2:  # MM:SS.mmm format
            minutes, seconds_part = parts
            hours = 0
        else:  # HH:MM:SS.mmm format
            hours, minutes, seconds_part = parts
        
        if '.' in seconds_part:
            seconds, milliseconds = seconds_part.split('.')
            milliseconds = int(milliseconds.ljust(3, '0')[:3])  # Pad or truncate to 3 digits
        else:
            seconds = seconds_part
            milliseconds = 0
        
        return int(hours) * 3600 + int(minutes) * 60 + int(seconds) + milliseconds / 1000


class TranscriptData(BaseModel):
    """Complete transcript data with entries and metadata."""
    
    entries: List[TranscriptEntry] = Field(
        description="List of transcript entries with timestamps",
        min_items=1
    )
    language: str = Field(
        default="en",
        description="Language code (e.g., 'en', 'zh-CN')"
    )
    total_duration: Optional[str] = Field(
        None,
        description="Total video duration in HH:MM:SS.mmm format"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata about the transcript"
    )

    @validator('entries')
    def validate_no_overlapping_segments(cls, v):
        """Validate that transcript entries don't overlap."""
        if len(v) <= 1:
            return v
        
        # Sort entries by start time
        sorted_entries = sorted(v, key=lambda x: TranscriptEntry._time_to_seconds(x.start_time))
        
        for i in range(len(sorted_entries) - 1):
            current_end = TranscriptEntry._time_to_seconds(sorted_entries[i].end_time)
            next_start = TranscriptEntry._time_to_seconds(sorted_entries[i + 1].start_time)
            
            if current_end > next_start:
                raise ValueError(f'Overlapping transcript segments detected: {sorted_entries[i].end_time} > {sorted_entries[i + 1].start_time}')
        
        return v


class VideoProcessingOptions(BaseModel):
    """Options for video processing."""
    
    output_format: VideoFormat = Field(
        default=VideoFormat.MP4,
        description="Output video format"
    )
    quality: VideoQuality = Field(
        default=VideoQuality.MEDIUM,
        description="Video quality setting"
    )
    preserve_audio: bool = Field(
        default=True,
        description="Whether to preserve audio in segments"
    )
    segment_padding_seconds: float = Field(
        default=0.5,
        ge=0,
        le=5,
        description="Padding to add before/after each segment in seconds"
    )
    max_segment_duration_minutes: int = Field(
        default=30,
        ge=1,
        le=120,
        description="Maximum duration for a single segment in minutes"
    )
    output_directory: Optional[str] = Field(
        None,
        description="Custom output directory path"
    )
    segment_naming_pattern: str = Field(
        default="{knowledge_point}_{start_time}_{end_time}",
        description="Pattern for naming segment files"
    )


class VideoProcessingRequest(BaseModel):
    """Request model for video processing."""
    
    video_url: HttpUrl = Field(
        description="URL of the video to process"
    )
    transcript_data: TranscriptData = Field(
        description="Transcript data with timestamps and knowledge points"
    )
    processing_options: Optional[VideoProcessingOptions] = Field(
        default_factory=VideoProcessingOptions,
        description="Processing options and preferences"
    )
    job_name: Optional[str] = Field(
        None,
        max_length=255,
        description="Optional name for the processing job"
    )
    webhook_url: Optional[HttpUrl] = Field(
        None,
        description="URL to notify when processing completes"
    )

    @validator('video_url')
    def validate_video_url(cls, v):
        """Validate that the URL is accessible and appears to be a video."""
        url_str = str(v)
        parsed = urlparse(url_str)
        
        # Check for common video platforms
        video_platforms = [
            'youtube.com', 'youtu.be', 'vimeo.com', 'dailymotion.com',
            'twitch.tv', 'facebook.com', 'instagram.com'
        ]
        
        # Check for direct video file extensions
        video_extensions = ['.mp4', '.webm', '.avi', '.mov', '.mkv', '.flv', '.wmv']
        
        is_platform = any(platform in parsed.netloc.lower() for platform in video_platforms)
        is_direct_video = any(url_str.lower().endswith(ext) for ext in video_extensions)
        
        if not (is_platform or is_direct_video):
            # Allow other URLs but warn they might not be videos
            pass
        
        return v


class VideoSegmentMetadata(BaseModel):
    """Metadata for a processed video segment."""
    
    segment_id: str = Field(description="Unique identifier for the segment")
    knowledge_point: Optional[str] = Field(description="Knowledge point covered")
    start_time: str = Field(description="Segment start time")
    end_time: str = Field(description="Segment end time")
    duration_seconds: float = Field(description="Segment duration in seconds")
    file_path: str = Field(description="Path to the segment file")
    file_size_mb: float = Field(description="File size in megabytes")
    title: str = Field(description="Generated title for the segment")
    description: Optional[str] = Field(None, description="Segment description")
    keywords: List[str] = Field(default_factory=list, description="Associated keywords")
    importance_level: int = Field(description="Importance level (1-5)")
    thumbnail_path: Optional[str] = Field(None, description="Path to thumbnail image")


class VideoProcessingProgress(BaseModel):
    """Progress information for video processing."""
    
    job_id: str = Field(description="Job identifier")
    status: JobStatus = Field(description="Current job status")
    progress_percentage: float = Field(
        ge=0, le=100, description="Progress percentage (0-100)"
    )
    current_step: str = Field(description="Current processing step")
    total_segments: int = Field(description="Total number of segments to process")
    completed_segments: int = Field(description="Number of completed segments")
    estimated_time_remaining_seconds: Optional[int] = Field(
        None, description="Estimated time remaining in seconds"
    )
    processing_speed_mbps: Optional[float] = Field(
        None, description="Current processing speed in MB/s"
    )
    error_message: Optional[str] = Field(None, description="Error message if failed")
    created_at: datetime = Field(description="Job creation timestamp")
    updated_at: datetime = Field(description="Last update timestamp")


class VideoProcessingResult(BaseModel):
    """Result of video processing operation."""
    
    job_id: str = Field(description="Job identifier")
    success: bool = Field(description="Whether processing was successful")
    original_video_url: str = Field(description="Original video URL")
    total_segments: int = Field(description="Total number of segments created")
    segments: List[VideoSegmentMetadata] = Field(
        description="List of processed segments"
    )
    processing_duration_seconds: float = Field(
        description="Total processing time in seconds"
    )
    output_directory: str = Field(description="Directory containing output files")
    total_output_size_mb: float = Field(description="Total size of output files")
    statistics: Dict[str, Any] = Field(
        default_factory=dict,
        description="Processing statistics and metrics"
    )
    created_at: datetime = Field(description="Job creation timestamp")
    completed_at: datetime = Field(description="Job completion timestamp")


class VideoProcessingResponse(BaseModel):
    """Response model for video processing request."""
    
    success: bool = Field(description="Whether the request was accepted")
    job_id: str = Field(description="Unique job identifier for tracking")
    message: str = Field(description="Response message")
    estimated_processing_time_minutes: Optional[int] = Field(
        None, description="Estimated processing time in minutes"
    )
    total_segments_to_create: int = Field(
        description="Number of segments that will be created"
    )
    status_url: str = Field(description="URL to check job status")
    progress_url: str = Field(description="URL to get progress updates")
    created_at: datetime = Field(
        default_factory=datetime.now,
        description="Request timestamp"
    )


class JobStatusResponse(BaseModel):
    """Response model for job status queries."""
    
    job_id: str = Field(description="Job identifier")
    status: JobStatus = Field(description="Current job status")
    progress: Optional[VideoProcessingProgress] = Field(
        None, description="Progress information if available"
    )
    result: Optional[VideoProcessingResult] = Field(
        None, description="Result if job is completed"
    )
    error_message: Optional[str] = Field(
        None, description="Error message if job failed"
    )
    created_at: datetime = Field(description="Job creation timestamp")
    updated_at: datetime = Field(description="Last update timestamp")


class VideoSegmentAnalysisRequest(BaseModel):
    """Request model for video transcript segment analysis."""
    
    resource_id: int = Field(
        description="ID of the learning resource to analyze",
        gt=0
    )


class VideoSegmentData(BaseModel):
    """Data model for a single video segment."""
    
    start_time: float = Field(
        description="Start time in seconds",
        ge=0
    )
    end_time: float = Field(
        description="End time in seconds", 
        gt=0
    )
    knowledge_id: int = Field(
        description="ID of the knowledge point for this segment",
        gt=0
    )
    summary: str = Field(
        description="Summary description of this segment",
        min_length=1,
        max_length=1000
    )

    @model_validator(mode='before')
    @classmethod
    def validate_time_order(cls, values):
        """Validate that start_time is before end_time."""
        if isinstance(values, dict):
            start_time = values.get('start_time')
            end_time = values.get('end_time')
            
            if start_time is not None and end_time is not None:
                if start_time >= end_time:
                    raise ValueError('start_time must be before end_time')
        
        return values


class VideoSegmentAnalysisJobResponse(BaseModel):
    """Response model for starting video segment analysis."""
    
    success: bool = Field(description="Whether the request was accepted")
    job_id: str = Field(description="Unique job identifier for tracking")
    message: str = Field(description="Response message")
    status_url: str = Field(description="URL to check job status")
    created_at: datetime = Field(
        default_factory=datetime.now,
        description="Request timestamp"
    )


class VideoSegmentAnalysisStatus(BaseModel):
    """Status information for video segment analysis job."""
    
    job_id: str = Field(description="Job identifier")
    status: JobStatus = Field(description="Current job status")
    message: Optional[str] = Field(None, description="Status message")
    progress_percentage: Optional[float] = Field(
        None, ge=0, le=100, description="Progress percentage (0-100)"
    )
    current_step: Optional[str] = Field(None, description="Current processing step")
    segments_created: Optional[int] = Field(None, description="Number of segments created")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    created_at: datetime = Field(description="Job creation timestamp")
    updated_at: datetime = Field(description="Last update timestamp")


class ErrorResponse(BaseModel):
    """Standard error response model."""
    
    success: bool = Field(default=False, description="Always false for errors")
    error: str = Field(description="Error message")
    error_type: str = Field(description="Type of error")
    detail: Optional[str] = Field(None, description="Detailed error information")
    job_id: Optional[str] = Field(None, description="Job ID if applicable")
    timestamp: datetime = Field(
        default_factory=datetime.now,
        description="Error timestamp"
    )


class FileUploadAnalysisJobResponse(BaseModel):
    """Response model for starting file upload analysis."""
    
    success: bool = Field(description="Whether the request was accepted")
    job_id: str = Field(description="Unique job identifier for tracking")
    resource_id: int = Field(description="ID of the newly created resource record")
    message: str = Field(description="Response message")
    status_url: str = Field(description="URL to check job status")
    filename: str = Field(description="Name of the uploaded file")
    file_size_bytes: int = Field(description="Size of the uploaded file in bytes")
    knowledge_context_id: int = Field(description="Knowledge context ID used for analysis")
    created_at: datetime = Field(
        default_factory=datetime.now,
        description="Request timestamp"
    )


class TranscriptFileFormat(str, Enum):
    """Supported transcript file formats."""
    VTT = "vtt"
    SRT = "srt"
    TXT = "txt"
    JSON = "json"


class FileValidationError(BaseModel):
    """File validation error details."""
    
    field: str = Field(description="Field that caused the error")
    message: str = Field(description="Error message")
    line_number: Optional[int] = Field(None, description="Line number where error occurred")


class FileUploadValidationResponse(BaseModel):
    """Response for file upload validation."""
    
    is_valid: bool = Field(description="Whether the file is valid")
    format_detected: Optional[TranscriptFileFormat] = Field(None, description="Detected file format")
    content_length: int = Field(description="Length of file content in characters")
    line_count: int = Field(description="Number of lines in the file")
    estimated_duration_minutes: Optional[float] = Field(None, description="Estimated video duration in minutes")
    errors: List[FileValidationError] = Field(default_factory=list, description="Validation errors if any")
    warnings: List[str] = Field(default_factory=list, description="Validation warnings")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional file metadata")


# Utility functions for validation
def validate_video_url_format(url: str) -> bool:
    """Validate if URL appears to be a video URL."""
    try:
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            return False
        
        # Check for video platforms or direct video files
        video_platforms = [
            'youtube.com', 'youtu.be', 'vimeo.com', 'dailymotion.com'
        ]
        video_extensions = ['.mp4', '.webm', '.avi', '.mov', '.mkv']
        
        is_platform = any(platform in parsed.netloc.lower() for platform in video_platforms)
        is_direct_video = any(url.lower().endswith(ext) for ext in video_extensions)
        
        return is_platform or is_direct_video
    except Exception:
        return False


def validate_transcript_format(transcript_data: Dict[str, Any]) -> List[str]:
    """Validate transcript data format and return list of validation errors."""
    errors = []
    
    try:
        # Try to create TranscriptData object to validate
        TranscriptData(**transcript_data)
    except Exception as e:
        errors.append(str(e))
    
    return errors


def generate_segment_filename(
    knowledge_point: Optional[str],
    start_time: str,
    end_time: str,
    pattern: str = "{knowledge_point}_{start_time}_{end_time}",
    extension: str = "mp4"
) -> str:
    """Generate filename for video segment based on pattern."""
    # Clean knowledge point for filename
    clean_knowledge_point = "segment"
    if knowledge_point:
        clean_knowledge_point = re.sub(r'[^\w\s-]', '', knowledge_point)
        clean_knowledge_point = re.sub(r'[-\s]+', '_', clean_knowledge_point)
    
    # Clean time strings for filename
    clean_start = start_time.replace(':', '-').replace('.', '_')
    clean_end = end_time.replace(':', '-').replace('.', '_')
    
    # Format filename
    filename = pattern.format(
        knowledge_point=clean_knowledge_point,
        start_time=clean_start,
        end_time=clean_end
    )
    
    # Ensure filename is safe
    filename = re.sub(r'[^\w\s-_.]', '', filename)
    filename = re.sub(r'[-\s_]+', '_', filename)
    
    return f"{filename}.{extension}"


# Utility functions for file processing
def detect_transcript_format(content: str, filename: str) -> Optional[TranscriptFileFormat]:
    """Detect transcript file format from content and filename."""
    filename_lower = filename.lower()
    
    # Check by file extension first
    if filename_lower.endswith('.vtt'):
        return TranscriptFileFormat.VTT
    elif filename_lower.endswith('.srt'):
        return TranscriptFileFormat.SRT
    elif filename_lower.endswith('.txt'):
        return TranscriptFileFormat.TXT
    elif filename_lower.endswith('.json'):
        return TranscriptFileFormat.JSON
    
    # Check by content patterns
    content_lower = content.lower().strip()
    
    # VTT format detection
    if content_lower.startswith('webvtt') or 'webvtt' in content_lower[:100]:
        return TranscriptFileFormat.VTT
    
    # SRT format detection (numbered sequences with timestamps)
    srt_pattern = r'^\d+\s*\n\d{2}:\d{2}:\d{2},\d{3}\s*-->\s*\d{2}:\d{2}:\d{2},\d{3}'
    if re.search(srt_pattern, content, re.MULTILINE):
        return TranscriptFileFormat.SRT
    
    # JSON format detection
    try:
        import json
        json.loads(content)
        return TranscriptFileFormat.JSON
    except:
        pass
    
    # Default to TXT if no specific format detected
    return TranscriptFileFormat.TXT


def validate_transcript_file_content(content: str, format_type: TranscriptFileFormat) -> FileUploadValidationResponse:
    """Validate transcript file content based on its format."""
    errors = []
    warnings = []
    metadata = {}
    
    lines = content.split('\n')
    line_count = len(lines)
    content_length = len(content)
    
    if format_type == TranscriptFileFormat.VTT:
        errors.extend(_validate_vtt_format(content, lines))
    elif format_type == TranscriptFileFormat.SRT:
        errors.extend(_validate_srt_format(content, lines))
    elif format_type == TranscriptFileFormat.JSON:
        errors.extend(_validate_json_format(content))
    elif format_type == TranscriptFileFormat.TXT:
        errors.extend(_validate_txt_format(content, lines))
    
    # General validations
    if content_length < 50:
        errors.append(FileValidationError(
            field="content",
            message="File content is too short - transcript must contain at least 50 characters"
        ))
    
    if content_length > 1000000:  # 1MB limit
        errors.append(FileValidationError(
            field="content",
            message="File is too large. Maximum size is 1MB"
        ))
    
    # Estimate duration based on content length (rough estimate)
    estimated_duration = None
    if content_length > 0:
        # Rough estimate: ~150 words per minute, ~5 characters per word
        estimated_words = content_length / 5
        estimated_duration = estimated_words / 150
    
    return FileUploadValidationResponse(
        is_valid=len(errors) == 0,
        format_detected=format_type,
        content_length=content_length,
        line_count=line_count,
        estimated_duration_minutes=estimated_duration,
        errors=errors,
        warnings=warnings,
        metadata=metadata
    )


def _validate_vtt_format(content: str, lines: List[str]) -> List[FileValidationError]:
    """Validate VTT format specific rules."""
    errors = []
    
    # Check for WEBVTT header
    if not content.strip().startswith('WEBVTT'):
        errors.append(FileValidationError(
            field="header",
            message="VTT file must start with 'WEBVTT'",
            line_number=1
        ))
    
    # Check for timestamp patterns
    timestamp_pattern = r'\d{2}:\d{2}:\d{2}\.\d{3}\s*-->\s*\d{2}:\d{2}:\d{2}\.\d{3}'
    if not re.search(timestamp_pattern, content):
        errors.append(FileValidationError(
            field="timestamps",
            message="No valid VTT timestamps found (expected format: HH:MM:SS.mmm --> HH:MM:SS.mmm)"
        ))
    
    return errors


def _validate_srt_format(content: str, lines: List[str]) -> List[FileValidationError]:
    """Validate SRT format specific rules."""
    errors = []
    
    # Check for SRT timestamp pattern
    timestamp_pattern = r'\d{2}:\d{2}:\d{2},\d{3}\s*-->\s*\d{2}:\d{2}:\d{2},\d{3}'
    if not re.search(timestamp_pattern, content):
        errors.append(FileValidationError(
            field="timestamps",
            message="No valid SRT timestamps found (expected format: HH:MM:SS,mmm --> HH:MM:SS,mmm)"
        ))
    
    # Check for sequence numbers
    sequence_pattern = r'^\d+\s*$'
    has_sequences = any(re.match(sequence_pattern, line.strip()) for line in lines if line.strip())
    if not has_sequences:
        errors.append(FileValidationError(
            field="sequences",
            message="SRT files should contain sequence numbers"
        ))
    
    return errors


def _validate_json_format(content: str) -> List[FileValidationError]:
    """Validate JSON format transcript."""
    errors = []
    
    try:
        import json
        data = json.loads(content)
        
        # Check if it's a valid transcript JSON structure
        if not isinstance(data, (list, dict)):
            errors.append(FileValidationError(
                field="structure",
                message="JSON must be an object or array"
            ))
        
        # If it's a list, check if entries have required fields
        if isinstance(data, list) and len(data) > 0:
            first_item = data[0]
            required_fields = ['start_time', 'end_time', 'text']
            missing_fields = [field for field in required_fields if field not in first_item]
            if missing_fields:
                errors.append(FileValidationError(
                    field="entries",
                    message=f"JSON entries missing required fields: {missing_fields}"
                ))
    
    except json.JSONDecodeError as e:
        errors.append(FileValidationError(
            field="json",
            message=f"Invalid JSON format: {str(e)}"
        ))
    
    return errors


def _validate_txt_format(content: str, lines: List[str]) -> List[FileValidationError]:
    """Validate TXT format specific rules."""
    errors = []
    
    # Check for meaningful content - not just a simple error message
    content_lower = content.lower().strip()
    invalid_phrases = [
        "this is not a valid transcript",
        "invalid file",
        "error",
        "not found",
        "file not supported"
    ]
    
    if any(phrase in content_lower for phrase in invalid_phrases):
        errors.append(FileValidationError(
            field="content",
            message="File appears to contain error message rather than transcript content"
        ))
    
    # Check for at least some structured content (multiple lines with meaningful text)
    meaningful_lines = [line for line in lines if line.strip() and len(line.strip()) > 10]
    if len(meaningful_lines) < 3:
        errors.append(FileValidationError(
            field="content",
            message="TXT transcript must contain at least 3 meaningful lines of text"
        ))
    
    # Check for some indication of time-based content
    time_indicators = [':', '时间', '秒', 'min', 'minute', 'second', '分钟']
    has_time_indicators = any(indicator in content_lower for indicator in time_indicators)
    if not has_time_indicators:
        errors.append(FileValidationError(
            field="content",
            message="TXT transcript should contain time-related information or timestamps"
        ))
    
    return errors


def generate_resource_title_from_filename(filename: str) -> str:
    """Generate a clean resource title from uploaded filename."""
    # Remove extension
    name = filename.rsplit('.', 1)[0] if '.' in filename else filename
    
    # Replace underscores and hyphens with spaces
    name = re.sub(r'[-_]+', ' ', name)
    
    # Capitalize first letter of each word
    name = ' '.join(word.capitalize() for word in name.split())
    
    # Add prefix to indicate it's uploaded
    return f"Uploaded Transcript: {name}"


class VideoLinkAnalysisRequest(BaseModel):
    """Request model for video link analysis with automatic transcript extraction."""
    
    video_url: HttpUrl = Field(
        description="URL of the video to analyze (YouTube, Vimeo, etc.)",
        example="https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    )
    knowledge_context_id: int = Field(
        description="用于查找关联知识点的上下文ID，例如 course_id",
        gt=0
    )
    preferred_subtitle_language: str = Field(
        default="en",
        description="Preferred subtitle language code (e.g., 'en', 'zh-Hans', 'zh-TW')",
        example="en"
    )
    resource_title: Optional[str] = Field(
        None,
        max_length=255,
        description="Optional custom title for the learning resource (will use video title if not provided)"
    )

    @validator('video_url')
    def validate_video_url(cls, v):
        """Validate that the URL is a supported video platform."""
        url_str = str(v)
        parsed = urlparse(url_str)
        
        # Check for supported video platforms
        supported_platforms = [
            'youtube.com', 'youtu.be', 'vimeo.com', 'dailymotion.com'
        ]
        
        is_supported_platform = any(platform in parsed.netloc.lower() for platform in supported_platforms)
        
        if not is_supported_platform:
            raise ValueError(f'Unsupported video platform. Supported platforms: {", ".join(supported_platforms)}')
        
        return v


class VideoLinkAnalysisJobResponse(BaseModel):
    """Response model for starting video link analysis."""
    
    success: bool = Field(description="Whether the request was accepted")
    job_id: str = Field(description="Unique job identifier for tracking")
    resource_id: int = Field(description="ID of the newly created resource record")
    message: str = Field(description="Response message")
    status_url: str = Field(description="URL to check job status")
    video_url: str = Field(description="Original video URL")
    video_title: Optional[str] = Field(None, description="Extracted video title if available")
    estimated_duration_minutes: Optional[float] = Field(None, description="Estimated video duration in minutes")
    knowledge_context_id: int = Field(description="Knowledge context ID used for analysis")
    created_at: datetime = Field(
        default_factory=datetime.now,
        description="Request timestamp"
    )