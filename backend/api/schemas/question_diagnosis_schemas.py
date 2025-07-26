"""Pydantic schemas for question diagnosis API."""

from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum


class DiagnosisJobStatus(str, Enum):
    """Enumeration of diagnosis job statuses."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class QuestionDiagnosisRequest(BaseModel):
    """Request model for question diagnosis."""
    
    user_question: str = Field(
        description="The user's natural language question",
        min_length=1,
        max_length=1000,
        example="为什么PPO算法里要用clip函数来限制策略更新的幅度？"
    )
    context_resource_id: int = Field(
        description="ID of the learning resource the user is currently viewing",
        gt=0,
        example=51
    )


class DiagnosedKnowledgePoint(BaseModel):
    """A diagnosed knowledge point with relevance information."""
    
    knowledge_id: int = Field(
        description="ID of the knowledge point",
        example=123
    )
    title: str = Field(
        description="Title of the knowledge point",
        example="PPO算法的裁剪机制"
    )
    relevance_score: float = Field(
        description="Relevance score between 0.0 and 1.0",
        ge=0.0,
        le=1.0,
        example=0.95
    )
    explanation: str = Field(
        description="Explanation of why this knowledge point is relevant",
        example="用户问题直接涉及PPO算法中clip函数的作用机制"
    )


class ContextualKnowledgePoint(BaseModel):
    """A contextual knowledge point from the current resource."""
    
    knowledge_id: int = Field(
        description="ID of the knowledge point",
        example=124
    )
    title: str = Field(
        description="Title of the knowledge point",
        example="强化学习中的策略梯度方法"
    )


class QuestionDiagnosisJobResponse(BaseModel):
    """Response model for creating a diagnosis job."""
    
    job_id: str = Field(
        description="Unique identifier for the diagnosis job",
        example="a1b2c3d4-e5f6-7890-abcd-ef1234567890"
    )
    status_url: str = Field(
        description="URL to check the status of the diagnosis job",
        example="/api/v1/questions/diagnose/status/a1b2c3d4-e5f6-7890-abcd-ef1234567890"
    )


class QuestionDiagnosisStatusResponse(BaseModel):
    """Response model for diagnosis job status and results."""
    
    job_id: str = Field(
        description="Unique identifier for the diagnosis job",
        example="a1b2c3d4-e5f6-7890-abcd-ef1234567890"
    )
    status: DiagnosisJobStatus = Field(
        description="Current status of the diagnosis job"
    )
    message: Optional[str] = Field(
        description="Human-readable status message",
        example="Diagnosis completed successfully"
    )
    user_question: Optional[str] = Field(
        description="The original user question",
        example="为什么PPO算法里要用clip函数来限制策略更新的幅度？"
    )
    diagnosed_knowledge_points: Optional[List[DiagnosedKnowledgePoint]] = Field(
        description="List of diagnosed knowledge points relevant to the question",
        default=None
    )
    contextual_candidate_knowledge_points: Optional[List[ContextualKnowledgePoint]] = Field(
        description="List of candidate knowledge points from the current resource context",
        default=None
    )
    error_message: Optional[str] = Field(
        description="Error message if the diagnosis failed",
        default=None
    )
    created_at: Optional[datetime] = Field(
        description="Timestamp when the job was created",
        default=None
    )
    completed_at: Optional[datetime] = Field(
        description="Timestamp when the job was completed",
        default=None
    )


class ErrorResponse(BaseModel):
    """Standard error response model."""
    
    success: bool = Field(default=False)
    error: str = Field(description="Error message")
    error_type: str = Field(description="Type of error")
    detail: Optional[str] = Field(description="Additional error details", default=None)