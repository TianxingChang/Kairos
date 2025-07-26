from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from agents.video_qa_agent import get_video_qa_agent, VideoTranscriptRequest

router = APIRouter(prefix="/video-qa", tags=["Video Q&A"])


class VideoQuestionRequest(BaseModel):
    """视频问答请求模型"""
    video_id: str
    timestamp: float  # 时间点（秒）
    question: str
    user_id: Optional[str] = "anonymous"
    session_id: Optional[str] = None


class VideoQuestionResponse(BaseModel):
    """视频问答响应模型"""
    success: bool
    answer: str
    context_info: dict
    error: Optional[str] = None


@router.post("/ask", response_model=VideoQuestionResponse)
async def ask_video_question(request: VideoQuestionRequest):
    """
    基于视频时间点回答用户问题
    
    Args:
        request: 包含视频ID、时间点和问题的请求
    
    Returns:
        AI分析的答案和上下文信息
    """
    try:
        # 创建视频问答Agent
        agent = get_video_qa_agent(
            user_id=request.user_id,
            session_id=request.session_id,
            debug_mode=False
        )
        
        # 构建用户消息
        user_message = f"""
我正在观看视频 {request.video_id}，在时间点 {request.timestamp}秒处有个问题：

{request.question}

请帮我分析这个时间点附近的视频内容并回答我的问题。
"""
        
        # 获取Agent回答
        response = agent.run(user_message)
        
        return VideoQuestionResponse(
            success=True,
            answer=response.content if hasattr(response, 'content') else str(response),
            context_info={
                "video_id": request.video_id,
                "timestamp": request.timestamp,
                "user_id": request.user_id,
                "session_id": request.session_id
            }
        )
        
    except Exception as e:
        return VideoQuestionResponse(
            success=False,
            answer="",
            context_info={},
            error=f"处理问题失败: {str(e)}"
        )


@router.post("/direct", response_model=VideoQuestionResponse)
async def direct_video_question(request: VideoQuestionRequest):
    """
    直接调用视频问答功能（不通过Agent对话）
    
    Args:
        request: 包含视频ID、时间点和问题的请求
    
    Returns:
        基于转录文本的直接答案
    """
    try:
        from agents.video_qa_agent import answer_video_question, VideoTranscriptRequest
        
        # 直接调用问答函数
        transcript_request = VideoTranscriptRequest(
            video_id=request.video_id,
            timestamp=request.timestamp,
            question=request.question
        )
        
        result = answer_video_question(transcript_request)
        
        if not result.success:
            return VideoQuestionResponse(
                success=False,
                answer="",
                context_info={},
                error=result.error
            )
        
        return VideoQuestionResponse(
            success=True,
            answer=result.answer,
            context_info={
                "video_id": request.video_id,
                "timestamp": request.timestamp,
                "timestamp_range": result.timestamp_range,
                "context_length": len(result.context_transcript)
            }
        )
        
    except Exception as e:
        return VideoQuestionResponse(
            success=False,
            answer="",
            context_info={},
            error=f"处理问题失败: {str(e)}"
        )


@router.get("/context/{video_id}")
async def get_video_context(
    video_id: str,
    timestamp: float,
    context_only: bool = False
):
    """
    获取视频在指定时间点的转录文本上下文
    
    Args:
        video_id: YouTube视频ID
        timestamp: 时间点（秒）
        context_only: 是否只返回上下文文本
    
    Returns:
        时间点附近的转录文本上下文
    """
    try:
        from agents.video_qa_agent import get_video_transcript_context
        
        result = get_video_transcript_context(video_id, timestamp)
        
        if not result["success"]:
            raise HTTPException(status_code=404, detail=result["error"])
        
        if context_only:
            return {"context_transcript": result["context_transcript"]}
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取上下文失败: {str(e)}")