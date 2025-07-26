from typing import Optional
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
import re

router = APIRouter(prefix="/frontend/youtube", tags=["Frontend YouTube"])


class YouTubeUploadRequest(BaseModel):
    """前端YouTube上传请求"""
    url: str
    user_id: Optional[str] = "frontend_user"


class YouTubeUploadResponse(BaseModel):
    """前端YouTube上传响应"""
    success: bool
    video_id: str
    message: str
    status: str  # "processing", "ready", "error"
    video_info: Optional[dict] = None
    error: Optional[str] = None


def extract_video_id_from_url(url: str) -> Optional[str]:
    """
    从YouTube URL提取视频ID
    支持多种YouTube URL格式
    """
    patterns = [
        r'(?:https?://)?(?:www\.)?youtube\.com/watch\?v=([a-zA-Z0-9_-]+)',
        r'(?:https?://)?(?:www\.)?youtu\.be/([a-zA-Z0-9_-]+)',
        r'(?:https?://)?(?:www\.)?youtube\.com/embed/([a-zA-Z0-9_-]+)',
        r'(?:https?://)?(?:www\.)?youtube\.com/v/([a-zA-Z0-9_-]+)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    
    # 如果直接是视频ID
    if re.match(r'^[a-zA-Z0-9_-]{11}$', url):
        return url
    
    return None


@router.post("/upload", response_model=YouTubeUploadResponse)
async def upload_youtube_video(
    request: YouTubeUploadRequest,
    background_tasks: BackgroundTasks
):
    """
    上传并处理YouTube视频
    
    自动提取视频ID，检查状态，如果需要则启动后台处理
    """
    try:
        # 提取视频ID
        video_id = extract_video_id_from_url(request.url)
        
        if not video_id:
            return YouTubeUploadResponse(
                success=False,
                video_id="",
                message="无效的YouTube URL",
                status="error",
                error="无法从URL中提取视频ID"
            )
        
        # 检查视频状态
        from db.session import SessionLocal
        from db.youtube_service import get_video_info, get_video_transcript_from_file
        
        db = SessionLocal()
        try:
            video_info = get_video_info(db, video_id)
            transcript = get_video_transcript_from_file(db, video_id)
            
            # 构建视频信息
            video_data = None
            if video_info:
                video_data = {
                    "video_id": video_id,
                    "title": video_info.title,
                    "duration": video_info.duration,
                    "channel": video_info.channel_name,
                    "created_at": video_info.created_at.isoformat() if video_info.created_at else None
                }
            
            # 如果已有转录文本，直接返回
            if transcript and len(transcript) > 0:
                return YouTubeUploadResponse(
                    success=True,
                    video_id=video_id,
                    message="视频转录已准备就绪",
                    status="ready",
                    video_info=video_data
                )
            
            # 如果没有转录文本，启动后台处理
            from api.routes.youtube import background_process_youtube
            background_tasks.add_task(background_process_youtube, request.url, SessionLocal)
            
            return YouTubeUploadResponse(
                success=True,
                video_id=video_id,
                message="视频已提交后台处理，请稍后查看状态",
                status="processing",
                video_info=video_data
            )
            
        finally:
            db.close()
            
    except Exception as e:
        return YouTubeUploadResponse(
            success=False,
            video_id="",
            message="处理失败",
            status="error",
            error=str(e)
        )


@router.get("/status/{video_id}")
async def get_youtube_status(video_id: str):
    """
    获取YouTube视频的详细处理状态
    
    提供比通用状态检查更详细的YouTube特定信息
    """
    try:
        from db.session import SessionLocal
        from db.youtube_service import get_video_info, get_video_transcript_from_file
        
        db = SessionLocal()
        try:
            video_info = get_video_info(db, video_id)
            transcript = get_video_transcript_from_file(db, video_id)
            
            has_transcript = transcript is not None and len(transcript) > 0
            
            # 判断状态
            if has_transcript:
                status = "ready"
                message = "视频转录已准备就绪，可以进行问答"
            elif video_info:
                status = "processing"
                message = "视频信息已获取，转录文本处理中"
            else:
                status = "not_found"
                message = "视频未找到，可能需要重新上传处理"
            
            return {
                "success": True,
                "video_id": video_id,
                "status": status,
                "message": message,
                "ready_for_qa": has_transcript,
                "video_info": {
                    "title": video_info.title if video_info else None,
                    "duration": video_info.duration if video_info else None,
                    "channel": video_info.channel_name if video_info else None,
                    "upload_date": video_info.upload_date.isoformat() if video_info and video_info.upload_date else None,
                    "created_at": video_info.created_at.isoformat() if video_info and video_info.created_at else None
                } if video_info else None,
                "transcript_info": {
                    "segment_count": len(transcript) if transcript else 0,
                    "language": video_info.transcript_language if video_info else None,
                    "file_path": video_info.transcript_file_path if video_info else None,
                    "file_size": video_info.transcript_file_size if video_info else None,
                    "created_at": video_info.transcript_created_at.isoformat() if video_info and video_info.transcript_created_at else None
                } if has_transcript else None
            }
            
        finally:
            db.close()
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"检查状态失败: {str(e)}")


@router.get("/search")
async def search_youtube_videos(
    query: Optional[str] = None,
    limit: int = 10
):
    """
    搜索已处理的YouTube视频
    
    Args:
        query: 搜索关键词（标题、频道名）
        limit: 返回结果数量限制
    """
    try:
        from db.session import SessionLocal
        from db.models import YouTubeVideo
        from sqlalchemy import or_
        
        db = SessionLocal()
        try:
            query_obj = db.query(YouTubeVideo)
            
            # 添加搜索条件
            if query:
                search_pattern = f"%{query}%"
                query_obj = query_obj.filter(
                    or_(
                        YouTubeVideo.title.ilike(search_pattern),
                        YouTubeVideo.channel_name.ilike(search_pattern)
                    )
                )
            
            # 只返回有转录文本的视频
            query_obj = query_obj.filter(YouTubeVideo.transcript_file_path.isnot(None))
            
            # 按创建时间排序并限制数量
            videos = query_obj.order_by(YouTubeVideo.created_at.desc()).limit(limit).all()
            
            results = []
            for video in videos:
                results.append({
                    "video_id": video.video_id,
                    "title": video.title,
                    "channel": video.channel_name,
                    "duration": video.duration,
                    "transcript_segments": video.transcript_segment_count,
                    "created_at": video.created_at.isoformat() if video.created_at else None,
                    "youtube_url": f"https://www.youtube.com/watch?v={video.video_id}"
                })
            
            return {
                "success": True,
                "query": query,
                "total": len(results),
                "videos": results
            }
            
        finally:
            db.close()
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"搜索失败: {str(e)}")


@router.delete("/delete/{video_id}")
async def delete_youtube_video(video_id: str):
    """
    删除YouTube视频及其转录文件
    
    完全清理视频相关的所有数据
    """
    try:
        from db.session import SessionLocal
        from db.models import YouTubeVideo
        from core.file_storage import transcript_storage
        
        db = SessionLocal()
        try:
            # 查找视频记录
            video = db.query(YouTubeVideo).filter(YouTubeVideo.video_id == video_id).first()
            
            if not video:
                raise HTTPException(status_code=404, detail="视频未找到")
            
            # 删除转录文件
            file_deleted = False
            try:
                file_deleted = transcript_storage.delete_transcript(video_id)
            except Exception as e:
                print(f"删除转录文件失败: {e}")
            
            # 删除数据库记录
            db.delete(video)
            db.commit()
            
            return {
                "success": True,
                "video_id": video_id,
                "message": "视频及转录文件已删除",
                "file_deleted": file_deleted
            }
            
        finally:
            db.close()
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除失败: {str(e)}")