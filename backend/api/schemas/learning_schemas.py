"""Pydantic schemas for learning resources and knowledge API."""

from datetime import datetime
from typing import List, Optional, Literal
from pydantic import BaseModel, Field


class TagBase(BaseModel):
    """标签基础模型"""
    name: str = Field(description="标签名称")
    description: Optional[str] = Field(None, description="标签描述")


class TagResponse(TagBase):
    """标签响应模型"""
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


class KnowledgeBase(BaseModel):
    """知识点基础模型"""
    title: str = Field(description="知识点标题")
    description: Optional[str] = Field(None, description="知识点详细描述")
    domain: str = Field(description="知识领域")
    difficulty_level: str = Field(
        default="beginner", description="难度等级"
    )
    estimated_hours: int = Field(default=1, description="预计学习时间（小时）")
    search_keywords: Optional[str] = Field(None, description="搜索关键词，用于匹配LLM输出")


class KnowledgeCreate(KnowledgeBase):
    """创建知识点的请求模型"""
    pass


class KnowledgeResponse(KnowledgeBase):
    """知识点响应模型"""
    id: int
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class LearningResourceBase(BaseModel):
    """学习资源基础模型"""
    title: str = Field(description="资源标题")
    resource_type: Literal["video", "document", "url", "local_file"] = Field(
        description="资源类型"
    )
    resource_url: str = Field(description="资源URL或本地路径")
    description: Optional[str] = Field(None, description="资源描述或内容摘要")
    transcript: Optional[str] = Field(None, description="视频的转录文本或文档的文本内容")
    duration_minutes: Optional[int] = Field(None, description="资源时长（分钟）")
    language: str = Field(default="zh-CN", description="语言")
    quality_score: int = Field(default=0, description="质量评分 0-10")


class LearningResourceCreate(LearningResourceBase):
    """创建学习资源的请求模型"""
    pass


class LearningResourceResponse(LearningResourceBase):
    """学习资源响应模型"""
    id: int
    is_available: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class VideoPrerequisiteRequest(BaseModel):
    """视频前置知识查询请求"""
    video_url: str = Field(description="视频URL（必填）")
    transcript: Optional[str] = Field(None, description="视频转录文本（可选，如果不提供会自动获取）")
    video_title: Optional[str] = Field(None, description="视频标题（可选，如果不提供会自动获取）")
    model_type: Literal["gpt-4.1", "o4-mini", "gemini-2.5-pro", "kimi-k2-0711-preview", "o3-mini"] = Field(
        default="o3-mini", description="使用的分析模型"
    )


class PrerequisiteKnowledge(BaseModel):
    """前置知识项"""
    knowledge_id: Optional[int] = Field(None, description="知识点ID")
    title: str = Field(description="知识点标题")
    description: str = Field(description="知识点描述")
    domain: str = Field(description="知识领域")
    estimated_hours: int = Field(description="预计学习时间")
    learning_resources: List[LearningResourceResponse] = Field(
        default_factory=list, description="相关学习资源"
    )


class VideoPrerequisiteResponse(BaseModel):
    """视频前置知识查询响应"""
    success: bool = Field(description="查询是否成功")
    message: str = Field(description="响应消息")
    video_info: Optional[dict] = Field(None, description="视频信息")
    prerequisite_knowledge: List[PrerequisiteKnowledge] = Field(
        default_factory=list, description="前置知识列表"
    )
    analysis_model: str = Field(description="使用的分析模型")
    confidence_score: int = Field(default=0, description="置信度评分 0-100")
    created_at: datetime = Field(default_factory=datetime.now, description="分析时间")


class KnowledgeWithResources(KnowledgeResponse):
    """包含学习资源的知识点模型"""
    resources: List[LearningResourceResponse] = Field(
        default_factory=list, description="关联的学习资源"
    )
    tags: List[TagResponse] = Field(
        default_factory=list, description="关联的标签"
    )
    prerequisites: List[KnowledgeResponse] = Field(
        default_factory=list, description="前置知识点"
    )


class PrerequisiteRelationCreate(BaseModel):
    """创建前置关系的请求模型"""
    knowledge_id: int
    prerequisite_id: int


class PrerequisiteRelationBatch(BaseModel):
    """批量创建前置关系的请求模型"""
    relations: List[PrerequisiteRelationCreate] 