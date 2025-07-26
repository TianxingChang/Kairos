from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel
import asyncio

from db.session import get_db
from db.models import YouTubeVideo
from core.youtube_handler import (
    process_youtube_url,
    get_transcript_with_timestamps,
    search_in_transcript,
    get_transcript_by_time
)

router = APIRouter(prefix="/youtube", tags=["YouTube"])


class YouTubeURLRequest(BaseModel):
    """YouTube URL请求模型"""
    url: str
    merge_segments: bool = True
    auto_process: bool = True  # 是否自动处理转录文本


class QuickProcessRequest(BaseModel):
    """快速处理请求模型（用于前端上传）"""
    url: str


class TranscriptResponse(BaseModel):
    """转录文本响应模型"""
    id: int
    start_time: float
    duration: float
    text: str
    language: str
    end_time: float


class ProcessResponse(BaseModel):
    """处理结果响应模型"""
    success: bool
    video_id: Optional[str]
    message: str
    transcript_count: int
    video_info: Optional[dict]


async def background_process_youtube(url: str, db_session_factory):
    """后台处理YouTube视频的函数"""
    try:
        # 创建新的数据库会话
        from db.session import SessionLocal
        db = SessionLocal()
        try:
            result = await process_youtube_url(
                db=db,
                youtube_url=url,
                merge_segments=True
            )
            print(f"✅ 后台处理完成: {url} - {result['message']}")
        finally:
            db.close()
    except Exception as e:
        print(f"❌ 后台处理失败: {url} - {e}")


@router.post("/quick-process")
async def quick_process_youtube(
    request: QuickProcessRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    快速处理YouTube视频（用于前端上传）
    立即返回响应，后台异步处理转录文本
    
    Args:
        request: 包含YouTube URL的请求
        background_tasks: 后台任务
        db: 数据库会话
    
    Returns:
        即时响应，转录文本将在后台处理
    """
    from core.youtube_processor import extract_video_id, validate_youtube_url
    
    # 验证URL
    if not validate_youtube_url(request.url):
        raise HTTPException(status_code=400, detail="无效的YouTube URL")
    
    video_id = extract_video_id(request.url)
    if not video_id:
        raise HTTPException(status_code=400, detail="无法提取视频ID")
    
    # 检查是否已存在转录文本
    from db.youtube_service import get_video_transcript_from_file
    existing_transcript = get_video_transcript_from_file(db, video_id)
    
    if existing_transcript:
        return {
            "success": True,
            "video_id": video_id,
            "message": "转录文本已存在",
            "status": "ready",
            "transcript_count": len(existing_transcript)
        }
    
    # 添加后台任务处理转录文本
    from db.session import SessionLocal
    background_tasks.add_task(background_process_youtube, request.url, SessionLocal)
    
    return {
        "success": True,
        "video_id": video_id,
        "message": "正在后台处理转录文本",
        "status": "processing",
        "transcript_count": 0
    }


@router.post("/process", response_model=ProcessResponse)
async def process_youtube_video(
    request: YouTubeURLRequest,
    db: Session = Depends(get_db)
):
    """
    处理YouTube视频URL，下载并保存转录文本
    
    Args:
        request: 包含YouTube URL的请求
        db: 数据库会话
    
    Returns:
        处理结果
    """
    result = await process_youtube_url(
        db=db,
        youtube_url=request.url,
        merge_segments=request.merge_segments
    )
    return ProcessResponse(**result)


@router.get("/transcript/{video_id}", response_model=List[TranscriptResponse])
async def get_video_transcript(
    video_id: str,
    db: Session = Depends(get_db)
):
    """
    获取视频的完整转录文本
    
    Args:
        video_id: YouTube视频ID
        db: 数据库会话
    
    Returns:
        转录文本列表
    """
    transcript = await get_transcript_with_timestamps(db, video_id)
    if transcript is None:
        raise HTTPException(status_code=404, detail="未找到转录文本")
    
    return [TranscriptResponse(**item) for item in transcript]


@router.get("/transcript/{video_id}/search", response_model=List[TranscriptResponse])
async def search_transcript(
    video_id: str,
    q: str = Query(..., description="搜索关键词"),
    db: Session = Depends(get_db)
):
    """
    在转录文本中搜索关键词
    
    Args:
        video_id: YouTube视频ID
        q: 搜索关键词
        db: 数据库会话
    
    Returns:
        匹配的转录片段列表
    """
    results = await search_in_transcript(db, video_id, q)
    return [TranscriptResponse(**item) for item in results]


@router.get("/transcript/{video_id}/time-range", response_model=List[TranscriptResponse])
async def get_transcript_by_time_range(
    video_id: str,
    start_time: float = Query(..., description="开始时间（秒）"),
    end_time: float = Query(..., description="结束时间（秒）"),
    db: Session = Depends(get_db)
):
    """
    获取指定时间范围内的转录文本
    
    Args:
        video_id: YouTube视频ID
        start_time: 开始时间（秒）
        end_time: 结束时间（秒）
        db: 数据库会话
    
    Returns:
        指定时间范围内的转录片段列表
    """
    if start_time >= end_time:
        raise HTTPException(status_code=400, detail="开始时间必须小于结束时间")
    
    results = await get_transcript_by_time(db, video_id, start_time, end_time)
    return [TranscriptResponse(**item) for item in results]


@router.get("/info/{video_id}")
async def get_video_info(
    video_id: str,
    db: Session = Depends(get_db)
):
    """
    获取视频基本信息
    
    Args:
        video_id: YouTube视频ID
        db: 数据库会话
    
    Returns:
        视频信息
    """
    from db.youtube_service import get_video_info
    
    video_info = get_video_info(db, video_id)
    if not video_info:
        raise HTTPException(status_code=404, detail="未找到视频信息")
    
    return {
        "video_id": video_info.video_id,
        "title": video_info.title,
        "duration": video_info.duration,
        "upload_date": video_info.upload_date,
        "channel_name": video_info.channel_name,
        "description": video_info.description,
        "created_at": video_info.created_at,
        "updated_at": video_info.updated_at
    }


@router.get("/stats")
async def get_storage_stats(db: Session = Depends(get_db)):
    """
    获取转录文件存储统计信息
    
    Args:
        db: 数据库会话
    
    Returns:
        存储统计信息
    """
    from db.youtube_service import get_transcript_file_stats
    
    stats = get_transcript_file_stats(db)
    return stats


@router.delete("/transcript/{video_id}")
async def delete_video_transcript(
    video_id: str,
    db: Session = Depends(get_db)
):
    """
    删除视频转录文件
    
    Args:
        video_id: YouTube视频ID
        db: 数据库会话
    
    Returns:
        删除结果
    """
    try:
        from core.file_storage import transcript_storage
        
        # 删除文件
        file_deleted = transcript_storage.delete_transcript(video_id)
        
        # 更新数据库记录
        video = db.query(YouTubeVideo).filter(YouTubeVideo.video_id == video_id).first()
        if video:
            video.transcript_file_path = None
            video.transcript_language = None
            video.transcript_segment_count = 0
            video.transcript_file_size = 0
            video.transcript_created_at = None
            video.updated_at = datetime.utcnow()
            db.commit()
        
        return {
            "success": True,
            "video_id": video_id,
            "message": "转录文件删除成功" if file_deleted else "文件不存在，数据库记录已清理"
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"删除失败: {str(e)}")


@router.post("/cleanup")
async def cleanup_orphaned_files(db: Session = Depends(get_db)):
    """
    清理孤立的转录文件（数据库中没有对应记录的文件）
    
    Args:
        db: 数据库会话
    
    Returns:
        清理结果
    """
    try:
        from core.file_storage import transcript_storage
        
        # 获取数据库中所有视频ID
        existing_videos = db.query(YouTubeVideo.video_id).all()
        existing_video_ids = [video.video_id for video in existing_videos]
        
        # 清理孤立文件
        deleted_count = transcript_storage.cleanup_orphaned_files(existing_video_ids)
        
        return {
            "success": True,
            "deleted_files": deleted_count,
            "message": f"清理了 {deleted_count} 个孤立文件"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"清理失败: {str(e)}")


@router.get("/status/{video_id}")
async def get_processing_status(
    video_id: str,
    db: Session = Depends(get_db)
):
    """
    获取视频处理状态
    
    Args:
        video_id: YouTube视频ID
        db: 数据库会话
    
    Returns:
        处理状态信息
    """
    from db.youtube_service import get_video_transcript_from_file, get_video_info
    
    # 检查转录文本是否存在
    transcript = get_video_transcript_from_file(db, video_id)
    video_info = get_video_info(db, video_id)
    
    if transcript:
        return {
            "video_id": video_id,
            "status": "ready",
            "message": "转录文本已准备就绪",
            "transcript_count": len(transcript),
            "has_video_info": video_info is not None
        }
    elif video_info:
        return {
            "video_id": video_id,
            "status": "processing",
            "message": "正在处理转录文本",
            "transcript_count": 0,
            "has_video_info": True
        }
    else:
        return {
            "video_id": video_id,
            "status": "not_found",
            "message": "未找到该视频",
            "transcript_count": 0,
            "has_video_info": False
        }