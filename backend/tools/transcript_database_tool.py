"""
集成数据库的字幕分析工具
"""

import json
import re
from typing import Dict, List, Any
from datetime import datetime
from pathlib import Path

from agno.tools import Toolkit
from tools.vtt_parser import VTTTool
from tools.knowledge_extractor import KnowledgeExtractionTool
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.knowledge_service import KnowledgeService, LearningResourceService
from db.session import get_db


class TranscriptDatabaseTool(Toolkit):
    """集成数据库的字幕分析工具"""
    
    def __init__(self):
        self.vtt_tool = VTTTool()
        self.knowledge_tool = KnowledgeExtractionTool()
        
        tools = [self.analyze_and_store_transcript]
        super().__init__(name="transcript_database_tool", tools=tools)
    
    def analyze_and_store_transcript(self, file_path: str, domain: str = "深度学习") -> str:
        """
        分析VTT字幕文件并存储到数据库
        
        Args:
            file_path (str): VTT文件路径
            domain (str): 知识领域，默认"深度学习"
            
        Returns:
            str: 处理结果的JSON字符串
        """
        try:
            # 直接导入数据库模型
            from db.session import SessionLocal
            from db.models import Knowledge, LearningResource
            
            db = SessionLocal()
            
            # Step 1: 解析VTT文件
            vtt_result = self.vtt_tool.parse_vtt_file(file_path)
            
            if not vtt_result["success"]:
                return json.dumps({
                    "success": False,
                    "error": f"Failed to parse VTT file: {vtt_result['error']}",
                    "stored_knowledge_count": 0,
                    "stored_segments_count": 0
                })
            
            # Step 2: 提取知识点
            from tools.vtt_parser import VTTSegment
            segments = []
            for seg_data in vtt_result["segments"]:
                segment = VTTSegment(
                    start_time=seg_data["start_time"],
                    end_time=seg_data["end_time"],
                    text=seg_data["text"],
                    start_seconds=seg_data["start_seconds"],
                    end_seconds=seg_data["end_seconds"]
                )
                segments.append(segment)
            
            analysis_result = self.knowledge_tool.analyze_transcript(segments)
            
            if not analysis_result["success"]:
                return json.dumps({
                    "success": False,
                    "error": f"Knowledge extraction failed: {analysis_result['error']}",
                    "stored_knowledge_count": 0,
                    "stored_segments_count": 0
                })
            
            # Step 3: 创建学习资源记录
            file_name = Path(file_path).name
            video_title = self._extract_video_title(file_name)
            
            # 合并所有segment文本作为transcript
            full_transcript = "\n".join([seg.text for seg in segments])
            
            # 计算总时长（分钟）
            total_duration_minutes = int(vtt_result.get("duration_seconds", 0) / 60)
            
            learning_resource = resource_service.create_or_update_resource(
                title=video_title,
                resource_type="video",
                resource_url=file_path,
                description=analysis_result.get("transcript_summary", ""),
                transcript=full_transcript,
                duration_minutes=total_duration_minutes,
                language="zh"
            )
            
            # Step 4: 处理知识点和片段
            knowledge_segments = analysis_result.get("knowledge_segments", {})
            stored_knowledge = []
            stored_segments = []
            knowledge_ids = []
            
            for concept_name, segment_info in knowledge_segments.items():
                # 查找或创建知识点
                knowledge, is_new = knowledge_service.find_or_create_knowledge(
                    title=concept_name,
                    description=segment_info.get("description", ""),
                    domain=domain,
                    difficulty_level=analysis_result.get("difficulty_level", "中级"),
                    estimated_hours=1,
                    keywords=segment_info.get("keywords", [])
                )
                
                stored_knowledge.append({
                    "id": knowledge.id,
                    "title": knowledge.title,
                    "is_new": is_new
                })
                knowledge_ids.append(knowledge.id)
                
                # 创建视频片段
                start_time = segment_info.get("start", "00:00:00.000")
                end_time = segment_info.get("end", "00:00:00.000")
                
                # 转换时间为秒数
                start_seconds = self._time_to_seconds(start_time)
                end_seconds = self._time_to_seconds(end_time)
                
                video_segment = resource_service.create_video_segment(
                    resource_id=learning_resource.id,
                    knowledge_id=knowledge.id,
                    start_time=start_time,
                    end_time=end_time,
                    start_seconds=start_seconds,
                    end_seconds=end_seconds,
                    segment_title=concept_name,
                    segment_description=segment_info.get("description", ""),
                    importance_level=segment_info.get("importance_level", 3),
                    keywords=segment_info.get("keywords", [])
                )
                
                stored_segments.append({
                    "id": video_segment.id,
                    "knowledge_title": concept_name,
                    "start_time": start_time,
                    "end_time": end_time,
                    "importance_level": segment_info.get("importance_level", 3)
                })
            
            # Step 5: 建立资源与知识点的关联
            if knowledge_ids:
                resource_service.link_resource_to_knowledge(learning_resource.id, knowledge_ids)
            
            # 构建返回结果
            result = {
                "success": True,
                "learning_resource": {
                    "id": learning_resource.id,
                    "title": learning_resource.title,
                    "resource_url": learning_resource.resource_url,
                    "duration_minutes": learning_resource.duration_minutes
                },
                "stored_knowledge_count": len(stored_knowledge),
                "stored_segments_count": len(stored_segments),
                "knowledge_points": stored_knowledge,
                "video_segments": stored_segments,
                "analysis_summary": {
                    "total_duration": analysis_result.get("total_duration", "unknown"),
                    "subject_area": analysis_result.get("subject_area", domain),
                    "difficulty_level": analysis_result.get("difficulty_level", "中级"),
                    "main_topics": analysis_result.get("main_topics", [])
                }
            }
            
            return json.dumps(result, ensure_ascii=False, indent=2)
            
        except Exception as e:
            return json.dumps({
                "success": False,
                "error": f"Unexpected error during transcript analysis and storage: {str(e)}",
                "stored_knowledge_count": 0,
                "stored_segments_count": 0
            })
    
    def _extract_video_title(self, filename: str) -> str:
        """从文件名提取视频标题"""
        # 移除文件扩展名
        title = Path(filename).stem
        
        # 清理常见的模式
        title = re.sub(r'\.zh-TW$', '', title)  # 移除语言标识
        title = re.sub(r'\.vtt$', '', title)    # 移除vtt扩展名
        title = re.sub(r'^DRL Lecture \d+：?\s*', '', title)  # 移除课程编号前缀
        
        return title.strip() or filename
    
    def _time_to_seconds(self, time_str: str) -> int:
        """将时间字符串转换为秒数"""
        try:
            # 格式: "00:01:23.456" 或 "00:01:23"
            parts = time_str.split(':')
            if len(parts) == 3:
                hours = int(parts[0])
                minutes = int(parts[1])
                seconds_part = parts[2].split('.')[0]  # 忽略毫秒
                seconds = int(seconds_part)
                
                return hours * 3600 + minutes * 60 + seconds
            return 0
        except (ValueError, IndexError):
            return 0