"""
Video-based question answering API routes (API 5).
Combines question diagnosis with video segment retrieval for comprehensive answers.
"""

import logging
import uuid
from datetime import datetime
from typing import Dict, Any

from fastapi import APIRouter, HTTPException, status, Depends, BackgroundTasks
from sqlalchemy.orm import Session

from db.session import get_db
from api.schemas.video_answer_schemas import (
    VideoAnswerRequest,
    VideoAnswerResponse,
    VideoAnswerJobResponse,
    VideoAnswerJobStatus
)

logger = logging.getLogger(__name__)

video_answer_router = APIRouter(prefix="/video-answers", tags=["Video-based Question Answering"])

# In-memory job store (use Redis in production)
video_answer_job_store: Dict[str, Dict] = {}


@video_answer_router.post(
    "/sync",
    response_model=VideoAnswerResponse,
    status_code=status.HTTP_200_OK
)
async def get_video_answer_sync(
    request: VideoAnswerRequest,
    db: Session = Depends(get_db)
):
    """
    Get video-based answers for a question synchronously.
    
    This endpoint:
    1. Breaks down the user's question into sub-questions
    2. Searches relevant video segments for each sub-question
    3. Generates comprehensive answers based on video content
    4. Returns results immediately
    """
    try:
        logger.info(f"Processing sync video answer request: {request.user_question}")
        
        # Initialize video answer service
        from services.video_answer_service import VideoAnswerService
        service = VideoAnswerService(db)
        
        # Get video-based answer
        result = service.get_video_answer(
            user_question=request.user_question,
            context_resource_id=request.context_resource_id,
            max_video_segments=request.max_video_segments,
            enable_global_search=request.enable_global_search
        )
        
        # Convert to response model
        response = VideoAnswerResponse(
            success=result["success"],
            user_question=result["user_question"],
            question_breakdowns=result["question_breakdowns"],
            total_video_segments=result["total_video_segments"],
            search_strategy=result["search_strategy"],
            processing_time_seconds=result["processing_time_seconds"]
        )
        
        logger.info(f"Sync video answer completed successfully with {result['total_video_segments']} segments")
        return response
        
    except Exception as e:
        logger.error(f"Error in sync video answer: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process video answer request: {str(e)}"
        )


@video_answer_router.post(
    "/async",
    response_model=VideoAnswerJobResponse,
    status_code=status.HTTP_202_ACCEPTED
)
async def create_video_answer_job(
    request: VideoAnswerRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Create an async video answer job for complex questions.
    
    Use this endpoint for questions that might take longer to process.
    Returns a job_id that can be used to poll for results.
    """
    try:
        # Create unique job ID
        job_id = str(uuid.uuid4())
        
        # Initialize job status
        video_answer_job_store[job_id] = {
            "job_id": job_id,
            "status": "pending",
            "progress_percentage": 0,
            "message": "Job created, starting video answer analysis",
            "current_step": "initialization",
            "result": None,
            "error_message": None,
            "created_at": datetime.utcnow(),
            "completed_at": None
        }
        
        # Start background task
        background_tasks.add_task(
            run_video_answer_task,
            job_id,
            request.user_question,
            request.context_resource_id,
            request.max_video_segments,
            request.enable_global_search
        )
        
        logger.info(f"Created video answer job {job_id} for question: {request.user_question}")
        
        return VideoAnswerJobResponse(
            job_id=job_id,
            status_url=f"/v1/video-answers/status/{job_id}"
        )
        
    except Exception as e:
        logger.error(f"Error creating video answer job: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create video answer job: {str(e)}"
        )


@video_answer_router.get(
    "/status/{job_id}",
    response_model=VideoAnswerJobStatus
)
async def get_video_answer_job_status(job_id: str):
    """
    Get the status and results of a video answer job.
    """
    if job_id not in video_answer_job_store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Video answer job {job_id} not found"
        )
    
    job_data = video_answer_job_store[job_id]
    
    return VideoAnswerJobStatus(**job_data)


@video_answer_router.get(
    "/search/segments",
    response_model=Dict[str, Any]
)
async def search_video_segments(
    question: str,
    resource_ids: str = None,  # Comma-separated resource IDs
    max_results: int = 10,
    db: Session = Depends(get_db)
):
    """
    Search video segments directly based on a question.
    
    This is a utility endpoint for testing the video segment search functionality.
    """
    try:
        from services.video_answer_service import VideoAnswerService
        service = VideoAnswerService(db)
        
        # Parse resource IDs if provided
        resource_id_list = None
        if resource_ids:
            try:
                resource_id_list = [int(rid.strip()) for rid in resource_ids.split(",")]
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid resource_ids format. Use comma-separated integers."
                )
        
        # Search video segments
        segments = service.search_video_segments_by_question(
            question=question,
            resource_ids=resource_id_list,
            max_results=max_results
        )
        
        return {
            "success": True,
            "question": question,
            "total_results": len(segments),
            "segments": segments
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error searching video segments: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to search video segments: {str(e)}"
        )


async def run_video_answer_task(
    job_id: str,
    user_question: str,
    context_resource_id: int = None,
    max_video_segments: int = 5,
    enable_global_search: bool = True
):
    """
    Background task to run video answer analysis.
    """
    try:
        # Update job status
        video_answer_job_store[job_id].update({
            "status": "processing",
            "progress_percentage": 10,
            "message": "Analyzing question and searching video segments",
            "current_step": "question_analysis"
        })
        
        logger.info(f"Starting video answer task for job {job_id}")
        
        # Get database session
        from db.session import get_db
        db_gen = get_db()
        db = next(db_gen)
        
        try:
            # Initialize service
            from services.video_answer_service import VideoAnswerService
            service = VideoAnswerService(db)
            
            # Update progress
            video_answer_job_store[job_id].update({
                "progress_percentage": 30,
                "message": "Breaking down question into sub-questions",
                "current_step": "question_breakdown"
            })
            
            # Process video answer
            result = service.get_video_answer(
                user_question=user_question,
                context_resource_id=context_resource_id,
                max_video_segments=max_video_segments,
                enable_global_search=enable_global_search
            )
            
            # Update progress
            video_answer_job_store[job_id].update({
                "progress_percentage": 80,
                "message": "Generating comprehensive answers",
                "current_step": "answer_generation"
            })
            
            # Create response
            response = VideoAnswerResponse(
                success=result["success"],
                user_question=result["user_question"],
                question_breakdowns=result["question_breakdowns"],
                total_video_segments=result["total_video_segments"],
                search_strategy=result["search_strategy"],
                processing_time_seconds=result["processing_time_seconds"]
            )
            
            # Update job as completed
            video_answer_job_store[job_id].update({
                "status": "completed",
                "progress_percentage": 100,
                "message": f"Video answer analysis completed successfully",
                "current_step": "completed",
                "result": response.dict(),
                "completed_at": datetime.utcnow()
            })
            
            logger.info(f"Video answer task completed for job {job_id}")
            
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Video answer task failed for job {job_id}: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        
        video_answer_job_store[job_id].update({
            "status": "failed",
            "progress_percentage": 0,
            "message": "Video answer analysis failed",
            "current_step": "failed",
            "error_message": str(e),
            "completed_at": datetime.utcnow()
        })


# Health check endpoint for video answer service
@video_answer_router.get("/health")
async def video_answer_health_check(db: Session = Depends(get_db)):
    """
    Health check endpoint for video answer service.
    """
    try:
        # Check database connectivity
        from db.models import VideoSegment
        segment_count = db.query(VideoSegment).count()
        
        return {
            "status": "healthy",
            "service": "video_answer_api",
            "database_connected": True,
            "total_video_segments": segment_count,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Video answer health check failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Service unhealthy: {str(e)}"
        )