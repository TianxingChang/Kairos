import json
import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
from abc import ABC, abstractmethod

from agno.models.openai import OpenAIChat
from tools.vtt_parser import VTTSegment


@dataclass
class KnowledgePoint:
    """Represents a knowledge point with time boundaries."""
    title: str
    description: str
    start_time: str
    end_time: str
    start_seconds: float
    end_seconds: float
    importance_level: int  # 1-5, 5 being most important
    keywords: List[str]
    related_concepts: List[str]


@dataclass
class KnowledgeAnalysisResult:
    """Result of knowledge point extraction."""
    knowledge_points: List[KnowledgePoint]
    summary: str
    total_duration: float
    main_topics: List[str]
    difficulty_level: str
    subject_area: str


class BaseKnowledgeExtractor(ABC):
    """Base class for knowledge extraction."""
    
    @abstractmethod
    def extract_knowledge_points(self, segments: List[VTTSegment]) -> KnowledgeAnalysisResult:
        """Extract knowledge points from VTT segments."""
        pass


class LLMKnowledgeExtractor(BaseKnowledgeExtractor):
    """LLM-based knowledge point extractor."""
    
    def __init__(self, model_id: str = "gpt-4"):
        # 根据 model_id 选择合适的模型
        if model_id == "gemini-2.5-pro":
            from agents.models import GeminiModel
            self.model = GeminiModel()
        elif model_id == "kimi-k2-0711-preview":
            from agents.models import KimiModel
            self.model = KimiModel()
        else:
            from agno.models.openai import OpenAIChat
            self.model = OpenAIChat(id=model_id)
    
    def _create_analysis_prompt(self, full_text: str, duration: float) -> str:
        """Create a prompt for LLM to analyze the transcript."""
        return f"""
作为一位教育专家和内容分析师，请分析以下视频转录文本，提取其中的知识脉络和关键概念。

转录文本：
{full_text[:4000]}  # 限制长度以避免token限制

视频总时长: {duration:.1f}秒

请按照以下格式分析并返回JSON结果：

{{
    "subject_area": "学科领域（如：机器学习、深度学习、强化学习等）",
    "difficulty_level": "难度等级（初级/中级/高级）",
    "main_topics": ["主要话题1", "主要话题2", "主要话题3"],
    "summary": "整体内容摘要",
    "knowledge_segments": [
        {{
            "title": "知识点标题",
            "description": "详细描述",
            "importance_level": 1-5,
            "keywords": ["关键词1", "关键词2"],
            "related_concepts": ["相关概念1", "相关概念2"],
            "estimated_start_percentage": 0.0,  # 估计开始位置（0-100%）
            "estimated_end_percentage": 25.0    # 估计结束位置（0-100%）
        }}
    ]
}}

分析要求：
1. 识别明确的知识点和概念转换
2. 根据内容的逻辑结构划分知识段落
3. 标记每个知识点的重要程度
4. 提取关键术语和概念
5. 估计每个知识点在视频中的大致位置（百分比）
6. 确保知识点划分有逻辑性和连贯性

请只返回JSON格式的结果，不要包含其他解释文字。
"""
    
    def _parse_llm_response(self, response: str, segments: List[VTTSegment], duration: float) -> KnowledgeAnalysisResult:
        """Parse LLM response and convert to KnowledgeAnalysisResult."""
        try:
            # 尝试提取JSON内容
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                response = json_match.group(0)
            
            data = json.loads(response)
            
            knowledge_points = []
            for segment_data in data.get("knowledge_segments", []):
                # 根据百分比计算实际时间
                start_percentage = segment_data.get("estimated_start_percentage", 0) / 100
                end_percentage = segment_data.get("estimated_end_percentage", 100) / 100
                
                start_seconds = duration * start_percentage
                end_seconds = duration * end_percentage
                
                # 转换为时间格式
                start_time = self._seconds_to_time(start_seconds)
                end_time = self._seconds_to_time(end_seconds)
                
                knowledge_point = KnowledgePoint(
                    title=segment_data.get("title", "未知知识点"),
                    description=segment_data.get("description", ""),
                    start_time=start_time,
                    end_time=end_time,
                    start_seconds=start_seconds,
                    end_seconds=end_seconds,
                    importance_level=segment_data.get("importance_level", 3),
                    keywords=segment_data.get("keywords", []),
                    related_concepts=segment_data.get("related_concepts", [])
                )
                knowledge_points.append(knowledge_point)
            
            return KnowledgeAnalysisResult(
                knowledge_points=knowledge_points,
                summary=data.get("summary", ""),
                total_duration=duration,
                main_topics=data.get("main_topics", []),
                difficulty_level=data.get("difficulty_level", "中级"),
                subject_area=data.get("subject_area", "未知领域")
            )
            
        except (json.JSONDecodeError, KeyError) as e:
            # 如果解析失败，返回基础分析结果
            return self._create_fallback_result(segments, duration)
    
    def _create_fallback_result(self, segments: List[VTTSegment], duration: float) -> KnowledgeAnalysisResult:
        """Create a fallback result when LLM parsing fails."""
        # 简单地按时间均分创建知识点
        num_segments = min(5, len(segments) // 10)  # 最多5个段落
        if num_segments == 0:
            num_segments = 1
        
        segment_duration = duration / num_segments
        knowledge_points = []
        
        for i in range(num_segments):
            start_seconds = i * segment_duration
            end_seconds = (i + 1) * segment_duration
            
            knowledge_point = KnowledgePoint(
                title=f"知识点 {i + 1}",
                description="自动生成的知识点",
                start_time=self._seconds_to_time(start_seconds),
                end_time=self._seconds_to_time(end_seconds),
                start_seconds=start_seconds,
                end_seconds=end_seconds,
                importance_level=3,
                keywords=[],
                related_concepts=[]
            )
            knowledge_points.append(knowledge_point)
        
        return KnowledgeAnalysisResult(
            knowledge_points=knowledge_points,
            summary="自动生成的摘要",
            total_duration=duration,
            main_topics=["未识别的主题"],
            difficulty_level="未知",
            subject_area="未知领域"
        )
    
    def _seconds_to_time(self, seconds: float) -> str:
        """Convert seconds to time format HH:MM:SS.mmm."""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millisecs = int((seconds % 1) * 1000)
        
        return f"{hours:02d}:{minutes:02d}:{secs:02d}.{millisecs:03d}"
    
    def extract_knowledge_points(self, segments: List[VTTSegment]) -> KnowledgeAnalysisResult:
        """Extract knowledge points from VTT segments using LLM."""
        if not segments:
            return KnowledgeAnalysisResult(
                knowledge_points=[],
                summary="",
                total_duration=0.0,
                main_topics=[],
                difficulty_level="未知",
                subject_area="未知领域"
            )
        
        # 获取全文和时长
        full_text = ' '.join([segment.text for segment in segments])
        duration = max(segment.end_seconds for segment in segments)
        
        # 创建分析提示
        prompt = self._create_analysis_prompt(full_text, duration)
        
        try:
            # 调用LLM分析
            response = self.model.run(prompt)
            result = self._parse_llm_response(response.content, segments, duration)
            return result
            
        except Exception as e:
            print(f"LLM analysis failed: {e}")
            return self._create_fallback_result(segments, duration)


class KnowledgeExtractionTool:
    """Tool class for integrating knowledge extraction with agents."""
    
    def __init__(self, model_id: str = "gpt-4"):
        self.extractor = LLMKnowledgeExtractor(model_id)
    
    def analyze_transcript(self, segments: List[VTTSegment]) -> dict:
        """Analyze transcript segments and return knowledge structure."""
        try:
            result = self.extractor.extract_knowledge_points(segments)
            
            return {
                "success": True,
                "analysis": {
                    "subject_area": result.subject_area,
                    "difficulty_level": result.difficulty_level,
                    "main_topics": result.main_topics,
                    "summary": result.summary,
                    "total_duration": result.total_duration,
                    "knowledge_segments": {
                        kp.title: {
                            "description": kp.description,
                            "start": kp.start_time,
                            "end": kp.end_time,
                            "start_seconds": kp.start_seconds,
                            "end_seconds": kp.end_seconds,
                            "importance_level": kp.importance_level,
                            "keywords": kp.keywords,
                            "related_concepts": kp.related_concepts
                        }
                        for kp in result.knowledge_points
                    }
                }
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "analysis": {}
            }
    
    def format_for_json_output(self, analysis_result: dict) -> dict:
        """Format analysis result for final JSON output."""
        if not analysis_result.get("success", False):
            return {
                "knowledge_segments": {},
                "transcript_summary": "分析失败",
                "total_duration": "00:00:00.000",
                "error": analysis_result.get("error", "未知错误")
            }
        
        analysis = analysis_result["analysis"]
        duration_seconds = analysis.get("total_duration", 0)
        
        # 转换时长格式
        hours = int(duration_seconds // 3600)
        minutes = int((duration_seconds % 3600) // 60)
        seconds = int(duration_seconds % 60)
        milliseconds = int((duration_seconds % 1) * 1000)
        duration_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}.{milliseconds:03d}"
        
        return {
            "knowledge_segments": analysis.get("knowledge_segments", {}),
            "transcript_summary": analysis.get("summary", ""),
            "total_duration": duration_str,
            "subject_area": analysis.get("subject_area", ""),
            "difficulty_level": analysis.get("difficulty_level", ""),
            "main_topics": analysis.get("main_topics", [])
        }