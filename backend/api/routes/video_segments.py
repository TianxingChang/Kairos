"""Video segment analysis API routes."""

import asyncio
import json
import logging
import uuid
from datetime import datetime
from typing import Dict, List, Optional
import tempfile
import os
import sys
from pathlib import Path

# Add scraping module to path
sys.path.append(str(Path(__file__).parent.parent.parent / "core" / "plan"))

from fastapi import APIRouter, HTTPException, status, Depends, BackgroundTasks, File, UploadFile, Form
from sqlalchemy.orm import Session
from sqlalchemy import and_
import yt_dlp
import threading

# 添加全局锁来防止yt-dlp并发问题
_ytdlp_lock = threading.Lock()

from db.session import get_db
from db.models import LearningResource, Knowledge, VideoSegment
from api.schemas.video_processing_schemas import (
    VideoSegmentAnalysisRequest,
    VideoSegmentAnalysisJobResponse,
    VideoSegmentAnalysisStatus,
    VideoSegmentData,
    JobStatus,
    ErrorResponse,
    FileUploadAnalysisJobResponse,
    TranscriptFileFormat,
    FileUploadValidationResponse,
    detect_transcript_format,
    validate_transcript_file_content,
    generate_resource_title_from_filename,
    VideoLinkAnalysisRequest,
    VideoLinkAnalysisJobResponse
)
from agents.selector import AgentType, get_agent
from services.knowledge_service import get_l3_atomic_knowledge_points

logger = logging.getLogger(__name__)

video_segments_router = APIRouter(prefix="/videos", tags=["Video Segments"])

# 简单的内存存储任务状态 (生产环境应使用 Redis)
job_status_store: Dict[str, Dict] = {}


@video_segments_router.post(
    "/analyze-segments", 
    response_model=VideoSegmentAnalysisJobResponse,
    status_code=status.HTTP_202_ACCEPTED
)
async def analyze_video_segments(
    request: VideoSegmentAnalysisRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    分析视频文稿并按知识点进行智能分段
    
    此接口会启动一个后台任务来执行分析，并立即返回 job_id 供客户端查询状态。
    """
    try:
        # 验证资源是否存在
        resource = db.query(LearningResource).filter(
            LearningResource.id == request.resource_id
        ).first()
        
        if not resource:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Learning resource with id {request.resource_id} not found"
            )
        
        if not resource.transcript:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Learning resource {request.resource_id} has no transcript data"
            )
        
        # 创建唯一的 job_id
        job_id = str(uuid.uuid4())
        
        # 初始化任务状态
        job_status_store[job_id] = {
            "job_id": job_id,
            "status": JobStatus.PENDING,
            "message": "Job created, waiting to start processing",
            "resource_id": request.resource_id,
            "progress_percentage": 0,
            "current_step": "Initializing",
            "segments_created": 0,
            "error_message": None,
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        }
        
        # 启动后台任务
        background_tasks.add_task(
            process_video_segment_analysis,
            job_id,
            request.resource_id,
            db
        )
        
        return VideoSegmentAnalysisJobResponse(
            success=True,
            job_id=job_id,
            message=f"Video segment analysis job created successfully for resource {request.resource_id}",
            status_url=f"/api/v1/videos/analyze-segments/status/{job_id}",
            created_at=datetime.now()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create video segment analysis job: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create analysis job: {str(e)}"
        )


@video_segments_router.post(
    "/analyze-segments-from-file", 
    response_model=FileUploadAnalysisJobResponse,
    status_code=status.HTTP_202_ACCEPTED
)
async def analyze_video_segments_from_file(
    transcript_file: UploadFile = File(..., description="用户上传的transcript文件 (.vtt, .srt, .txt)"),
    knowledge_context_id: int = Form(..., description="用于查找关联知识点的上下文ID，例如 course_id"),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: Session = Depends(get_db)
):
    """
    分析用户上传的transcript文件并按知识点进行智能分段
    
    这是新的文件上传版本的API，支持：
    - 上传transcript文件（支持VTT、SRT、TXT格式）
    - 指定知识点上下文ID来确定候选知识点范围
    - 自动创建新的学习资源记录
    - 异步处理和状态查询
    """
    try:
        # 验证文件
        if not transcript_file.filename:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="文件名不能为空"
            )
        
        # 读取文件内容
        try:
            file_content = await transcript_file.read()
            content_str = file_content.decode('utf-8')
        except UnicodeDecodeError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="文件编码错误，请确保文件是UTF-8编码"
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"读取文件失败: {str(e)}"
            )
        
        # 检测和验证文件格式
        detected_format = detect_transcript_format(content_str, transcript_file.filename)
        validation_result = validate_transcript_file_content(content_str, detected_format)
        
        if not validation_result.is_valid:
            error_messages = [error.message for error in validation_result.errors]
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"文件格式验证失败: {'; '.join(error_messages)}"
            )
        
        # 验证知识点上下文ID（这里可以根据实际需求调整验证逻辑）
        knowledge_points = db.query(Knowledge).filter(
            Knowledge.is_active == True
        ).all()
        
        if not knowledge_points:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="未找到可用的知识点，请先创建知识点"
            )
        
        # 创建新的学习资源记录
        resource_title = generate_resource_title_from_filename(transcript_file.filename)
        new_resource = LearningResource(
            title=resource_title,
            resource_type="uploaded_transcript",
            resource_url=f"uploaded://{transcript_file.filename}",
            description=f"用户上传的transcript文件，文件名: {transcript_file.filename}",
            transcript=content_str,
            language="zh",  # 默认中文，可以根据需要检测
            is_available=True
        )
        
        db.add(new_resource)
        db.commit()
        db.refresh(new_resource)
        
        logger.info(f"Created new resource with ID {new_resource.id} for uploaded file: {transcript_file.filename}")
        
        # 生成任务ID
        job_id = str(uuid.uuid4())
        
        # 初始化任务状态
        _update_job_status(
            job_id,
            JobStatus.PENDING,
            "File uploaded successfully, analysis task created",
            progress=5,
            segments_created=0
        )
        
        # 启动后台任务
        background_tasks.add_task(
            process_file_upload_segment_analysis,
            job_id,
            new_resource.id,
            content_str,
            knowledge_context_id,
            db
        )
        
        # 生成状态查询URL
        status_url = f"/api/v1/videos/analyze-segments/status/{job_id}"
        
        logger.info(f"File upload analysis job {job_id} created for resource {new_resource.id}")
        
        return FileUploadAnalysisJobResponse(
            success=True,
            job_id=job_id,
            resource_id=new_resource.id,
            message=f"File '{transcript_file.filename}' uploaded and analysis job created successfully",
            status_url=status_url,
            filename=transcript_file.filename,
            file_size_bytes=len(file_content),
            knowledge_context_id=knowledge_context_id
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create file upload analysis job: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"创建分析任务失败: {str(e)}"
        )


@video_segments_router.post(
    "/analyze-segments-from-video-link", 
    response_model=VideoLinkAnalysisJobResponse,
    status_code=status.HTTP_202_ACCEPTED
)
async def analyze_video_segments_from_link(
    request: VideoLinkAnalysisRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    分析视频链接并自动提取字幕进行智能分段
    
    支持从YouTube、Vimeo等平台自动提取VTT字幕，然后按知识点进行智能分段。
    """
    try:
        # 创建唯一的 job_id
        job_id = str(uuid.uuid4())
        
        # 预创建学习资源记录（状态为处理中）
        resource = LearningResource(
            title=request.resource_title or f"Video: {request.video_url}",
            resource_url=str(request.video_url),
            resource_type="video",
            description=f"Video analysis from link: {request.video_url} (extracting transcript)",
            transcript="",  # 将在后台任务中填充
            language=request.preferred_subtitle_language or "en"
        )
        
        db.add(resource)
        db.commit()
        db.refresh(resource)
        
        # 初始化任务状态
        job_status_store[job_id] = {
            "job_id": job_id,
            "status": JobStatus.PENDING,
            "message": "Job created, starting transcript extraction from video link",
            "resource_id": resource.id,
            "video_url": str(request.video_url),
            "progress_percentage": 0,
            "current_step": "Extracting video transcript",
            "segments_created": 0,
            "error_message": None,
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        }
        
        # 启动后台任务
        background_tasks.add_task(
            process_video_link_analysis,
            job_id,
            resource.id,
            str(request.video_url),
            request.knowledge_context_id,
            request.preferred_subtitle_language,
            db
        )
        
        logger.info(f"Started video link analysis job {job_id} for resource {resource.id}")
        
        return VideoLinkAnalysisJobResponse(
            success=True,
            job_id=job_id,
            resource_id=resource.id,
            message="Video link analysis job started successfully. Extracting transcript...",
            status_url=f"/v1/videos/analyze-segments/status/{job_id}",
            video_url=str(request.video_url),
            knowledge_context_id=request.knowledge_context_id
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建视频链接分析任务失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"创建视频链接分析任务失败: {str(e)}"
        )


@video_segments_router.get(
    "/analyze-segments/status/{job_id}",
    response_model=VideoSegmentAnalysisStatus
)
async def get_analysis_status(job_id: str):
    """
    查询视频分段分析任务的状态
    """
    try:
        if job_id not in job_status_store:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Job {job_id} not found"
            )
        
        job_data = job_status_store[job_id]
        
        return VideoSegmentAnalysisStatus(**job_data)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get job status for {job_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get job status: {str(e)}"
        )


async def process_video_segment_analysis(job_id: str, resource_id: int, db: Session):
    """
    后台任务：执行视频分段分析的核心逻辑
    """
    try:
        # 更新状态为处理中
        _update_job_status(job_id, JobStatus.PROCESSING, "Starting analysis", 10)
        
        # Step 1: 获取资源数据
        logger.info(f"Job {job_id}: Fetching resource data for resource_id {resource_id}")
        resource = db.query(LearningResource).filter(
            LearningResource.id == resource_id
        ).first()
        
        if not resource or not resource.transcript:
            _update_job_status(
                job_id, 
                JobStatus.FAILED, 
                "Resource not found or has no transcript",
                error_message="Invalid resource or missing transcript data"
            )
            return
        
        _update_job_status(job_id, JobStatus.PROCESSING, "Resource data loaded", 20)
        
        # Step 2: 获取候选知识点列表
        logger.info(f"Job {job_id}: Fetching candidate knowledge points")
        # 使用专门的服务函数获取L3原子知识点
        l3_knowledge_points = get_l3_atomic_knowledge_points(db)
        
        if not l3_knowledge_points:
            _update_job_status(
                job_id,
                JobStatus.FAILED,
                "No active L3 knowledge points found",
                error_message="No L3 atomic knowledge points available for video segmentation"
            )
            return
        
        logger.info(f"Job {job_id}: Found {len(l3_knowledge_points)} L3 atomic knowledge points for segmentation")
        _update_job_status(job_id, JobStatus.PROCESSING, f"Loaded {len(l3_knowledge_points)} L3 knowledge points", 30)
        
        # Step 3: 调用 LLM 进行分析
        logger.info(f"Job {job_id}: Starting LLM analysis")
        segments_data = await _analyze_transcript_with_llm(
            job_id, resource.transcript, l3_knowledge_points
        )
        
        # 检查LLM分析结果
        if segments_data is None:
            _update_job_status(
                job_id,
                JobStatus.FAILED,
                "LLM analysis failed",
                error_message="Failed to analyze transcript with LLM"
            )
            return
        elif len(segments_data) == 0:
            # 这是正常情况：视频内容与知识点不匹配
            _update_job_status(
                job_id,
                JobStatus.COMPLETED,
                "Analysis completed: no matching knowledge points found in transcript",
                100,
                segments_created=0
            )
            logger.info(f"Job {job_id}: Analysis completed but no matching knowledge points found - this is normal for content that doesn't match L3 atomic knowledge points")
            return
        
        _update_job_status(job_id, JobStatus.PROCESSING, "LLM analysis completed", 70)
        
        # Step 4: 验证和存储结果
        logger.info(f"Job {job_id}: Storing analysis results")
        segments_created = await _store_video_segments(
            job_id, resource_id, segments_data, db
        )
        
        # 完成任务
        _update_job_status(
            job_id,
            JobStatus.COMPLETED,
            f"Analysis completed successfully. Created {segments_created} segments",
            100,
            segments_created=segments_created
        )
        
        logger.info(f"Job {job_id}: Analysis completed successfully with {segments_created} segments")
        
    except Exception as e:
        logger.error(f"Job {job_id}: Analysis failed with error: {e}")
        _update_job_status(
            job_id,
            JobStatus.FAILED,
            "Analysis failed due to internal error",
            error_message=str(e)
        )


async def process_file_upload_segment_analysis(
    job_id: str, 
    resource_id: int, 
    transcript_content: str,
    knowledge_context_id: int,
    db: Session
):
    """
    处理文件上传的视频分段分析任务
    这是新版本的处理函数，直接使用传入的transcript内容
    """
    try:
        # 更新状态为处理中
        _update_job_status(job_id, JobStatus.PROCESSING, "Starting analysis", 10)
        
        logger.info(f"Job {job_id}: Starting file upload analysis for resource_id {resource_id}")
        
        # Step 1: 获取资源数据（验证资源是否存在）
        resource = db.query(LearningResource).filter(
            LearningResource.id == resource_id
        ).first()
        
        if not resource:
            _update_job_status(
                job_id, 
                JobStatus.FAILED, 
                "Resource not found",
                error_message="Created resource record not found"
            )
            return
        
        _update_job_status(job_id, JobStatus.PROCESSING, "Resource data loaded", 20)
        
        # Step 2: 获取候选知识点列表（使用knowledge_context_id或所有活跃的知识点）
        logger.info(f"Job {job_id}: Fetching candidate knowledge points with context_id {knowledge_context_id}")
        # 使用专门的服务函数获取L3原子知识点
        l3_knowledge_points = get_l3_atomic_knowledge_points(db)
        
        if not l3_knowledge_points:
            _update_job_status(
                job_id,
                JobStatus.FAILED,
                "No active L3 knowledge points found",
                error_message="No L3 atomic knowledge points available for video segmentation"
            )
            return
        
        logger.info(f"Job {job_id}: Found {len(l3_knowledge_points)} L3 atomic knowledge points for segmentation")
        _update_job_status(job_id, JobStatus.PROCESSING, f"Loaded {len(l3_knowledge_points)} L3 knowledge points", 30)
        
        # Step 3: 调用 LLM 进行分析（使用传入的transcript内容）
        logger.info(f"Job {job_id}: Starting LLM analysis with {len(transcript_content)} characters")
        segments_data = await _analyze_transcript_with_llm(
            job_id, transcript_content, l3_knowledge_points
        )
        
        # 检查LLM分析结果
        if segments_data is None:
            _update_job_status(
                job_id,
                JobStatus.FAILED,
                "LLM analysis failed",
                error_message="Failed to analyze transcript content with LLM"
            )
            return
        elif len(segments_data) == 0:
            # 这是正常情况：视频内容与知识点不匹配
            _update_job_status(
                job_id,
                JobStatus.COMPLETED,
                "Analysis completed: no matching knowledge points found in transcript",
                progress=100,
                segments_created=0
            )
            logger.info(f"Job {job_id}: Analysis completed but no matching knowledge points found - this is normal for content that doesn't match L3 atomic knowledge points")
            return
        
        _update_job_status(job_id, JobStatus.PROCESSING, f"LLM analysis completed, storing {len(segments_data)} segments", 70)
        
        # Step 4: 存储分析结果
        logger.info(f"Job {job_id}: Storing {len(segments_data)} segments")
        segments_created = await _store_video_segments(job_id, resource_id, segments_data, db)
        
        if segments_created > 0:
            _update_job_status(
                job_id,
                JobStatus.COMPLETED,
                f"Analysis completed successfully. Created {segments_created} segments",
                progress=100,
                segments_created=segments_created
            )
            logger.info(f"Job {job_id}: Analysis completed successfully with {segments_created} segments")
        else:
            _update_job_status(
                job_id,
                JobStatus.COMPLETED,
                "Analysis completed but no segments were created due to validation issues",
                progress=100,
                segments_created=0
            )
            logger.warning(f"Job {job_id}: Analysis completed but no segments were stored")
    
    except Exception as e:
        logger.error(f"Job {job_id}: Analysis failed with error: {e}")
        _update_job_status(
            job_id,
            JobStatus.FAILED,
            "Analysis failed with unexpected error",
            error_message=str(e)
        )


async def process_video_link_analysis(
    job_id: str, 
    resource_id: int,
    video_url: str,
    knowledge_context_id: int,
    preferred_subtitle_language: Optional[str],
    db: Session
):
    """
    后台任务：从视频链接提取字幕并进行分段分析
    """
    try:
        # 更新状态为处理中
        _update_job_status(job_id, JobStatus.PROCESSING, "Starting transcript extraction", 10)
        
        logger.info(f"Job {job_id}: Starting transcript extraction from {video_url}")
        
        # Step 1: 使用yt-dlp提取字幕
        _update_job_status(job_id, JobStatus.PROCESSING, "Extracting transcript from video", 20)
        transcript_content = await _extract_transcript_with_ytdlp(video_url, preferred_subtitle_language)
        
        if not transcript_content:
            _update_job_status(
                job_id,
                JobStatus.FAILED,
                "Failed to extract transcript from video link",
                error_message="Could not extract transcript from video link. Please ensure the video has subtitles available."
            )
            return
        
        _update_job_status(job_id, JobStatus.PROCESSING, "Transcript extracted successfully", 30)
        
        # Step 2: 更新资源记录，添加transcript
        resource = db.query(LearningResource).filter(
            LearningResource.id == resource_id
        ).first()
        
        if not resource:
            _update_job_status(
                job_id,
                JobStatus.FAILED,
                "Resource not found",
                error_message="Resource record not found after transcript extraction"
            )
            return
        
        resource.transcript = transcript_content
        resource.description = f"Video analysis from link: {video_url} (analyzing transcript)"
        db.commit()
        db.refresh(resource)
        
        logger.info(f"Job {job_id}: Resource {resource_id} updated with transcript. Starting analysis.")
        
        # Step 3: 获取候选知识点列表
        _update_job_status(job_id, JobStatus.PROCESSING, "Fetching candidate knowledge points", 40)
        l3_knowledge_points = get_l3_atomic_knowledge_points(db)
        
        if not l3_knowledge_points:
            _update_job_status(
                job_id,
                JobStatus.FAILED,
                "No active L3 knowledge points found",
                error_message="No L3 atomic knowledge points available for video segmentation"
            )
            return
        
        _update_job_status(job_id, JobStatus.PROCESSING, f"Loaded {len(l3_knowledge_points)} L3 knowledge points", 50)
        
        # Step 4: 调用 LLM 进行分析
        _update_job_status(job_id, JobStatus.PROCESSING, "Starting LLM analysis with transcript", 60)
        segments_data = await _analyze_transcript_with_llm(
            job_id, transcript_content, l3_knowledge_points
        )
        
        # 检查LLM分析结果
        if segments_data is None:
            _update_job_status(
                job_id,
                JobStatus.FAILED,
                "LLM analysis failed",
                error_message="Failed to analyze transcript content with LLM"
            )
            return
        elif len(segments_data) == 0:
            # 这是正常情况：视频内容与知识点不匹配
            _update_job_status(
                job_id,
                JobStatus.COMPLETED,
                "Analysis completed: no matching knowledge points found in transcript",
                progress=100,
                segments_created=0
            )
            logger.info(f"Job {job_id}: Analysis completed but no matching knowledge points found - this is normal for content that doesn't match L3 atomic knowledge points")
            return
        
        _update_job_status(job_id, JobStatus.PROCESSING, f"LLM analysis completed, storing {len(segments_data)} segments", 70)
        
        # Step 5: 存储分析结果
        _update_job_status(job_id, JobStatus.PROCESSING, "Storing analysis results", 80)
        segments_created = await _store_video_segments(job_id, resource_id, segments_data, db)
        
        if segments_created > 0:
            _update_job_status(
                job_id,
                JobStatus.COMPLETED,
                f"Analysis completed successfully. Created {segments_created} segments",
                progress=100,
                segments_created=segments_created
            )
            logger.info(f"Job {job_id}: Analysis completed successfully with {segments_created} segments")
        else:
            _update_job_status(
                job_id,
                JobStatus.COMPLETED,
                "Analysis completed but no segments were created due to validation issues",
                progress=100,
                segments_created=0
            )
            logger.warning(f"Job {job_id}: Analysis completed but no segments were stored")
    
    except Exception as e:
        logger.error(f"Job {job_id}: Analysis failed with error: {e}")
        _update_job_status(
            job_id,
            JobStatus.FAILED,
            "Analysis failed with unexpected error",
            error_message=str(e)
        )


async def _extract_transcript_with_ytdlp(
    video_url: str,
    preferred_language: Optional[str] = "en"
) -> Optional[str]:
    """
    使用yt-dlp从视频URL提取字幕内容
    """
    try:
        # 创建临时目录来保存字幕文件
        with tempfile.TemporaryDirectory() as temp_dir:
            logger.info(f"Extracting subtitles from {video_url} using yt-dlp")
            logger.info(f"Temporary directory: {temp_dir}")
            
            # 配置yt-dlp选项 - 添加更安全的配置
            ydl_opts = {
                'skip_download': True,  # 不下载视频，只下载字幕
                'writesubtitles': True,  # 下载字幕
                'writeautomaticsub': True,  # 下载自动生成的字幕  
                'subtitleslangs': [preferred_language, 'en', 'zh-Hans', 'zh-TW', 'zh'],  # 语言优先级
                'outtmpl': os.path.join(temp_dir, '%(title)s.%(ext)s'),
                'quiet': True,
                'no_warnings': True,
                'ignoreerrors': True,  # 忽略错误继续处理
                'concurrent_fragment_downloads': 1,  # 限制并发下载
                'retries': 2,  # 减少重试次数
                'fragment_retries': 1,  # 减少片段重试
                'abort_on_unavailable_fragment': False,  # 片段不可用时不中止
            }
            
            # 提取字幕 - 使用锁防止并发问题
            with _ytdlp_lock:  # 防止yt-dlp并发访问导致内存问题
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    try:
                        logger.info(f"Getting video info for {video_url}")
                        info = ydl.extract_info(video_url, download=False)
                        video_title = info.get('title', 'video')
                        logger.info(f"Video title: {video_title}")
                        
                        # 检查可用字幕
                        subtitles_available = False
                        if info.get('subtitles'):
                            logger.info(f"Manual subtitles available: {list(info['subtitles'].keys())}")
                            subtitles_available = True
                        if info.get('automatic_captions'):
                            logger.info(f"Automatic captions available: {list(info['automatic_captions'].keys())}")
                            subtitles_available = True
                        
                        if not subtitles_available:
                            logger.warning(f"No subtitles or captions available for {video_url}")
                            return None
                        
                        # 下载字幕
                        logger.info(f"Downloading subtitles for {video_url}")
                        ydl.download([video_url])
                        
                        # 查找并读取字幕文件
                        logger.info("Searching for subtitle files")
                        subtitle_files = []
                        for file in os.listdir(temp_dir):
                            if file.endswith(('.vtt', '.srt')):
                                subtitle_files.append(file)
                                logger.info(f"Found subtitle file: {file}")
                        
                        if not subtitle_files:
                            logger.warning(f"No subtitle files found in {temp_dir}")
                            # 列出目录中的所有文件用于调试
                            all_files = os.listdir(temp_dir)
                            logger.info(f"All files in temp dir: {all_files}")
                            return None
                        
                        # 优先选择首选语言的字幕
                        preferred_file = None
                        for file in subtitle_files:
                            if preferred_language and preferred_language in file:
                                preferred_file = file
                                logger.info(f"Using preferred language file: {file}")
                                break
                        
                        # 如果没有找到首选语言，使用第一个可用的字幕文件
                        if not preferred_file:
                            preferred_file = subtitle_files[0]
                            logger.info(f"Using first available subtitle file: {preferred_file}")
                        
                        subtitle_path = os.path.join(temp_dir, preferred_file)
                        with open(subtitle_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                        
                        logger.info(f"Successfully extracted subtitles from {video_url}, content length: {len(content)}")
                        return content
                        
                    except Exception as e:
                        logger.error(f"yt-dlp extraction failed for {video_url}: {e}")
                        import traceback
                        logger.error(f"Full traceback: {traceback.format_exc()}")
                        return None
    
    except Exception as e:
        logger.error(f"Failed to extract transcript with yt-dlp: {e}")
        import traceback
        logger.error(f"Full traceback: {traceback.format_exc()}")
        return None


async def _analyze_transcript_with_llm(
    job_id: str,
    transcript: str,
    knowledge_points: List[Knowledge]
) -> Optional[List[VideoSegmentData]]:
    """使用LLM分析转录文本并生成视频片段。复用现有的逻辑。"""
    try:
        _update_job_status(job_id, JobStatus.PROCESSING, "Starting LLM analysis", 60)
        
        # 准备知识点列表用于LLM
        knowledge_points_text = "\n".join([
            f"- {kp.id}: {kp.title} ({kp.description})"
            for kp in knowledge_points
        ])
        
        # 创建提示
        system_prompt = """You are an expert in educational content analysis. Your task is to analyze video transcripts and identify segments that correspond to specific knowledge points.

Given a video transcript and a list of L3 atomic knowledge points, identify time segments where each knowledge point is discussed.

IMPORTANT REQUIREMENTS:
1. Aim for COMPREHENSIVE COVERAGE - try to identify segments that cover as much of the video as possible
2. Look for ALL mentions of knowledge points throughout the entire transcript, not just the main discussions
3. Include brief mentions, examples, and review sections that relate to knowledge points
4. Segments can be short (even 30-60 seconds) if they contain relevant content
5. If content doesn't match any knowledge points, that's okay - only segment what's relevant

For each segment you identify:
1. Determine the start and end time (in seconds from video beginning)
2. Match it to the most relevant knowledge point ID
3. Write a brief summary of what's discussed in that segment
4. Ensure segments don't overlap - if content relates to multiple knowledge points, choose the most relevant one

Return your analysis in JSON format:
{
  "segments": [
    {
      "start_time": 0.0,
      "end_time": 120.5,
      "knowledge_id": 123,
      "summary": "Introduction to machine learning concepts"
    }
  ]
}

If no segments match any knowledge points, return {"segments": []}."""

        # 合并系统提示和用户提示
        full_prompt = f"""{system_prompt}

Available L3 Knowledge Points:
{knowledge_points_text}

Video Transcript:
{transcript}

Please analyze this transcript and identify segments that match the knowledge points."""

        # 调用LLM
        agent = get_agent(agent_id=AgentType.TRANSCRIPT_ANALYZER)        
        response = await agent.arun(full_prompt, stream=False)
        
        if not response or not response.content:
            logger.error(f"Job {job_id}: Empty response from LLM")
            return None
        
        # 记录原始响应内容以便调试
        logger.info(f"Job {job_id}: Raw LLM response content (first 500 chars): {response.content[:500]}")
        
        # 解析响应 - 先处理可能的markdown格式
        try:
            # 去除可能的markdown代码块标记
            content = response.content.strip()
            if content.startswith('```json'):
                content = content[7:]  # 移除 ```json
            if content.startswith('```'):
                content = content[3:]   # 移除 ```
            if content.endswith('```'):
                content = content[:-3]  # 移除结尾的 ```
            content = content.strip()
            
            response_data = json.loads(content)
            segments_data = response_data.get("segments", [])
            
            # 验证并转换为VideoSegmentData对象
            validated_segments = []
            for segment in segments_data:
                try:
                    segment_data = VideoSegmentData(
                        start_time=float(segment["start_time"]),
                        end_time=float(segment["end_time"]),
                        knowledge_id=int(segment["knowledge_id"]),
                        summary=str(segment["summary"])
                    )
                    validated_segments.append(segment_data)
                except Exception as e:
                    logger.warning(f"Job {job_id}: Invalid segment data: {segment}, error: {e}")
                    continue
            
            logger.info(f"Job {job_id}: LLM analysis completed, found {len(validated_segments)} valid segments")
            return validated_segments
            
        except json.JSONDecodeError as e:
            logger.error(f"Job {job_id}: Failed to parse LLM response as JSON: {e}")
            logger.error(f"Job {job_id}: Full response content: {response.content}")
            logger.error(f"Job {job_id}: Response content type: {type(response.content)}")
            logger.error(f"Job {job_id}: Response content length: {len(response.content) if response.content else 0}")
            return None
        
    except Exception as e:
        logger.error(f"Job {job_id}: LLM analysis error: {e}")
        return None


async def _store_video_segments(
    job_id: str,
    resource_id: int,
    segments_data: List[VideoSegmentData],
    db: Session
) -> int:
    """
    将分析结果存储到数据库
    """
    try:
        segments_created = 0
        
        for i, segment_data in enumerate(segments_data):
            try:
                # 验证 knowledge_id 是否存在
                knowledge = db.query(Knowledge).filter(
                    Knowledge.id == segment_data.knowledge_id
                ).first()
                
                if not knowledge:
                    logger.warning(f"Job {job_id}: Knowledge ID {segment_data.knowledge_id} not found, skipping segment")
                    continue
                
                # 创建视频片段记录
                video_segment = VideoSegment(
                    resource_id=resource_id,
                    knowledge_id=segment_data.knowledge_id,
                    start_time=_seconds_to_time_string(segment_data.start_time),
                    end_time=_seconds_to_time_string(segment_data.end_time),
                    start_seconds=int(segment_data.start_time),
                    end_seconds=int(segment_data.end_time),
                    segment_title=knowledge.title,
                    segment_description=segment_data.summary,
                    importance_level=3  # 默认重要级别
                )
                
                db.add(video_segment)
                segments_created += 1
                
                # 更新进度
                progress = 70 + (20 * (i + 1) / len(segments_data))
                _update_job_status(
                    job_id, 
                    JobStatus.PROCESSING, 
                    f"Storing segment {i+1}/{len(segments_data)}", 
                    progress
                )
                
            except Exception as e:
                logger.error(f"Job {job_id}: Failed to store segment {i}: {e}")
                continue
        
        # 提交所有更改
        db.commit()
        
        logger.info(f"Job {job_id}: Successfully stored {segments_created} segments")
        return segments_created
        
    except Exception as e:
        logger.error(f"Job {job_id}: Failed to store segments: {e}")
        db.rollback()
        raise


def _seconds_to_time_string(seconds: float) -> str:
    """
    将秒数转换为时间字符串格式 HH:MM:SS.mmm
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = seconds % 60
    
    return f"{hours:02d}:{minutes:02d}:{secs:06.3f}"


def _update_job_status(
    job_id: str,
    status: JobStatus,
    message: str,
    progress: Optional[float] = None,
    current_step: Optional[str] = None,
    segments_created: Optional[int] = None,
    error_message: Optional[str] = None
):
    """
    更新任务状态
    """
    # 如果job不存在，创建新的job记录
    if job_id not in job_status_store:
        job_status_store[job_id] = {
            "job_id": job_id,
            "status": status,
            "message": message,
            "progress_percentage": progress or 0,
            "current_step": current_step,
            "segments_created": segments_created or 0,
            "error_message": error_message,
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        }
    else:
        # 更新已有的job记录
        job_data = job_status_store[job_id]
        job_data["status"] = status
        job_data["message"] = message
        job_data["updated_at"] = datetime.now()
        
        if progress is not None:
            job_data["progress_percentage"] = progress
        
        if current_step is not None:
            job_data["current_step"] = current_step
        
        if segments_created is not None:
            job_data["segments_created"] = segments_created
        
        if error_message is not None:
            job_data["error_message"] = error_message