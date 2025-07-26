from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
import re

router = APIRouter(prefix="/frontend/video-qa", tags=["Frontend Video Q&A"])


class VideoContextRequest(BaseModel):
    """前端视频上下文请求模型"""
    video_id: str
    timestamp: float  # 时间点（秒）
    question: str
    user_id: Optional[str] = "frontend_user"
    session_id: Optional[str] = None
    context_before: int = 20  # 前20秒
    context_after: int = 5    # 后5秒


class VideoContextResponse(BaseModel):
    """前端视频上下文响应模型"""
    success: bool
    answer: str
    context_transcript: str
    timestamp_info: dict
    video_info: dict
    error: Optional[str] = None


class FullVideoRequest(BaseModel):
    """完整视频问答请求模型"""
    video_id: str
    question: str
    user_id: Optional[str] = "frontend_user"
    session_id: Optional[str] = None


class FullVideoResponse(BaseModel):
    """完整视频问答响应模型"""
    success: bool
    answer: str
    full_transcript: str
    video_info: dict
    transcript_stats: Optional[dict] = None
    error: Optional[str] = None


def parse_timestamp(timestamp_str: str) -> float:
    """
    解析时间戳字符串为秒数
    支持格式: "1:23", "01:23:45", "83", "83.5"
    """
    if isinstance(timestamp_str, (int, float)):
        return float(timestamp_str)
    
    timestamp_str = str(timestamp_str).strip()
    
    # 匹配 MM:SS 或 HH:MM:SS 格式
    time_pattern = re.match(r'^(\d{1,2}):(\d{2})(?::(\d{2}))?$', timestamp_str)
    if time_pattern:
        hours = 0
        if time_pattern.group(3):  # HH:MM:SS
            hours = int(time_pattern.group(1))
            minutes = int(time_pattern.group(2))
            seconds = int(time_pattern.group(3))
        else:  # MM:SS
            minutes = int(time_pattern.group(1))
            seconds = int(time_pattern.group(2))
        
        return hours * 3600 + minutes * 60 + seconds
    
    # 直接是数字格式
    try:
        return float(timestamp_str)
    except ValueError:
        raise ValueError(f"无法解析时间戳: {timestamp_str}")


@router.post("/ask", response_model=VideoContextResponse)
async def frontend_video_ask(request: VideoContextRequest):
    """
    前端视频时间点问答接口
    
    专为前端设计，提供完整的上下文信息和用户友好的响应
    """
    try:
        from agents.video_qa_agent import get_video_transcript_context, answer_video_question, VideoTranscriptRequest
        from db.session import SessionLocal
        from db.youtube_service import get_video_info
        
        # 获取视频信息
        db = SessionLocal()
        try:
            video_info = get_video_info(db, request.video_id)
            video_data = {
                "video_id": request.video_id,
                "title": video_info.title if video_info else "未知标题",
                "duration": video_info.duration if video_info else None,
                "channel": video_info.channel_name if video_info else "未知频道"
            }
        finally:
            db.close()
        
        # 获取上下文转录
        context_result = get_video_transcript_context(request.video_id, request.timestamp)
        
        if not context_result["success"]:
            return VideoContextResponse(
                success=False,
                answer="",
                context_transcript="",
                timestamp_info={},
                video_info=video_data,
                error=context_result["error"]
            )
        
        # 使用问答功能获取AI回答
        qa_request = VideoTranscriptRequest(
            video_id=request.video_id,
            timestamp=request.timestamp,
            question=request.question
        )
        
        qa_result = answer_video_question(qa_request)
        
        if not qa_result.success:
            return VideoContextResponse(
                success=False,
                answer="",
                context_transcript=context_result["context_transcript"],
                timestamp_info=context_result["timestamp_range"],
                video_info=video_data,
                error=qa_result.error
            )
        
        # 格式化时间戳信息
        timestamp_info = {
            "target_time": request.timestamp,
            "target_formatted": f"{int(request.timestamp//60):02d}:{int(request.timestamp%60):02d}",
            "context_start": context_result["timestamp_range"]["start"],
            "context_end": context_result["timestamp_range"]["end"],
            "context_duration": context_result["timestamp_range"]["end"] - context_result["timestamp_range"]["start"]
        }
        
        return VideoContextResponse(
            success=True,
            answer=qa_result.answer,
            context_transcript=context_result["context_transcript"],
            timestamp_info=timestamp_info,
            video_info=video_data
        )
        
    except Exception as e:
        return VideoContextResponse(
            success=False,
            answer="",
            context_transcript="",
            timestamp_info={},
            video_info={"video_id": request.video_id},
            error=f"处理请求失败: {str(e)}"
        )


@router.post("/ask-full", response_model=FullVideoResponse)
async def frontend_full_video_ask(request: FullVideoRequest):
    """
    前端完整视频问答接口
    
    基于整个视频的转录文本回答用户问题，适合询问视频的整体主题、结构、关键观点等
    """
    try:
        from agents.full_video_qa_agent import get_full_video_transcript, answer_full_video_question, FullVideoTranscriptRequest, get_full_video_qa_agent
        from db.session import SessionLocal
        from db.youtube_service import get_video_info
        
        # 获取视频信息
        db = SessionLocal()
        try:
            video_info = get_video_info(db, request.video_id)
            print(f"视频信息查询结果: {video_info}")
            # 不再要求必须有视频信息，如果没有就继续尝试获取转录
        finally:
            db.close()
        
        # 获取完整转录文本
        print(f"正在获取视频 {request.video_id} 的完整转录文本...")
        transcript_result = get_full_video_transcript(request.video_id)
        print(f"转录结果: success={transcript_result['success']}")
        
        if not transcript_result["success"]:
            print(f"转录获取失败: {transcript_result.get('error', '未知错误')}")
            return FullVideoResponse(
                success=False,
                answer="",
                full_transcript="",
                video_info=transcript_result.get("video_info", {"video_id": request.video_id}),
                error=transcript_result["error"]
            )
        
        # 使用完整视频问答功能获取AI回答
        qa_request = FullVideoTranscriptRequest(
            video_id=request.video_id,
            question=request.question
        )
        
        qa_result = answer_full_video_question(qa_request)
        
        if not qa_result.success:
            return FullVideoResponse(
                success=False,
                answer="",
                full_transcript=transcript_result["full_transcript"],
                video_info=transcript_result["video_info"],
                transcript_stats=transcript_result.get("transcript_stats"),
                error=qa_result.error
            )
        
        return FullVideoResponse(
            success=True,
            answer=qa_result.answer,
            full_transcript=transcript_result["full_transcript"],
            video_info=transcript_result["video_info"],
            transcript_stats=transcript_result.get("transcript_stats")
        )
        
    except Exception as e:
        return FullVideoResponse(
            success=False,
            answer="",
            full_transcript="",
            video_info={"video_id": request.video_id},
            error=f"处理请求失败: {str(e)}"
        )


@router.post("/ask-full-agent", response_model=FullVideoResponse)
async def frontend_full_video_ask_with_agent(request: FullVideoRequest):
    """
    前端完整视频问答接口 (使用Agent)
    
    使用Full Video QA Agent进行对话式问答，支持上下文记忆和更智能的交互
    """
    try:
        from agents.full_video_qa_agent import get_full_video_qa_agent, get_full_video_transcript
        from db.session import SessionLocal
        from db.youtube_service import get_video_info
        
        # 获取视频信息
        db = SessionLocal()
        try:
            video_info = get_video_info(db, request.video_id)
            print(f"视频信息查询结果: {video_info}")
            # 不再要求必须有视频信息，如果没有就继续尝试获取转录
        finally:
            db.close()
        
        # 获取完整转录文本
        print(f"正在获取视频 {request.video_id} 的完整转录文本...")
        transcript_result = get_full_video_transcript(request.video_id)
        print(f"转录结果: success={transcript_result['success']}")
        
        if not transcript_result["success"]:
            print(f"转录获取失败: {transcript_result.get('error', '未知错误')}")
            return FullVideoResponse(
                success=False,
                answer="",
                full_transcript="",
                video_info=transcript_result.get("video_info", {"video_id": request.video_id}),
                error=transcript_result["error"]
            )
        
        # 创建完整视频问答Agent
        agent = get_full_video_qa_agent(
            user_id=request.user_id,
            session_id=request.session_id,
            debug_mode=False
        )
        
        # 构建包含完整转录文本的用户消息
        full_transcript = transcript_result["full_transcript"]
        video_info_data = transcript_result["video_info"]
        
        user_message = f"""
我正在分析视频 {request.video_id}，想要询问关于整个视频的问题。

**视频信息:**
- 标题: {video_info_data.get('title', '未知')}
- 频道: {video_info_data.get('channel', '未知')}
- 时长: {video_info_data.get('duration', 0)} 秒
- 转录片段数: {video_info_data.get('total_segments', 0)}

**完整视频转录文本:**
{full_transcript}

**我的问题:**
{request.question}

请基于上述完整的视频转录文本，全面回答我的问题。
"""
        
        # 获取Agent回答
        response = agent.run(user_message)
        
        # 提取Agent回答内容
        if hasattr(response, 'content'):
            answer = response.content
        elif hasattr(response, 'get_content_as_string'):
            answer = response.get_content_as_string()
        else:
            answer = str(response)
        
        return FullVideoResponse(
            success=True,
            answer=answer,
            full_transcript=full_transcript,
            video_info=video_info_data,
            transcript_stats=transcript_result.get("transcript_stats")
        )
        
    except Exception as e:
        return FullVideoResponse(
            success=False,
            answer="",
            full_transcript="",
            video_info={"video_id": request.video_id},
            error=f"Agent处理失败: {str(e)}"
        )


@router.get("/context/{video_id}")
async def get_frontend_context(
    video_id: str,
    timestamp: str = Query(..., description="时间戳 (支持 MM:SS 或秒数)"),
    before: int = Query(20, description="前向上下文秒数"),
    after: int = Query(5, description="后向上下文秒数")
):
    """
    获取视频时间点的上下文转录（前端友好格式）
    
    Args:
        video_id: YouTube视频ID
        timestamp: 时间戳，支持 "1:23" 或 "83" 格式
        before: 前向上下文秒数
        after: 后向上下文秒数
    """
    try:
        # 解析时间戳
        timestamp_seconds = parse_timestamp(timestamp)
        
        from agents.video_qa_agent import get_video_transcript_context
        
        # 自定义时间范围的上下文获取
        def get_custom_context(video_id: str, timestamp: float, before: int = 20, after: int = 5):
            from db.session import SessionLocal
            from db.youtube_service import get_video_transcript_from_file
            
            db = SessionLocal()
            try:
                transcript_data = get_video_transcript_from_file(db, video_id)
                if not transcript_data:
                    return {"success": False, "error": f"未找到视频 {video_id} 的转录文本"}
                
                start_time = max(0, timestamp - before)
                end_time = timestamp + after
                
                context_segments = []
                for segment in transcript_data:
                    segment_start = segment.get('start', 0)
                    segment_end = segment_start + segment.get('duration', 0)
                    
                    if segment_start <= end_time and segment_end >= start_time:
                        context_segments.append({
                            'start': segment_start,
                            'end': segment_end,
                            'text': segment.get('text', ''),
                            'duration': segment.get('duration', 0)
                        })
                
                if not context_segments:
                    return {
                        "success": False,
                        "error": f"在时间点 {timestamp}s 附近未找到转录文本"
                    }
                
                context_segments.sort(key=lambda x: x['start'])
                context_text_parts = []
                
                for segment in context_segments:
                    start_min = int(segment['start'] // 60)
                    start_sec = int(segment['start'] % 60)
                    context_text_parts.append(f"[{start_min:02d}:{start_sec:02d}] {segment['text']}")
                
                return {
                    "success": True,
                    "context_transcript": "\\n".join(context_text_parts),
                    "timestamp_range": {"start": start_time, "end": end_time, "target": timestamp},
                    "segments": context_segments
                }
                
            finally:
                db.close()
        
        result = get_custom_context(video_id, timestamp_seconds, before, after)
        
        if not result["success"]:
            raise HTTPException(status_code=404, detail=result["error"])
        
        # 添加前端友好的格式化信息
        result["timestamp_info"] = {
            "target_time": timestamp_seconds,
            "target_formatted": f"{int(timestamp_seconds//60):02d}:{int(timestamp_seconds%60):02d}",
            "context_start": result["timestamp_range"]["start"],
            "context_end": result["timestamp_range"]["end"],
            "before_seconds": before,
            "after_seconds": after
        }
        
        return result
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取上下文失败: {str(e)}")


@router.get("/parse-timestamp")
async def parse_timestamp_endpoint(timestamp: str = Query(..., description="时间戳字符串")):
    """
    解析时间戳字符串工具接口
    
    帮助前端验证和转换时间戳格式
    """
    try:
        seconds = parse_timestamp(timestamp)
        
        return {
            "success": True,
            "original": timestamp,
            "seconds": seconds,
            "formatted": f"{int(seconds//60):02d}:{int(seconds%60):02d}",
            "hours_minutes_seconds": f"{int(seconds//3600):02d}:{int((seconds%3600)//60):02d}:{int(seconds%60):02d}"
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/video-status/{video_id}")
async def get_video_status(video_id: str):
    """
    检查视频的处理状态和可用性
    
    帮助前端判断视频是否已处理并可用于问答
    """
    try:
        from db.session import SessionLocal
        from db.youtube_service import get_video_info, get_video_transcript_from_file
        
        db = SessionLocal()
        try:
            # 检查视频信息
            video_info = get_video_info(db, video_id)
            
            # 检查转录文本
            transcript = get_video_transcript_from_file(db, video_id)
            
            has_transcript = transcript is not None and len(transcript) > 0
            
            status = {
                "video_id": video_id,
                "has_video_info": video_info is not None,
                "has_transcript": has_transcript,
                "ready_for_qa": has_transcript,
                "video_info": {
                    "title": video_info.title if video_info else None,
                    "duration": video_info.duration if video_info else None,
                    "channel": video_info.channel_name if video_info else None,
                    "created_at": video_info.created_at.isoformat() if video_info and video_info.created_at else None
                } if video_info else None,
                "transcript_info": {
                    "segment_count": len(transcript) if transcript else 0,
                    "language": video_info.transcript_language if video_info else None,
                    "file_size": video_info.transcript_file_size if video_info else None
                } if has_transcript else None
            }
            
            return status
            
        finally:
            db.close()
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"检查视频状态失败: {str(e)}")