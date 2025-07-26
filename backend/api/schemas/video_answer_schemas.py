"""
Schemas for video-based question answering API (API 5).
Combines question diagnosis with video segment retrieval.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


class VideoAnswerRequest(BaseModel):
    """Request schema for video-based question answering."""
    
    user_question: str = Field(
        ...,
        description="用户的自然语言问题",
        example="为什么PPO算法里要用clip函数来限制策略更新的幅度？"
    )
    context_resource_id: Optional[int] = Field(
        None,
        description="可选的上下文资源ID，用于优先搜索特定视频资源的片段"
    )
    max_video_segments: int = Field(
        5,
        description="返回的最大视频片段数量",
        ge=1,
        le=20
    )
    enable_global_search: bool = Field(
        True,
        description="是否启用全局搜索（搜索所有视频资源）"
    )


class VideoTimeRange(BaseModel):
    """Video time range information."""
    
    start_seconds: int = Field(..., description="开始时间（秒）")
    end_seconds: int = Field(..., description="结束时间（秒）")
    start_time: str = Field(..., description="开始时间（格式化字符串，如 00:02:15）")
    end_time: str = Field(..., description="结束时间（格式化字符串）")
    duration: int = Field(..., description="片段时长（秒）")


class VideoResourceInfo(BaseModel):
    """Video resource basic information."""
    
    resource_id: int = Field(..., description="视频资源ID")
    title: str = Field(..., description="视频标题")
    url: str = Field(..., description="视频URL")
    duration_minutes: Optional[int] = Field(None, description="视频总时长（分钟）")


class VideoSegmentMatch(BaseModel):
    """Video segment that matches the question."""
    
    segment_id: int = Field(..., description="视频片段ID")
    video_resource: VideoResourceInfo = Field(..., description="视频资源信息")
    time_range: VideoTimeRange = Field(..., description="时间范围")
    knowledge_point: Dict[str, Any] = Field(..., description="相关知识点信息")
    relevance_score: float = Field(..., description="与问题的相关性评分", ge=0.0, le=1.0)
    segment_description: str = Field(..., description="片段描述")
    answer_explanation: str = Field(..., description="基于该片段的问题解答")


class QuestionBreakdown(BaseModel):
    """Question breakdown result."""
    
    sub_question: str = Field(..., description="拆解出的子问题")
    knowledge_focus: str = Field(..., description="该子问题关注的知识点")
    video_segments: List[VideoSegmentMatch] = Field(..., description="匹配的视频片段")
    answer_summary: str = Field(..., description="基于视频片段的综合答案")


class VideoAnswerResponse(BaseModel):
    """Response schema for video-based question answering."""
    
    success: bool = Field(..., description="请求是否成功")
    user_question: str = Field(..., description="用户原始问题")
    question_breakdowns: List[QuestionBreakdown] = Field(..., description="问题拆解和对应的视频答案")
    total_video_segments: int = Field(..., description="总共找到的视频片段数量")
    search_strategy: str = Field(..., description="使用的搜索策略")
    processing_time_seconds: float = Field(..., description="处理时间（秒）")
    created_at: datetime = Field(default_factory=datetime.now, description="响应创建时间")


class VideoAnswerJobResponse(BaseModel):
    """Async job response for video answer processing."""
    
    job_id: str = Field(..., description="任务ID")
    status_url: str = Field(..., description="状态查询URL")
    message: str = Field(default="Video answer analysis started", description="状态消息")


class VideoAnswerJobStatus(BaseModel):
    """Video answer job status."""
    
    job_id: str = Field(..., description="任务ID")
    status: str = Field(..., description="任务状态")
    progress_percentage: int = Field(..., description="进度百分比", ge=0, le=100)
    message: str = Field(..., description="状态消息")
    current_step: str = Field(..., description="当前处理步骤")
    result: Optional[VideoAnswerResponse] = Field(None, description="完成后的结果")
    error_message: Optional[str] = Field(None, description="错误信息")
    created_at: datetime = Field(..., description="任务创建时间")
    completed_at: Optional[datetime] = Field(None, description="任务完成时间")


class VideoSegmentSearchCriteria(BaseModel):
    """Criteria for searching video segments."""
    
    question_keywords: List[str] = Field(..., description="问题关键词")
    knowledge_domain: Optional[str] = Field(None, description="知识领域")
    difficulty_level: Optional[str] = Field(None, description="难度级别")
    resource_ids: Optional[List[int]] = Field(None, description="限制搜索的资源ID列表")