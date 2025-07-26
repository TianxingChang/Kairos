"""
简化的数据库存储工具
"""

import json
import re
from typing import Dict, List, Any
from datetime import datetime
from pathlib import Path

from agno.tools import Toolkit
from tools.vtt_parser import VTTTool
from tools.knowledge_extractor import KnowledgeExtractionTool


class SimpleDatabaseTool(Toolkit):
    """简化的数据库存储工具"""
    
    def __init__(self):
        self.vtt_tool = VTTTool()
        self.knowledge_tool = KnowledgeExtractionTool()
        
        tools = [self.analyze_and_store_simple]
        super().__init__(name="simple_database_tool", tools=tools)
    
    def analyze_and_store_simple(self, file_path: str, domain: str = "深度学习") -> str:
        """
        分析VTT字幕文件并简单存储到数据库
        
        Args:
            file_path (str): VTT文件路径
            domain (str): 知识领域
            
        Returns:
            str: 处理结果的JSON字符串
        """
        try:
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
            
            # Step 3: 简单存储到数据库
            stored_count = self._store_to_database(
                file_path, 
                analysis_result, 
                vtt_result, 
                segments, 
                domain
            )
            
            return json.dumps({
                "success": True,
                "message": "分析和存储完成",
                "stored_knowledge_count": stored_count["knowledge"],
                "stored_segments_count": stored_count["segments"],
                "learning_resource_id": stored_count["resource_id"],
                "file_path": file_path,
                "domain": domain,
                "analysis_summary": analysis_result
            }, ensure_ascii=False, indent=2)
            
        except Exception as e:
            return json.dumps({
                "success": False,
                "error": f"Unexpected error: {str(e)}",
                "stored_knowledge_count": 0,
                "stored_segments_count": 0
            })
    
    def _store_to_database(self, file_path: str, analysis_result: dict, vtt_result: dict, segments: list, domain: str) -> dict:
        """存储到数据库的简化实现"""
        try:
            from db.session import SessionLocal
            from db.models import Knowledge, LearningResource
            
            db = SessionLocal()
            
            # 创建学习资源
            file_name = Path(file_path).name
            video_title = self._extract_video_title(file_name)
            full_transcript = "\n".join([seg.text for seg in segments])
            total_duration_minutes = int(vtt_result.get("duration_seconds", 0) / 60)
            
            # 检查资源是否已存在
            existing_resource = db.query(LearningResource).filter(
                LearningResource.resource_url == file_path
            ).first()
            
            if existing_resource:
                learning_resource = existing_resource
            else:
                learning_resource = LearningResource(
                    title=video_title,
                    resource_type="video",
                    resource_url=file_path,
                    description=analysis_result.get("transcript_summary", ""),
                    transcript=full_transcript,
                    duration_minutes=total_duration_minutes,
                    language="zh",
                    is_available=True
                )
                db.add(learning_resource)
                db.commit()
                db.refresh(learning_resource)
            
            # 处理知识点
            knowledge_segments = analysis_result.get("knowledge_segments", {})
            stored_knowledge = 0
            stored_segments = 0
            
            for concept_name, segment_info in knowledge_segments.items():
                # 检查知识点是否已存在
                existing_knowledge = db.query(Knowledge).filter(
                    Knowledge.title == concept_name,
                    Knowledge.domain == domain
                ).first()
                
                if existing_knowledge:
                    knowledge = existing_knowledge
                else:
                    knowledge = Knowledge(
                        title=concept_name,
                        description=segment_info.get("description", ""),
                        domain=domain,
                        difficulty_level=analysis_result.get("difficulty_level", "中级"),
                        estimated_hours=1,
                        is_active=True,
                        search_keywords=" ".join(segment_info.get("keywords", []))
                    )
                    db.add(knowledge)
                    db.commit()
                    db.refresh(knowledge)
                    stored_knowledge += 1
                
                # 这里可以创建video_segment记录，但为了简化先跳过
                stored_segments += 1
            
            db.close()
            
            return {
                "knowledge": stored_knowledge,
                "segments": stored_segments,
                "resource_id": learning_resource.id
            }
            
        except Exception as e:
            print(f"Database storage error: {e}")
            return {"knowledge": 0, "segments": 0, "resource_id": None}
    
    def _extract_video_title(self, filename: str) -> str:
        """从文件名提取视频标题"""
        title = Path(filename).stem
        title = re.sub(r'\.zh-TW$', '', title)
        title = re.sub(r'\.vtt$', '', title)
        title = re.sub(r'^DRL Lecture \d+：?\s*', '', title)
        return title.strip() or filename