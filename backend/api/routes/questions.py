"""Question diagnosis API routes."""

import logging
import uuid
from datetime import datetime
from typing import Dict

from fastapi import APIRouter, HTTPException, status, Depends, BackgroundTasks
from sqlalchemy.orm import Session

from db.session import get_db
from db.models import LearningResource
from api.schemas.question_diagnosis_schemas import (
    QuestionDiagnosisRequest,
    QuestionDiagnosisJobResponse,
    QuestionDiagnosisStatusResponse,
    DiagnosisJobStatus,
    ErrorResponse
)

logger = logging.getLogger(__name__)

questions_router = APIRouter(prefix="/questions", tags=["Question Diagnosis"])

# Simple in-memory storage for job status (production should use Redis)
diagnosis_job_store: Dict[str, Dict] = {}


@questions_router.post(
    "/diagnose/sync",
    response_model=Dict,
    status_code=status.HTTP_200_OK
)
async def diagnose_question_sync(
    request: QuestionDiagnosisRequest,
    db: Session = Depends(get_db)
):
    """
    Synchronously diagnose a question and return JSON results immediately.
    
    This endpoint provides a simple sync API that returns diagnosed knowledge points
    and contextual candidates directly as JSON without the need for polling.
    """
    try:
        # Validate that the resource exists
        resource = db.query(LearningResource).filter(
            LearningResource.id == request.context_resource_id
        ).first()
        
        if not resource:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Learning resource with id {request.context_resource_id} not found"
            )
        
        logger.info(f"Starting sync diagnosis for question: {request.user_question}")
        logger.info(f"Context resource ID: {request.context_resource_id}")
        
        # Initialize service
        from services.question_diagnosis_service import QuestionDiagnosisService
        service = QuestionDiagnosisService(db)
        
        # Get contextual knowledge points
        contextual_knowledge_points = service.get_contextual_knowledge_points(request.context_resource_id)
        
        # Perform diagnosis
        diagnosed_points, contextual_points, used_global = service.diagnose_user_question(
            request.user_question, contextual_knowledge_points
        )
        
        # Validate knowledge points exist
        diagnosed_ids = [point["knowledge_id"] for point in diagnosed_points]
        contextual_ids = [point["knowledge_id"] for point in contextual_points]
        
        valid_diagnosed_ids = service.validate_knowledge_points_exist(diagnosed_ids)
        valid_contextual_ids = service.validate_knowledge_points_exist(contextual_ids)
        
        # Filter out invalid knowledge points
        filtered_diagnosed_points = [
            point for point in diagnosed_points 
            if point["knowledge_id"] in valid_diagnosed_ids
        ]
        filtered_contextual_points = [
            point for point in contextual_points 
            if point["knowledge_id"] in valid_contextual_ids
        ]
        
        # Return JSON response
        result = {
            "success": True,
            "user_question": request.user_question,
            "context_resource_id": request.context_resource_id,
            "diagnosed_knowledge_points": filtered_diagnosed_points,
            "contextual_candidate_knowledge_points": filtered_contextual_points,
            "used_global_search": used_global,
            "summary": {
                "total_diagnosed": len(filtered_diagnosed_points),
                "total_contextual": len(filtered_contextual_points),
                "max_relevance_score": max([p.get("relevance_score", 0) for p in filtered_diagnosed_points] + [0])
            }
        }
        
        logger.info(f"Sync diagnosis completed: {len(filtered_diagnosed_points)} diagnosed, {len(filtered_contextual_points)} contextual")
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to diagnose question synchronously: {str(e)}")
        import traceback
        logger.error(f"Full traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to diagnose question: {str(e)}"
        )


@questions_router.post(
    "/diagnose",
    response_model=QuestionDiagnosisJobResponse,
    status_code=status.HTTP_202_ACCEPTED
)
async def create_diagnosis_job(
    request: QuestionDiagnosisRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Create a new question diagnosis job.
    
    This endpoint starts a background task to analyze the user's question
    and identify relevant knowledge points, then immediately returns a job_id
    for the client to poll for status and results.
    """
    try:
        # Validate that the resource exists
        resource = db.query(LearningResource).filter(
            LearningResource.id == request.context_resource_id
        ).first()
        
        if not resource:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Learning resource with id {request.context_resource_id} not found"
            )
        
        # Create unique job_id
        job_id = str(uuid.uuid4())
        
        # Initialize job status
        diagnosis_job_store[job_id] = {
            "job_id": job_id,
            "status": DiagnosisJobStatus.PENDING,
            "message": "Job created, waiting to start processing",
            "user_question": request.user_question,
            "context_resource_id": request.context_resource_id,
            "diagnosed_knowledge_points": None,
            "contextual_candidate_knowledge_points": None,
            "error_message": None,
            "created_at": datetime.utcnow(),
            "completed_at": None
        }
        
        # Start background task
        background_tasks.add_task(
            run_diagnosis_task,
            job_id,
            request.user_question,
            request.context_resource_id
        )
        
        return QuestionDiagnosisJobResponse(
            job_id=job_id,
            status_url=f"/v1/questions/diagnose/status/{job_id}"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create diagnosis job: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create diagnosis job: {str(e)}"
        )


@questions_router.get(
    "/diagnose/status/{job_id}",
    response_model=QuestionDiagnosisStatusResponse
)
async def get_diagnosis_status(job_id: str):
    """
    Get the status and results of a question diagnosis job.
    
    Returns the current status of the job. If completed successfully,
    includes the diagnosed knowledge points and contextual candidates.
    """
    if job_id not in diagnosis_job_store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Diagnosis job {job_id} not found"
        )
    
    job_data = diagnosis_job_store[job_id]
    
    return QuestionDiagnosisStatusResponse(**job_data)


async def run_diagnosis_task(
    job_id: str,
    user_question: str,
    context_resource_id: int
):
    """
    Background task to run the question diagnosis.
    
    This function performs the core diagnosis logic:
    1. Get contextual knowledge points from the resource
    2. Build diagnosis prompt with user question and candidates
    3. Call LLM for analysis
    4. Parse and store results
    """
    try:
        # Update status to processing
        diagnosis_job_store[job_id]["status"] = DiagnosisJobStatus.PROCESSING
        diagnosis_job_store[job_id]["message"] = "Analyzing question and identifying relevant knowledge points"
        
        logger.info(f"Starting diagnosis for job {job_id}")
        logger.info(f"Question: {user_question}")
        logger.info(f"Context resource ID: {context_resource_id}")
        
        # Step 1: Get database session and initialize service
        from db.session import get_db
        from services.question_diagnosis_service import QuestionDiagnosisService
        
        db_gen = get_db()
        db = next(db_gen)
        
        try:
            service = QuestionDiagnosisService(db)
            
            # Step 2: Get contextual knowledge points
            diagnosis_job_store[job_id]["message"] = "Retrieving contextual knowledge points"
            contextual_knowledge_points = service.get_contextual_knowledge_points(context_resource_id)
            
            # Step 3: Perform two-stage diagnosis
            diagnosis_job_store[job_id]["message"] = "Analyzing question with AI model"
            diagnosed_points, contextual_points, used_global = service.diagnose_user_question(
                user_question, contextual_knowledge_points
            )
            
            # Step 4: Validate knowledge points exist
            diagnosed_ids = [point["knowledge_id"] for point in diagnosed_points]
            contextual_ids = [point["knowledge_id"] for point in contextual_points]
            
            valid_diagnosed_ids = service.validate_knowledge_points_exist(diagnosed_ids)
            valid_contextual_ids = service.validate_knowledge_points_exist(contextual_ids)
            
            # Filter out invalid knowledge points
            filtered_diagnosed_points = [
                point for point in diagnosed_points 
                if point["knowledge_id"] in valid_diagnosed_ids
            ]
            filtered_contextual_points = [
                point for point in contextual_points 
                if point["knowledge_id"] in valid_contextual_ids
            ]
            
            # Update job status with results
            success_message = "Diagnosis completed successfully"
            if used_global:
                success_message += " (used global knowledge search)"
            
            diagnosis_job_store[job_id].update({
                "status": DiagnosisJobStatus.COMPLETED,
                "message": success_message,
                "diagnosed_knowledge_points": filtered_diagnosed_points,
                "contextual_candidate_knowledge_points": filtered_contextual_points,
                "completed_at": datetime.utcnow()
            })
            
            logger.info(f"Diagnosis completed for job {job_id}")
            logger.info(f"Found {len(filtered_diagnosed_points)} diagnosed knowledge points (global: {used_global})")
            
        finally:
            db.close()
        
    except Exception as e:
        logger.error(f"Diagnosis failed for job {job_id}: {str(e)}")
        import traceback
        logger.error(f"Full traceback: {traceback.format_exc()}")
        
        diagnosis_job_store[job_id].update({
            "status": DiagnosisJobStatus.FAILED,
            "message": "Diagnosis failed",
            "error_message": str(e),
            "completed_at": datetime.utcnow()
        })


# Import asyncio at the top for the background task
import asyncio