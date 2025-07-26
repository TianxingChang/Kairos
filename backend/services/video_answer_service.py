"""
Video-based question answering service.
Combines question diagnosis with video segment search to provide comprehensive answers.
"""

import json
import logging
import time
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc

from db.models import LearningResource, Knowledge, VideoSegment
from services.question_diagnosis_service import QuestionDiagnosisService

logger = logging.getLogger(__name__)


class VideoAnswerService:
    """Service for answering questions using video segments."""
    
    def __init__(self, db: Session):
        self.db = db
        self.question_service = QuestionDiagnosisService(db)
    
    def get_video_answer(
        self,
        user_question: str,
        context_resource_id: Optional[int] = None,
        max_video_segments: int = 5,
        enable_global_search: bool = True
    ) -> Dict[str, Any]:
        """
        Main entry point for video-based question answering.
        
        Args:
            user_question: User's natural language question
            context_resource_id: Optional resource ID to prioritize
            max_video_segments: Maximum number of video segments to return
            enable_global_search: Whether to search all video resources
            
        Returns:
            Complete video answer response
        """
        start_time = time.time()
        
        try:
            logger.info(f"Processing video answer request for: {user_question}")
            
            # Step 1: Break down the question into sub-questions
            question_breakdowns = self.break_down_question(user_question)
            
            # Step 2: For each sub-question, find relevant video segments
            enriched_breakdowns = []
            total_segments = 0
            
            for breakdown in question_breakdowns:
                # Search video segments for this sub-question
                video_segments = self.search_video_segments_by_question(
                    question=breakdown["sub_question"],
                    knowledge_keywords=breakdown.get("knowledge_keywords", []),
                    resource_ids=[context_resource_id] if context_resource_id else None,
                    max_results=max_video_segments
                )
                
                # If context search didn't find enough results and global search is enabled
                if len(video_segments) < 2 and enable_global_search and context_resource_id:
                    logger.info(f"Context search found {len(video_segments)} segments, trying global search")
                    global_segments = self.search_video_segments_by_question(
                        question=breakdown["sub_question"],
                        knowledge_keywords=breakdown.get("knowledge_keywords", []),
                        resource_ids=None,  # Search all resources
                        max_results=max_video_segments
                    )
                    # Merge results, prioritizing context results
                    video_segments = self._merge_video_segments(video_segments, global_segments, max_video_segments)
                
                # Generate comprehensive answer based on found segments
                answer_summary = self._generate_answer_from_segments(
                    breakdown["sub_question"], 
                    video_segments
                )
                
                enriched_breakdown = {
                    "sub_question": breakdown["sub_question"],
                    "knowledge_focus": breakdown["knowledge_focus"],
                    "video_segments": video_segments,
                    "answer_summary": answer_summary
                }
                enriched_breakdowns.append(enriched_breakdown)
                total_segments += len(video_segments)
            
            # Determine search strategy
            search_strategy = "context_only" if context_resource_id and not enable_global_search else \
                             "context_with_global_fallback" if context_resource_id else \
                             "global_search"
            
            processing_time = time.time() - start_time
            
            return {
                "success": True,
                "user_question": user_question,
                "question_breakdowns": enriched_breakdowns,
                "total_video_segments": total_segments,
                "search_strategy": search_strategy,
                "processing_time_seconds": round(processing_time, 2)
            }
            
        except Exception as e:
            logger.error(f"Error in video answer processing: {str(e)}")
            raise
    
    def break_down_question(self, user_question: str) -> List[Dict[str, Any]]:
        """
        Break down a complex question into simpler sub-questions.
        
        Args:
            user_question: User's original question
            
        Returns:
            List of question breakdowns with focus areas
        """
        try:
            # Use LLM to break down the question
            breakdown_prompt = self._build_question_breakdown_prompt(user_question)
            llm_response = self._call_llm(breakdown_prompt)
            
            if llm_response:
                breakdowns = self._parse_question_breakdown_response(llm_response)
                if breakdowns:
                    logger.info(f"Successfully broke down question into {len(breakdowns)} sub-questions")
                    return breakdowns
            
            # Fallback: treat the entire question as a single breakdown
            logger.warning("Question breakdown failed, using original question as single breakdown")
            return [{
                "sub_question": user_question,
                "knowledge_focus": "general",
                "knowledge_keywords": self.question_service._extract_keywords(user_question)
            }]
            
        except Exception as e:
            logger.error(f"Error in question breakdown: {str(e)}")
            # Fallback
            return [{
                "sub_question": user_question,
                "knowledge_focus": "general",
                "knowledge_keywords": self.question_service._extract_keywords(user_question)
            }]
    
    def search_video_segments_by_question(
        self,
        question: str,
        knowledge_keywords: List[str] = None,
        resource_ids: Optional[List[int]] = None,
        max_results: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Search video segments that are relevant to a specific question.
        
        Args:
            question: The question to search for
            knowledge_keywords: Additional keywords to search
            resource_ids: Optional list of resource IDs to limit search
            max_results: Maximum number of results
            
        Returns:
            List of relevant video segments with metadata
        """
        try:
            # Step 1: Use question diagnosis to find relevant knowledge points
            if resource_ids:
                # Get contextual knowledge from specified resources
                contextual_knowledge = []
                for resource_id in resource_ids:
                    kp_list = self.question_service.get_contextual_knowledge_points(resource_id)
                    contextual_knowledge.extend(kp_list)
            else:
                # Use global knowledge points
                contextual_knowledge = self.question_service.get_global_knowledge_points(limit=50)
            
            # Perform question diagnosis
            diagnosed_points, contextual_points, used_global = self.question_service.diagnose_user_question(
                question, contextual_knowledge
            )
            
            # Extract knowledge point IDs
            relevant_knowledge_ids = [point["knowledge_id"] for point in diagnosed_points]
            if not relevant_knowledge_ids:
                # If no diagnosed points, use contextual points
                relevant_knowledge_ids = [point["knowledge_id"] for point in contextual_points[:10]]
            
            # Step 2: Search video segments based on knowledge points
            segments = self._search_segments_by_knowledge_ids(
                relevant_knowledge_ids, 
                resource_ids, 
                max_results * 2  # Get more candidates for ranking
            )
            
            # Step 3: Rank segments by relevance to the question
            ranked_segments = self._rank_segments_by_question_relevance(
                question, segments, diagnosed_points
            )
            
            # Step 4: Format results
            formatted_segments = []
            for segment_data in ranked_segments[:max_results]:
                formatted_segment = self._format_video_segment(segment_data)
                formatted_segments.append(formatted_segment)
            
            logger.info(f"Found {len(formatted_segments)} relevant video segments for question")
            return formatted_segments
            
        except Exception as e:
            logger.error(f"Error searching video segments: {str(e)}")
            return []
    
    def _search_segments_by_knowledge_ids(
        self, 
        knowledge_ids: List[int], 
        resource_ids: Optional[List[int]] = None,
        max_results: int = 10
    ) -> List[Dict]:
        """Search video segments by knowledge point IDs."""
        try:
            # Query video segments with related knowledge and resource info
            query = self.db.query(
                VideoSegment,
                Knowledge,
                LearningResource
            ).join(
                Knowledge, VideoSegment.knowledge_id == Knowledge.id
            ).join(
                LearningResource, VideoSegment.resource_id == LearningResource.id
            ).filter(
                VideoSegment.knowledge_id.in_(knowledge_ids)
            )
            
            # Apply resource filter if specified
            if resource_ids:
                query = query.filter(VideoSegment.resource_id.in_(resource_ids))
            
            # Order by importance and recency
            query = query.order_by(
                desc(VideoSegment.importance_level),
                desc(VideoSegment.created_at)
            ).limit(max_results)
            
            results = query.all()
            
            # Format results
            segments = []
            for segment, knowledge, resource in results:
                segment_data = {
                    "segment": segment,
                    "knowledge": knowledge,
                    "resource": resource
                }
                segments.append(segment_data)
            
            return segments
            
        except Exception as e:
            logger.error(f"Error searching segments by knowledge IDs: {str(e)}")
            return []
    
    def _rank_segments_by_question_relevance(
        self, 
        question: str, 
        segments: List[Dict],
        diagnosed_points: List[Dict]
    ) -> List[Dict]:
        """Rank video segments by their relevance to the question."""
        try:
            # Create a mapping of knowledge_id to relevance score from diagnosis
            knowledge_scores = {}
            for point in diagnosed_points:
                knowledge_scores[point["knowledge_id"]] = point.get("relevance_score", 0.5)
            
            # Extract question keywords for text matching
            question_keywords = self.question_service._extract_keywords(question)
            
            # Score each segment
            scored_segments = []
            for segment_data in segments:
                segment = segment_data["segment"]
                knowledge = segment_data["knowledge"]
                
                # Base score from knowledge point diagnosis
                base_score = knowledge_scores.get(knowledge.id, 0.3)
                
                # Text similarity score
                segment_text = f"{segment.segment_title} {segment.segment_description}"
                text_score = self._calculate_text_similarity(question_keywords, segment_text)
                
                # Importance bonus
                importance_bonus = (segment.importance_level or 1) * 0.1
                
                # Combined score
                total_score = base_score * 0.6 + text_score * 0.3 + importance_bonus
                
                segment_data["relevance_score"] = total_score
                scored_segments.append(segment_data)
            
            # Sort by score descending
            scored_segments.sort(key=lambda x: x["relevance_score"], reverse=True)
            
            return scored_segments
            
        except Exception as e:
            logger.error(f"Error ranking segments: {str(e)}")
            return segments
    
    def _calculate_text_similarity(self, keywords: List[str], text: str) -> float:
        """Calculate similarity between keywords and text."""
        if not keywords or not text:
            return 0.0
        
        text_lower = text.lower()
        matches = 0
        
        for keyword in keywords:
            if keyword.lower() in text_lower:
                matches += 1
        
        return min(matches / len(keywords), 1.0)
    
    def _format_video_segment(self, segment_data: Dict) -> Dict[str, Any]:
        """Format video segment data for API response."""
        segment = segment_data["segment"]
        knowledge = segment_data["knowledge"]
        resource = segment_data["resource"]
        relevance_score = segment_data.get("relevance_score", 0.5)
        
        return {
            "segment_id": segment.id,
            "video_resource": {
                "resource_id": resource.id,
                "title": resource.title,
                "url": resource.resource_url,
                "duration_minutes": resource.duration_minutes
            },
            "time_range": {
                "start_seconds": segment.start_seconds,
                "end_seconds": segment.end_seconds,
                "start_time": segment.start_time,
                "end_time": segment.end_time,
                "duration": segment.end_seconds - segment.start_seconds
            },
            "knowledge_point": {
                "id": knowledge.id,
                "title": knowledge.title,
                "description": knowledge.description,
                "domain": knowledge.domain,
                "level": knowledge.knowledge_level
            },
            "relevance_score": round(relevance_score, 3),
            "segment_description": segment.segment_description,
            "answer_explanation": self._generate_segment_answer_explanation(segment, knowledge)
        }
    
    def _generate_segment_answer_explanation(self, segment, knowledge) -> str:
        """Generate an explanation of how this segment answers the question."""
        # Simple template-based explanation
        return f"该视频片段（{segment.start_time} - {segment.end_time}）讲解了{knowledge.title}的相关内容。{segment.segment_description}"
    
    def _merge_video_segments(
        self, 
        context_segments: List[Dict], 
        global_segments: List[Dict], 
        max_results: int
    ) -> List[Dict]:
        """Merge context and global search results, avoiding duplicates."""
        merged = context_segments.copy()
        context_segment_ids = {seg["segment_id"] for seg in context_segments}
        
        for global_seg in global_segments:
            if global_seg["segment_id"] not in context_segment_ids:
                merged.append(global_seg)
                if len(merged) >= max_results:
                    break
        
        return merged[:max_results]
    
    def _generate_answer_from_segments(self, question: str, video_segments: List[Dict]) -> str:
        """Generate a comprehensive answer based on video segments."""
        if not video_segments:
            return "未找到相关的视频内容来回答这个问题。"
        
        # Use LLM to generate comprehensive answer
        try:
            answer_prompt = self._build_answer_generation_prompt(question, video_segments)
            llm_response = self._call_llm(answer_prompt)
            
            if llm_response:
                # Extract answer from LLM response
                answer = self._parse_answer_response(llm_response)
                if answer:
                    return answer
            
            # Fallback: simple concatenation
            segment_descriptions = [seg["segment_description"] for seg in video_segments]
            return f"基于找到的视频内容：{' '.join(segment_descriptions[:3])}"
            
        except Exception as e:
            logger.error(f"Error generating answer from segments: {str(e)}")
            return "找到了相关视频内容，但无法生成完整答案。请查看具体的视频片段。"
    
    def _build_question_breakdown_prompt(self, user_question: str) -> str:
        """Build prompt for question breakdown."""
        prompt = f"""# 问题分解任务

请将下面的复杂问题分解为2-4个更简单的子问题，每个子问题应该关注一个特定的知识点或概念。

## 用户问题
"{user_question}"

## 分解要求
1. 识别问题中涉及的主要概念和知识点
2. 将复杂问题分解为可独立回答的子问题
3. 为每个子问题确定其关注的知识领域
4. 提取相关的关键词

## 输出格式
请严格按照以下JSON格式输出：

```json
{{
  "question_breakdowns": [
    {{
      "sub_question": "具体的子问题",
      "knowledge_focus": "该子问题关注的知识领域",
      "knowledge_keywords": ["关键词1", "关键词2", "关键词3"]
    }}
  ]
}}
```

请确保每个子问题都是独立的、可回答的，并且合在一起能够完整回答原问题。"""
        
        return prompt
    
    def _build_answer_generation_prompt(self, question: str, video_segments: List[Dict]) -> str:
        """Build prompt for generating comprehensive answers."""
        # Format video segments information
        segments_info = []
        for i, seg in enumerate(video_segments, 1):
            segments_info.append(
                f"{i}. 视频：{seg['video_resource']['title']}\n"
                f"   时间：{seg['time_range']['start_time']} - {seg['time_range']['end_time']}\n"
                f"   知识点：{seg['knowledge_point']['title']}\n"
                f"   内容：{seg['segment_description']}\n"
                f"   相关性：{seg['relevance_score']}"
            )
        
        segments_text = "\n\n".join(segments_info)
        
        prompt = f"""# 基于视频内容的问题回答任务

## 用户问题
"{question}"

## 相关视频片段
{segments_text}

## 任务要求
基于上述视频片段的内容，为用户问题提供一个综合性的答案。请：

1. 整合多个视频片段的信息
2. 按逻辑顺序组织答案
3. 使用清晰、易懂的语言
4. 保持答案的准确性和完整性
5. 适当引用具体的视频片段

## 输出格式
请直接输出答案内容，不需要JSON格式。答案应该：
- 开门见山回答问题
- 有条理地展开解释
- 总结关键要点
- 长度控制在200-300字"""
        
        return prompt
    
    def _parse_question_breakdown_response(self, llm_response: str) -> List[Dict]:
        """Parse LLM response for question breakdown."""
        try:
            import re
            
            # Extract JSON from response
            json_match = re.search(r'```json\s*\n(.*?)\n```', llm_response, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                json_match = re.search(r'\{.*\}', llm_response, re.DOTALL)
                if json_match:
                    json_str = json_match.group(0)
                else:
                    raise ValueError("No JSON found in response")
            
            parsed_data = json.loads(json_str)
            breakdowns = parsed_data.get("question_breakdowns", [])
            
            # Validate structure
            for breakdown in breakdowns:
                required_fields = ["sub_question", "knowledge_focus", "knowledge_keywords"]
                for field in required_fields:
                    if field not in breakdown:
                        raise ValueError(f"Missing field: {field}")
            
            return breakdowns
            
        except Exception as e:
            logger.error(f"Error parsing question breakdown response: {str(e)}")
            return []
    
    def _parse_answer_response(self, llm_response: str) -> str:
        """Parse LLM response for answer generation."""
        try:
            # Simply return the response as the answer
            # Remove any markdown formatting or extra whitespace
            answer = llm_response.strip()
            
            # Remove code block markers if present
            if answer.startswith("```") and answer.endswith("```"):
                lines = answer.split("\n")
                answer = "\n".join(lines[1:-1])
            
            return answer
            
        except Exception as e:
            logger.error(f"Error parsing answer response: {str(e)}")
            return llm_response
    
    def _call_llm(self, prompt: str) -> str:
        """Call LLM with the given prompt."""
        try:
            from agents.selector import SmartModelSelector
            from agno.models.message import Message
            import asyncio
            
            model_selector = SmartModelSelector()
            messages = [Message(content=prompt, role="user")]
            
            # Handle event loop
            try:
                loop = asyncio.get_event_loop()
                if loop.is_closed():
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            result = loop.run_until_complete(model_selector.get_response(messages))
            
            if result and len(result) == 2:
                response, model_name = result
                llm_response = response.content if response else ""
                logger.info(f"LLM response from {model_name}: {len(llm_response)} characters")
                return llm_response
            
            return ""
            
        except Exception as e:
            logger.error(f"Error calling LLM: {str(e)}")
            return ""