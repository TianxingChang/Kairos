"""
Video segment search tool for AI agents.
Enables intelligent retrieval of video segments based on questions and knowledge points.
"""

from typing import List, Dict, Any, Optional
import logging
from sqlalchemy.orm import Session
from agno.tools import Tool

logger = logging.getLogger(__name__)


class VideoSegmentSearchTool(Tool):
    """
    Tool for searching video segments based on questions and knowledge points.
    """
    
    def __init__(self, db_session: Session = None):
        super().__init__(
            name="video_segment_search",
            description="""
            Search for video segments that match specific questions or knowledge points.
            
            This tool can find relevant video segments with time ranges that explain
            concepts related to the user's question. Use this when you need to find
            video content that explains or demonstrates specific knowledge points.
            
            Parameters:
            - question: The user's question or topic to search for
            - knowledge_keywords: List of specific knowledge point keywords
            - resource_ids: Optional list of specific video resource IDs to search within
            - max_results: Maximum number of segments to return (default 5)
            
            Returns:
            - List of video segments with time ranges, descriptions, and relevance scores
            """
        )
        self.db_session = db_session
    
    def run(
        self,
        question: str,
        knowledge_keywords: Optional[List[str]] = None,
        resource_ids: Optional[List[int]] = None,
        max_results: int = 5
    ) -> str:
        """
        Search for video segments based on question and knowledge keywords.
        
        Args:
            question: User's question or search query
            knowledge_keywords: Specific knowledge point keywords to search for
            resource_ids: Optional list of video resource IDs to limit search
            max_results: Maximum number of results to return
            
        Returns:
            JSON string with search results
        """
        try:
            if not self.db_session:
                from db.session import get_db
                db_gen = get_db()
                self.db_session = next(db_gen)
            
            from services.video_answer_service import VideoAnswerService
            service = VideoAnswerService(self.db_session)
            
            # Search for relevant video segments
            segments = service.search_video_segments_by_question(
                question=question,
                knowledge_keywords=knowledge_keywords or [],
                resource_ids=resource_ids,
                max_results=max_results
            )
            
            if not segments:
                return "No relevant video segments found for the given question."
            
            # Format results for agent consumption
            results = []
            for segment in segments:
                result = {
                    "segment_id": segment["segment_id"],
                    "video_title": segment["video_resource"]["title"],
                    "video_url": segment["video_resource"]["url"],
                    "time_range": {
                        "start": f"{segment['time_range']['start_time']}",
                        "end": f"{segment['time_range']['end_time']}",
                        "duration": f"{segment['time_range']['duration']} seconds"
                    },
                    "knowledge_point": segment["knowledge_point"]["title"],
                    "description": segment["segment_description"],
                    "relevance_score": segment["relevance_score"]
                }
                results.append(result)
            
            import json
            return json.dumps({
                "success": True,
                "question": question,
                "total_results": len(results),
                "segments": results
            }, ensure_ascii=False, indent=2)
            
        except Exception as e:
            logger.error(f"Error in video segment search: {str(e)}")
            return f"Error searching video segments: {str(e)}"


class KnowledgePointLookupTool(Tool):
    """
    Tool for looking up detailed information about knowledge points.
    """
    
    def __init__(self, db_session: Session = None):
        super().__init__(
            name="knowledge_point_lookup",
            description="""
            Look up detailed information about specific knowledge points by ID or title.
            
            This tool can retrieve comprehensive information about knowledge points
            including their descriptions, domains, prerequisites, and related resources.
            
            Parameters:
            - knowledge_ids: List of knowledge point IDs to look up
            - titles: List of knowledge point titles to search for
            - domain: Optional domain filter (e.g., "机器学习", "深度学习")
            
            Returns:
            - Detailed information about the knowledge points
            """
        )
        self.db_session = db_session
    
    def run(
        self,
        knowledge_ids: Optional[List[int]] = None,
        titles: Optional[List[str]] = None,
        domain: Optional[str] = None
    ) -> str:
        """
        Look up knowledge points by IDs or titles.
        
        Args:
            knowledge_ids: List of knowledge point IDs
            titles: List of knowledge point titles to search
            domain: Optional domain filter
            
        Returns:
            JSON string with knowledge point details
        """
        try:
            if not self.db_session:
                from db.session import get_db
                db_gen = get_db()
                self.db_session = next(db_gen)
            
            from db.models import Knowledge
            from sqlalchemy import or_, and_
            
            query = self.db_session.query(Knowledge).filter(Knowledge.is_active == True)
            
            # Apply filters
            if knowledge_ids:
                query = query.filter(Knowledge.id.in_(knowledge_ids))
            
            if titles:
                title_conditions = [Knowledge.title.ilike(f"%{title}%") for title in titles]
                query = query.filter(or_(*title_conditions))
            
            if domain:
                query = query.filter(Knowledge.domain.ilike(f"%{domain}%"))
            
            knowledge_points = query.limit(20).all()
            
            if not knowledge_points:
                return "No knowledge points found matching the criteria."
            
            # Format results
            results = []
            for kp in knowledge_points:
                result = {
                    "id": kp.id,
                    "title": kp.title,
                    "description": kp.description,
                    "domain": kp.domain,
                    "difficulty_level": kp.difficulty_level,
                    "knowledge_level": kp.knowledge_level,
                    "search_keywords": kp.search_keywords
                }
                results.append(result)
            
            import json
            return json.dumps({
                "success": True,
                "total_results": len(results),
                "knowledge_points": results
            }, ensure_ascii=False, indent=2)
            
        except Exception as e:
            logger.error(f"Error in knowledge point lookup: {str(e)}")
            return f"Error looking up knowledge points: {str(e)}"


class VideoResourceSearchTool(Tool):
    """
    Tool for searching and getting information about video resources.
    """
    
    def __init__(self, db_session: Session = None):
        super().__init__(
            name="video_resource_search",
            description="""
            Search for video resources based on title, URL, or content keywords.
            
            This tool can find video resources that contain content related to
            specific topics or questions.
            
            Parameters:
            - search_query: Search query for video titles or descriptions
            - resource_ids: Optional list of specific resource IDs
            - has_segments: Filter for videos that have been segmented
            
            Returns:
            - List of video resources with their metadata
            """
        )
        self.db_session = db_session
    
    def run(
        self,
        search_query: Optional[str] = None,
        resource_ids: Optional[List[int]] = None,
        has_segments: bool = True
    ) -> str:
        """
        Search for video resources.
        
        Args:
            search_query: Text to search in titles and descriptions
            resource_ids: Specific resource IDs to retrieve
            has_segments: Only return videos that have been segmented
            
        Returns:
            JSON string with video resource information
        """
        try:
            if not self.db_session:
                from db.session import get_db
                db_gen = get_db()
                self.db_session = next(db_gen)
            
            from db.models import LearningResource, VideoSegment
            from sqlalchemy import and_, or_
            
            query = self.db_session.query(LearningResource)
            
            # Apply filters
            if resource_ids:
                query = query.filter(LearningResource.id.in_(resource_ids))
            
            if search_query:
                search_conditions = [
                    LearningResource.title.ilike(f"%{search_query}%"),
                    LearningResource.description.ilike(f"%{search_query}%")
                ]
                query = query.filter(or_(*search_conditions))
            
            if has_segments:
                # Only return resources that have video segments
                query = query.filter(
                    LearningResource.id.in_(
                        self.db_session.query(VideoSegment.resource_id).distinct()
                    )
                )
            
            resources = query.limit(20).all()
            
            if not resources:
                return "No video resources found matching the criteria."
            
            # Format results
            results = []
            for resource in resources:
                # Count segments for this resource
                segment_count = self.db_session.query(VideoSegment).filter(
                    VideoSegment.resource_id == resource.id
                ).count()
                
                result = {
                    "resource_id": resource.id,
                    "title": resource.title,
                    "url": resource.resource_url,
                    "description": resource.description,
                    "duration_minutes": resource.duration_minutes,
                    "segment_count": segment_count,
                    "created_at": resource.created_at.isoformat() if resource.created_at else None
                }
                results.append(result)
            
            import json
            return json.dumps({
                "success": True,
                "total_results": len(results),
                "resources": results
            }, ensure_ascii=False, indent=2)
            
        except Exception as e:
            logger.error(f"Error in video resource search: {str(e)}")
            return f"Error searching video resources: {str(e)}"