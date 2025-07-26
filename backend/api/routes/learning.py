"""Learning resources and video prerequisite analysis API routes."""

import logging
import json
import re
from typing import List, Set
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, HTTPException, status, Depends
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_, text

from config.learning_config import learning_config

from db.session import get_db
from db.models import Knowledge, LearningResource, VideoPrerequisiteHistory
from models.learning import VideoSegment
from services.knowledge_service import KnowledgeService
from api.schemas.learning_schemas import (
    KnowledgeCreate, KnowledgeResponse, KnowledgeWithResources,
    LearningResourceCreate, LearningResourceResponse,
    VideoPrerequisiteRequest, VideoPrerequisiteResponse,
    PrerequisiteKnowledge, PrerequisiteRelationCreate, PrerequisiteRelationBatch
)
from agents.selector import AgentType, get_agent, get_model
from agents.transcript_analyzer import get_transcript_analyzer

logger = logging.getLogger(__name__)

learning_router = APIRouter(prefix="/learning", tags=["Learning Resources"])


@learning_router.post("/knowledge", response_model=KnowledgeResponse)
async def create_knowledge(
    knowledge: KnowledgeCreate,
    db: Session = Depends(get_db)
):
    """创建新的知识点"""
    try:
        # 移除已废弃的字段
        knowledge_data = knowledge.model_dump()
        if 'prerequisites' in knowledge_data:
            del knowledge_data['prerequisites']
        if 'tags' in knowledge_data:
            del knowledge_data['tags']
        
        db_knowledge = Knowledge(**knowledge_data)
        db.add(db_knowledge)
        db.commit()
        db.refresh(db_knowledge)
        return db_knowledge
    except Exception as e:
        logger.error(f"创建知识点失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"创建知识点失败: {str(e)}"
        )


@learning_router.post("/resources", response_model=LearningResourceResponse)
async def create_learning_resource(
    resource: LearningResourceCreate,
    db: Session = Depends(get_db)
):
    """创建新的学习资源"""
    try:
        db_resource = LearningResource(**resource.model_dump())
        db.add(db_resource)
        db.commit()
        db.refresh(db_resource)
        return db_resource
    except Exception as e:
        logger.error(f"创建学习资源失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"创建学习资源失败: {str(e)}"
        )


@learning_router.get("/knowledge", response_model=List[KnowledgeWithResources])
async def list_knowledge(
    domain: str = None,
    difficulty: str = None,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """获取知识点列表"""
    try:
        query = db.query(Knowledge).filter(Knowledge.is_active == True)
        
        if domain:
            query = query.filter(Knowledge.domain == domain)
        if difficulty:
            query = query.filter(Knowledge.difficulty_level == difficulty)
            
        knowledge_list = query.limit(limit).all()
        
        # 转换为响应格式，包含关联的学习资源、标签和前置知识
        result = []
        for k in knowledge_list:
            k_dict = KnowledgeResponse.model_validate(k).model_dump()
            k_dict["resources"] = [
                LearningResourceResponse.model_validate(r).model_dump() 
                for r in k.resources
            ]
            k_dict["tags"] = [
                {"id": t.id, "name": t.name, "description": t.description, "created_at": t.created_at}
                for t in k.tags
            ]
            k_dict["prerequisites"] = [
                KnowledgeResponse.model_validate(p).model_dump()
                for p in k.prerequisites
            ]
            result.append(KnowledgeWithResources(**k_dict))
        
        return result
    except Exception as e:
        logger.error(f"获取知识点列表失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取知识点列表失败: {str(e)}"
        )


@learning_router.post("/video/prerequisites", response_model=VideoPrerequisiteResponse)
async def analyze_video_prerequisites(
    request: VideoPrerequisiteRequest,
    db: Session = Depends(get_db)
):
    """
    分析视频的前置知识需求 - 使用优化后的数据库Schema
    
    改进的流程：
    1. LLM分析视频内容，提取主要知识点
    2. 使用语义搜索匹配数据库中的知识点
    3. 递归查询前置知识图谱
    4. 为每个前置知识点匹配最佳学习资源
    """
    try:
        logger.info(f"开始分析视频前置知识，模型: {request.model_type}")
        
        # 准备分析文本
        analysis_text = ""
        if request.transcript:
            analysis_text = request.transcript
        elif request.video_url:
            # 尝试自动获取YouTube视频转录
            try:
                logger.info(f"尝试自动获取视频转录: {request.video_url}")
                from api.routes.video_segments_safe import _extract_transcript_with_ytdlp_safe
                transcript_result = await _extract_transcript_with_ytdlp_safe(request.video_url)
                if transcript_result and transcript_result.strip():
                    analysis_text = transcript_result
                    logger.info(f"成功获取转录文本，长度: {len(analysis_text)}")
                else:
                    logger.warning("无法获取转录文本，使用URL和标题进行分析")
                    analysis_text = f"视频URL: {request.video_url}"
                    if request.video_title:
                        analysis_text += f"\n视频标题: {request.video_title}"
            except Exception as e:
                logger.warning(f"获取转录失败: {e}，使用URL和标题进行分析")
                analysis_text = f"视频URL: {request.video_url}"
                if request.video_title:
                    analysis_text += f"\n视频标题: {request.video_title}"
        
        if not analysis_text:
            raise ValueError("没有可分析的文本内容")
        
        # 从文本中提取主题
        topic = _extract_topic_from_text(analysis_text, request.video_title)
        logger.info(f"提取的主题: {topic}")
        
        # Step 1: 使用LLM分析视频内容，提取主要知识点
        main_knowledge_points = await _extract_main_knowledge_points(
            analysis_text, request.model_type
        )
        logger.info(f"LLM提取的主要知识点: {main_knowledge_points}")
        
        # Step 2: 语义搜索匹配数据库中的知识点
        matched_knowledge_ids = await _semantic_match_knowledge_points(
            db, main_knowledge_points
        )
        logger.info(f"匹配到的知识点ID: {matched_knowledge_ids}")
        
        # 添加调试信息：显示匹配过程
        if not matched_knowledge_ids:
            logger.warning(f"未匹配到任何知识点！LLM提取的知识点: {main_knowledge_points}")
            # 尝试获取所有知识点的标题进行对比
            all_knowledge = db.query(Knowledge).filter(Knowledge.is_active == True).all()
            all_titles = [k.title for k in all_knowledge]
            logger.info(f"数据库中的所有知识点标题: {all_titles[:20]}...")  # 只显示前20个
        
        # Step 3: 递归查询前置知识图谱
        prerequisite_ids = await _get_prerequisite_knowledge_recursive(
            db, matched_knowledge_ids
        )
        logger.info(f"前置知识点ID: {prerequisite_ids}")
        
        # Step 4: 为每个前置知识点匹配最佳学习资源
        prerequisite_knowledge = await _build_prerequisite_response(
            db, prerequisite_ids
        )
        
        # 计算置信度分数
        confidence_score = _calculate_confidence_score(
            len(main_knowledge_points), len(matched_knowledge_ids), analysis_text
        )
        
        # 保存分析历史
        await _save_analysis_history(
            db=db,
            video_title=request.video_title,
            video_url=request.video_url,
            extracted_knowledge_ids=matched_knowledge_ids,
            prerequisite_knowledge_ids=prerequisite_ids,
            model=request.model_type,
            confidence=confidence_score
        )
        
        response_data = VideoPrerequisiteResponse(
            success=True,
            message=f"成功分析视频前置知识，共识别出 {len(prerequisite_knowledge)} 个前置知识点",
            video_info={
                "title": request.video_title,
                "url": request.video_url,
                "has_transcript": bool(request.transcript or (request.video_url and len(analysis_text) > 100))
            },
            prerequisite_knowledge=prerequisite_knowledge,
            analysis_model=request.model_type,
            confidence_score=confidence_score,
            created_at=datetime.now()
        )
        
        return response_data
        
    except Exception as e:
        logger.error(f"分析视频前置知识失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"分析视频前置知识失败: {str(e)}"
        )


async def _extract_main_knowledge_points(analysis_text: str, model_type: str) -> List[str]:
    """Step 1: 使用LLM提取视频的主要知识点"""
    try:
        # 使用现有的知识图谱Agent，但专门针对主要知识点提取
        agent = get_agent(
            model_id=model_type,
            agent_id=AgentType.KNOWLEDGE_GRAPH_AGENT,
            debug_mode=True
        )
        
        # 优化的prompt，专门用于提取主要知识点
        prompt = f"""
        请分析以下课程内容，仅提取这节课主要讲解的核心知识点（不是前置知识）。
        
        课程内容：
        {analysis_text[:learning_config.analysis_text_max_length]}...
        
        要求：
        1. 只提取本节课直接讲解的主要概念（2-5个）
        2. 使用具体、明确的知识点名称
        3. 避免过于宽泛的概念
        4. 按重要性排序
        5. 每行一个知识点，不要编号
        
        请直接返回知识点列表，每行一个，不要其他格式或解释。
        """
        
        response = await agent.arun(prompt)
        response_text = response.content if hasattr(response, 'content') else str(response)
        
        # 解析LLM返回的知识点列表
        knowledge_points = []
        for line in response_text.strip().split('\n'):
            line = line.strip()
            if line and not line.startswith('#') and not line.startswith('*'):
                # 清理格式
                line = re.sub(r'^[0-9]+\.?\s*', '', line)  # 移除编号
                line = re.sub(r'^[-*]\s*', '', line)  # 移除列表符号
                if len(line) > 3:  # 过滤太短的内容
                    knowledge_points.append(line)
        
        return knowledge_points[:learning_config.max_main_knowledge_points]
        
    except Exception as e:
        logger.error(f"提取主要知识点失败: {e}")
        return []


async def _semantic_match_knowledge_points(db: Session, knowledge_points: List[str]) -> List[int]:
    """Step 2: 使用语义搜索匹配数据库中的知识点"""
    matched_ids = []
    
    logger.info(f"开始匹配知识点，输入: {knowledge_points}")
    
    for point in knowledge_points:
        logger.info(f"正在匹配知识点: '{point}'")
        
        # 策略A: 精确匹配标题
        exact_match = db.query(Knowledge).filter(
            and_(
                Knowledge.is_active == True,
                Knowledge.title.ilike(f"%{point}%")
            )
        ).first()
        
        if exact_match:
            logger.info(f"精确匹配成功: '{point}' -> '{exact_match.title}' (ID: {exact_match.id})")
            matched_ids.append(exact_match.id)
            continue
        
        # 策略B: 搜索关键词匹配（增强版）
        keyword_match = db.query(Knowledge).filter(
            and_(
                Knowledge.is_active == True,
                or_(
                    Knowledge.search_keywords.ilike(f"%{point}%"),
                    Knowledge.description.ilike(f"%{point}%"),
                    # 增加更灵活的匹配：去掉标点符号后匹配
                    Knowledge.title.ilike(f"%{re.sub(r'[^\w\u4e00-\u9fff]', '', point)}%"),
                    Knowledge.search_keywords.ilike(f"%{re.sub(r'[^\w\u4e00-\u9fff]', '', point)}%")
                )
            )
        ).first()
        
        if keyword_match:
            logger.info(f"关键词匹配成功: '{point}' -> '{keyword_match.title}' (ID: {keyword_match.id})")
            matched_ids.append(keyword_match.id)
            continue
        
        # 策略B2: 处理复合技术术语（如"On-policy与Off-policy训练方法"）
        # 提取主要技术关键词
        tech_keywords = []
        if 'policy' in point.lower():
            tech_keywords.extend(['policy', '策略'])
        if 'learning' in point.lower():
            tech_keywords.extend(['learning', '学习'])
        if 'training' in point.lower() or '训练' in point:
            tech_keywords.extend(['training', '训练'])
        if 'reward' in point.lower() or '奖励' in point:
            tech_keywords.extend(['reward', '奖励'])
        
        tech_matched = False
        for keyword in tech_keywords:
            tech_match = db.query(Knowledge).filter(
                and_(
                    Knowledge.is_active == True,
                    or_(
                        Knowledge.title.ilike(f"%{keyword}%"),
                        Knowledge.search_keywords.ilike(f"%{keyword}%")
                    )
                )
            ).first()
            
            if tech_match and tech_match.id not in matched_ids:
                logger.info(f"技术术语匹配成功: '{point}' -> '{tech_match.title}' (ID: {tech_match.id}) via keyword '{keyword}'")
                matched_ids.append(tech_match.id)
                tech_matched = True
                break
        
        if tech_matched:
            continue
        
        # 策略C: 模糊匹配（拆分关键词）
        # 改进的中英文分词处理
        # 1. 先尝试按照常见技术术语分隔符分割
        words = []
        # 按常见分隔符分割（中文顿号、与、和、及等）
        parts = re.split(r'[、，,与和及&\-\s]+', point)
        for part in parts:
            if part.strip():
                words.append(part.strip())
        
        # 2. 如果分割后还是很长，再按照英文单词边界分割
        if not words or max(len(w) for w in words) > 20:
            words.extend(re.findall(r'[A-Za-z]+|[^\x00-\x7F]+', point))
        
        matched_for_this_point = False
        
        logger.info(f"分词结果: {words}")
        for word in words:
            if len(word) > learning_config.min_keyword_length:
                logger.info(f"尝试匹配单词: '{word}'")
                
                fuzzy_match = db.query(Knowledge).filter(
                    and_(
                        Knowledge.is_active == True,
                        or_(
                            Knowledge.title.ilike(f"%{word}%"),
                            Knowledge.search_keywords.ilike(f"%{word}%")
                        )
                    )
                ).first()
                
                if fuzzy_match and fuzzy_match.id not in matched_ids:
                    logger.info(f"模糊匹配成功: '{word}' -> '{fuzzy_match.title}' (ID: {fuzzy_match.id})")
                    matched_ids.append(fuzzy_match.id)
                    matched_for_this_point = True
                    break
        
        if not matched_for_this_point:
            logger.warning(f"未能匹配知识点: '{point}'")
    
    logger.info(f"匹配结果: {len(matched_ids)} 个知识点，ID: {matched_ids}")
    return list(set(matched_ids))  # 去重


async def _get_prerequisite_knowledge_recursive(db: Session, knowledge_ids: List[int]) -> List[int]:
    """Step 3: 递归查询前置知识图谱"""
    all_prerequisites = set()
    to_process = set(knowledge_ids)
    processed = set()
    
    # 递归遍历前置知识
    while to_process:
        current_id = to_process.pop()
        if current_id in processed:
            continue
            
        processed.add(current_id)
        
        # 查询当前知识点的直接前置知识
        current_knowledge = db.query(Knowledge).filter(Knowledge.id == current_id).first()
        if current_knowledge:
            direct_prerequisites = current_knowledge.prerequisites
            for prereq in direct_prerequisites:
                if prereq.id not in processed:
                    all_prerequisites.add(prereq.id)
                    to_process.add(prereq.id)
    
    return list(all_prerequisites)


async def _build_prerequisite_response(db: Session, prerequisite_ids: List[int]) -> List[PrerequisiteKnowledge]:
    """Step 4: 构建前置知识响应，匹配最佳学习资源"""
    prerequisite_knowledge = []
    
    for knowledge_id in prerequisite_ids:
        # 使用eager loading预加载resources关系
        knowledge = db.query(Knowledge).options(joinedload(Knowledge.resources)).filter(Knowledge.id == knowledge_id).first()
        if not knowledge:
            continue
        
        # 获取该知识点的最佳学习资源（按质量评分排序）
        logger.info(f"知识点 '{knowledge.title}' (ID: {knowledge.id}) 的资源数量: {len(knowledge.resources)}")
        for i, r in enumerate(knowledge.resources):
            logger.info(f"  资源 {i+1}: '{r.title}' (可用: {r.is_available}, 质量: {r.quality_score})")
            
        best_resources = sorted(
            [r for r in knowledge.resources if r.is_available],
            key=lambda x: x.quality_score or 0,
            reverse=True
        )[:learning_config.max_best_resources_per_knowledge]
        
        logger.info(f"筛选后的可用资源数量: {len(best_resources)}")
        
        learning_resources = [
            LearningResourceResponse.model_validate(r)
            for r in best_resources
        ]
        
        prerequisite_knowledge.append(PrerequisiteKnowledge(
            knowledge_id=knowledge.id,
            title=knowledge.title,
            description=knowledge.description or f"学习{knowledge.title}的相关知识",
            domain=knowledge.domain,
            estimated_hours=knowledge.estimated_hours,
            learning_resources=learning_resources
        ))
    
    return prerequisite_knowledge


async def _save_analysis_history(
    db: Session,
    video_title: str,
    video_url: str,
    extracted_knowledge_ids: List[int],
    prerequisite_knowledge_ids: List[int],
    model: str,
    confidence: int
):
    """保存分析历史"""
    try:
        history = VideoPrerequisiteHistory(
            video_title=video_title,
            video_url=video_url,
            extracted_knowledge_ids=json.dumps(extracted_knowledge_ids),
            prerequisite_knowledge_ids=json.dumps(prerequisite_knowledge_ids),
            analysis_model=model,
            confidence_score=confidence
        )
        db.add(history)
        db.commit()
        
    except Exception as e:
        logger.error(f"保存分析历史失败: {e}")


def _extract_topic_from_text(text: str, title: str = None) -> str:
    """从文本中提取主题"""
    if title:
        return title
    
    # 简单的主题提取逻辑
    lines = text.split('\n')[:10]
    for line in lines:
        if len(line.strip()) > 10 and len(line.strip()) < 100:
            return line.strip()
    
    return "课程内容分析"


def _calculate_confidence_score(
    extracted_count: int, 
    matched_count: int, 
    analysis_text: str
) -> int:
    """计算分析结果的置信度分数"""
    base_score = learning_config.base_confidence_score
    
    # 根据匹配成功率调整
    if extracted_count > 0:
        match_rate = matched_count / extracted_count
        base_score += int(match_rate * learning_config.match_rate_weight)
    
    # 根据文本长度调整
    if len(analysis_text) > learning_config.long_text_threshold:
        base_score += learning_config.text_length_bonus
    
    # 根据识别出的知识点数量调整
    if matched_count > 0:
        base_score += min(
            matched_count * learning_config.knowledge_count_bonus, 
            learning_config.max_knowledge_count_bonus
        )
    
    return min(base_score, 100)


# 添加新的 Pydantic 模型
from pydantic import BaseModel
from typing import Optional

class TranscriptAnalysisRequest(BaseModel):
    """字幕分析请求模型"""
    file_path: str
    domain: str = "深度学习"
    store_to_database: bool = True
    model_id: Optional[str] = "o3-mini"


@learning_router.post("/transcript/analyze", status_code=status.HTTP_200_OK)
async def analyze_transcript_endpoint(
    request: TranscriptAnalysisRequest,
    db: Session = Depends(get_db)
):
    """
    分析VTT字幕文件并可选择存储到数据库
    """
    try:
        # 获取transcript analyzer
        model = get_model(request.model_id)
        analyzer = get_transcript_analyzer(model=model, debug_mode=True)
        
        # 选择使用哪个工具
        if request.store_to_database:
            # 使用数据库存储工具
            message = f"请使用analyze_and_store_transcript工具分析文件：{request.file_path}，领域：{request.domain}"
        else:
            # 仅分析不存储
            message = f"请使用analyze_transcript工具分析文件：{request.file_path}"
        
        # 运行分析
        response = await analyzer.arun(message, stream=False)
        
        return {"result": response.content}
        
    except Exception as e:
        logger.error(f"字幕分析失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Analysis failed: {str(e)}"
        )


@learning_router.get("/resources/{resource_id}/segments")
async def get_resource_segments_endpoint(
    resource_id: int,
    db: Session = Depends(get_db)
):
    """
    获取特定资源的视频片段
    """
    try:
        # 验证资源存在
        resource = db.query(LearningResource).filter(LearningResource.id == resource_id).first()
        if not resource:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Resource with id {resource_id} not found"
            )
        
        # 获取片段
        segments = db.query(VideoSegment).filter(
            VideoSegment.resource_id == resource_id
        ).order_by(VideoSegment.start_seconds).all()
        
        result = []
        for segment in segments:
            result.append({
                "id": segment.id,
                "start_time": segment.start_time,
                "end_time": segment.end_time,
                "start_seconds": segment.start_seconds,
                "end_seconds": segment.end_seconds,
                "segment_title": segment.segment_title,
                "segment_description": segment.segment_description,
                "importance_level": segment.importance_level,
                "knowledge_title": segment.knowledge.title if segment.knowledge else "Unknown",
                "knowledge_id": segment.knowledge_id
            })
        
        return {
            "resource_id": resource_id,
            "resource_title": resource.title,
            "total_segments": len(result),
            "segments": result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取资源片段失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取资源片段失败: {str(e)}"
        )


@learning_router.get("/knowledge/search")
async def search_knowledge_endpoint(
    query: str,
    domain: str = None,
    limit: int = 20,
    db: Session = Depends(get_db)
):
    """
    搜索知识点
    """
    try:
        knowledge_service = KnowledgeService(db)
        results = knowledge_service.search_knowledge(query, domain, limit)
        
        # 转换为响应格式
        return [
            {
                "id": k.id,
                "title": k.title,
                "description": k.description,
                "domain": k.domain,
                "difficulty_level": k.difficulty_level,
                "estimated_hours": k.estimated_hours,
                "search_keywords": k.search_keywords,
                "created_at": k.created_at,
                "updated_at": k.updated_at
            }
            for k in results
        ]
        
    except Exception as e:
        logger.error(f"搜索知识点失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"搜索知识点失败: {str(e)}"
        )


@learning_router.get("/stats")
async def get_learning_stats(db: Session = Depends(get_db)):
    """
    获取学习系统统计信息
    """
    try:
        knowledge_count = db.query(Knowledge).filter(Knowledge.is_active == True).count()
        resource_count = db.query(LearningResource).filter(LearningResource.is_available == True).count()
        
        # 尝试获取视频片段数量（如果表存在）
        try:
            segment_count = db.query(VideoSegment).count()
        except:
            segment_count = 0
        
        # 按域统计知识点
        try:
            domain_stats = db.query(
                Knowledge.domain,
                db.func.count(Knowledge.id).label('count')
            ).filter(Knowledge.is_active == True).group_by(Knowledge.domain).all()
        except:
            domain_stats = []
        
        # 按类型统计资源
        try:
            resource_type_stats = db.query(
                LearningResource.resource_type,
                db.func.count(LearningResource.id).label('count')
            ).filter(LearningResource.is_available == True).group_by(LearningResource.resource_type).all()
        except:
            resource_type_stats = []
        
        return {
            "total_knowledge_points": knowledge_count,
            "total_resources": resource_count,
            "total_video_segments": segment_count,
            "knowledge_by_domain": [{"domain": domain, "count": count} for domain, count in domain_stats],
            "resources_by_type": [{"type": res_type, "count": count} for res_type, count in resource_type_stats]
        }
        
    except Exception as e:
        logger.error(f"获取统计信息失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取统计信息失败: {str(e)}"
        )


@learning_router.post("/knowledge/prerequisites/add")
async def add_prerequisite_relation(
    relation: PrerequisiteRelationCreate,
    db: Session = Depends(get_db)
):
    """添加单个前置知识关系"""
    try:
        # 验证知识点存在
        knowledge = db.query(Knowledge).filter(Knowledge.id == relation.knowledge_id).first()
        if not knowledge:
            raise HTTPException(status_code=404, detail=f"Knowledge point {relation.knowledge_id} not found")
        
        prerequisite = db.query(Knowledge).filter(Knowledge.id == relation.prerequisite_id).first()
        if not prerequisite:
            raise HTTPException(status_code=404, detail=f"Prerequisite {relation.prerequisite_id} not found")
        
        # 检查关系是否已存在
        existing = db.execute(
            text("SELECT 1 FROM knowledge_prerequisites WHERE knowledge_id = :kid AND prerequisite_id = :pid"),
            {"kid": relation.knowledge_id, "pid": relation.prerequisite_id}
        ).fetchone()
        
        if existing:
            return {"message": "Prerequisite relation already exists", "success": True}
        
        # 添加前置关系
        db.execute(
            text("INSERT INTO knowledge_prerequisites (knowledge_id, prerequisite_id) VALUES (:kid, :pid)"),
            {"kid": relation.knowledge_id, "pid": relation.prerequisite_id}
        )
        db.commit()
        
        logger.info(f"Added prerequisite relation: {knowledge.title} -> {prerequisite.title}")
        
        return {
            "message": f"Successfully added prerequisite relation: {knowledge.title} requires {prerequisite.title}",
            "success": True
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to add prerequisite relation: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to add prerequisite relation: {str(e)}")


@learning_router.post("/knowledge/prerequisites/batch")
async def add_prerequisite_relations_batch(
    batch: PrerequisiteRelationBatch,
    db: Session = Depends(get_db)
):
    """批量添加前置知识关系"""
    try:
        added_count = 0
        skipped_count = 0
        errors = []
        
        for relation in batch.relations:
            try:
                # 验证知识点存在
                knowledge = db.query(Knowledge).filter(Knowledge.id == relation.knowledge_id).first()
                prerequisite = db.query(Knowledge).filter(Knowledge.id == relation.prerequisite_id).first()
                
                if not knowledge or not prerequisite:
                    errors.append(f"Knowledge {relation.knowledge_id} or prerequisite {relation.prerequisite_id} not found")
                    continue
                
                # 检查关系是否已存在
                existing = db.execute(
                    text("SELECT 1 FROM knowledge_prerequisites WHERE knowledge_id = :kid AND prerequisite_id = :pid"),
                    {"kid": relation.knowledge_id, "pid": relation.prerequisite_id}
                ).fetchone()
                
                if existing:
                    skipped_count += 1
                    continue
                
                # 添加前置关系
                db.execute(
                    text("INSERT INTO knowledge_prerequisites (knowledge_id, prerequisite_id) VALUES (:kid, :pid)"),
                    {"kid": relation.knowledge_id, "pid": relation.prerequisite_id}
                )
                added_count += 1
                
            except Exception as e:
                errors.append(f"Failed to add relation {relation.knowledge_id} -> {relation.prerequisite_id}: {str(e)}")
        
        db.commit()
        
        result = {
            "message": f"Batch operation completed. Added: {added_count}, Skipped: {skipped_count}, Errors: {len(errors)}",
            "success": True,
            "added_count": added_count,
            "skipped_count": skipped_count,
            "errors": errors
        }
        
        logger.info(f"Batch prerequisite operation: {result}")
        return result
        
    except Exception as e:
        logger.error(f"Batch prerequisite operation failed: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Batch operation failed: {str(e)}")


@learning_router.get("/knowledge/prerequisites/stats")
async def get_prerequisite_stats(db: Session = Depends(get_db)):
    """获取前置关系统计信息"""
    try:
        # 总的前置关系数
        total_relations = db.execute(text("SELECT COUNT(*) FROM knowledge_prerequisites")).fetchone()[0]
        
        # 有前置关系的知识点数
        knowledge_with_prereqs = db.execute(
            text("SELECT COUNT(DISTINCT knowledge_id) FROM knowledge_prerequisites")
        ).fetchone()[0]
        
        # 被作为前置的知识点数
        prerequisites_used = db.execute(
            text("SELECT COUNT(DISTINCT prerequisite_id) FROM knowledge_prerequisites")
        ).fetchone()[0]
        
        # 示例前置关系
        sample_relations = db.execute(text("""
            SELECT 
                k1.title as knowledge_title,
                k2.title as prerequisite_title
            FROM knowledge_prerequisites kp
            JOIN knowledge k1 ON kp.knowledge_id = k1.id
            JOIN knowledge k2 ON kp.prerequisite_id = k2.id
            ORDER BY k1.title
            LIMIT 5
        """)).fetchall()
        
        return {
            "total_prerequisite_relations": total_relations,
            "knowledge_points_with_prerequisites": knowledge_with_prereqs,
            "knowledge_points_used_as_prerequisites": prerequisites_used,
            "sample_relations": [
                {"knowledge": r.knowledge_title, "prerequisite": r.prerequisite_title}
                for r in sample_relations
            ]
        }
        
    except Exception as e:
        logger.error(f"Failed to get prerequisite stats: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}") 