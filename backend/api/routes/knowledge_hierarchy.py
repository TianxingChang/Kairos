"""
知识层级管理API
提供查看、验证和管理知识层级结构的接口
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import and_, func
from typing import List, Dict, Any
import logging

from db.session import get_db
from db.models import Knowledge
from services.knowledge_service import (
    get_knowledge_hierarchy_summary, 
    validate_knowledge_hierarchy,
    get_l3_atomic_knowledge_points
)
from pydantic import BaseModel

logger = logging.getLogger(__name__)

knowledge_hierarchy_router = APIRouter(prefix="/knowledge-hierarchy", tags=["Knowledge Hierarchy"])


class HierarchyNode(BaseModel):
    """层级节点模型"""
    id: int
    title: str
    description: str
    domain: str
    knowledge_level: str
    difficulty_level: int
    estimated_hours: int
    parent_id: int = None
    children_count: int = 0


class HierarchyStructure(BaseModel):
    """层级结构响应模型"""
    courses: List[HierarchyNode]
    lectures: List[HierarchyNode] 
    knowledge_points: List[HierarchyNode]
    total_counts: Dict[str, int]


class ValidationResult(BaseModel):
    """验证结果模型"""
    is_valid: bool
    issues: List[str]
    suggestions: List[str]
    orphan_l3_count: int
    summary: Dict[str, Any]


@knowledge_hierarchy_router.get("/structure", response_model=HierarchyStructure)
async def get_hierarchy_structure(db: Session = Depends(get_db)):
    """
    获取完整的知识层级结构
    
    Returns:
        包含L1课程、L2讲座、L3知识点的完整层级结构
    """
    try:
        # 获取所有L1课程
        courses = db.query(Knowledge).filter(
            and_(
                Knowledge.knowledge_level == 'L1',
                Knowledge.is_active == True
            )
        ).order_by(Knowledge.domain, Knowledge.title).all()
        
        # 获取所有L2讲座
        lectures = db.query(Knowledge).filter(
            and_(
                Knowledge.knowledge_level == 'L2', 
                Knowledge.is_active == True
            )
        ).order_by(Knowledge.parent_knowledge_id, Knowledge.title).all()
        
        # 获取所有L3知识点
        knowledge_points = db.query(Knowledge).filter(
            and_(
                Knowledge.knowledge_level == 'L3',
                Knowledge.is_active == True
            )
        ).order_by(Knowledge.parent_knowledge_id, Knowledge.title).all()
        
        # 统计每个节点的子节点数量
        def add_children_count(nodes: List[Knowledge], level: str) -> List[HierarchyNode]:
            result = []
            for node in nodes:
                # 统计子节点数量
                if level == 'L1':
                    children_count = db.query(Knowledge).filter(
                        and_(
                            Knowledge.parent_knowledge_id == node.id,
                            Knowledge.is_active == True
                        )
                    ).count()
                elif level == 'L2':
                    children_count = db.query(Knowledge).filter(
                        and_(
                            Knowledge.parent_knowledge_id == node.id,
                            Knowledge.knowledge_level == 'L3',
                            Knowledge.is_active == True
                        )
                    ).count()
                else:
                    children_count = 0
                
                result.append(HierarchyNode(
                    id=node.id,
                    title=node.title,
                    description=node.description or "",
                    domain=node.domain,
                    knowledge_level=node.knowledge_level,
                    difficulty_level=int(node.difficulty_level) if node.difficulty_level else 1,
                    estimated_hours=node.estimated_hours or 0,
                    parent_id=node.parent_knowledge_id,
                    children_count=children_count
                ))
            return result
        
        course_nodes = add_children_count(courses, 'L1')
        lecture_nodes = add_children_count(lectures, 'L2')
        knowledge_point_nodes = add_children_count(knowledge_points, 'L3')
        
        total_counts = {
            'courses': len(course_nodes),
            'lectures': len(lecture_nodes), 
            'knowledge_points': len(knowledge_point_nodes),
            'total_active': len(course_nodes) + len(lecture_nodes) + len(knowledge_point_nodes)
        }
        
        return HierarchyStructure(
            courses=course_nodes,
            lectures=lecture_nodes,
            knowledge_points=knowledge_point_nodes,
            total_counts=total_counts
        )
        
    except Exception as e:
        logger.error(f"Failed to get hierarchy structure: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve hierarchy structure: {str(e)}"
        )


@knowledge_hierarchy_router.get("/validate", response_model=ValidationResult)
async def validate_hierarchy(db: Session = Depends(get_db)):
    """
    验证知识层级结构的完整性和正确性
    
    Returns:
        验证结果，包含发现的问题和改进建议
    """
    try:
        # 使用服务层的验证函数
        validation_result = validate_knowledge_hierarchy(db)
        
        # 获取层级汇总信息
        summary = get_knowledge_hierarchy_summary(db)
        
        return ValidationResult(
            is_valid=validation_result['is_valid'],
            issues=validation_result['issues'],
            suggestions=validation_result['suggestions'],
            orphan_l3_count=validation_result['orphan_l3_count'],
            summary=summary
        )
        
    except Exception as e:
        logger.error(f"Failed to validate hierarchy: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to validate hierarchy: {str(e)}"
        )


@knowledge_hierarchy_router.get("/courses/{course_id}/lectures")
async def get_course_lectures(course_id: int, db: Session = Depends(get_db)):
    """
    获取指定课程的所有讲座
    
    Args:
        course_id: L1课程ID
        
    Returns:
        该课程下的所有L2讲座列表
    """
    try:
        # 验证课程是否存在
        course = db.query(Knowledge).filter(
            and_(
                Knowledge.id == course_id,
                Knowledge.knowledge_level == 'L1',
                Knowledge.is_active == True
            )
        ).first()
        
        if not course:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Course with id {course_id} not found"
            )
        
        # 获取该课程的所有讲座
        lectures = db.query(Knowledge).filter(
            and_(
                Knowledge.parent_knowledge_id == course_id,
                Knowledge.knowledge_level == 'L2',
                Knowledge.is_active == True
            )
        ).order_by(Knowledge.title).all()
        
        # 为每个讲座统计知识点数量
        lecture_data = []
        for lecture in lectures:
            knowledge_point_count = db.query(Knowledge).filter(
                and_(
                    Knowledge.parent_knowledge_id == lecture.id,
                    Knowledge.knowledge_level == 'L3',
                    Knowledge.is_active == True
                )
            ).count()
            
            lecture_data.append({
                "id": lecture.id,
                "title": lecture.title,
                "description": lecture.description,
                "difficulty_level": lecture.difficulty_level,
                "estimated_hours": lecture.estimated_hours,
                "knowledge_point_count": knowledge_point_count
            })
        
        return {
            "course": {
                "id": course.id,
                "title": course.title,
                "domain": course.domain
            },
            "lectures": lecture_data,
            "total_lectures": len(lecture_data)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get course lectures: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve course lectures: {str(e)}"
        )


@knowledge_hierarchy_router.get("/lectures/{lecture_id}/knowledge-points")
async def get_lecture_knowledge_points(lecture_id: int, db: Session = Depends(get_db)):
    """
    获取指定讲座的所有知识点
    
    Args:
        lecture_id: L2讲座ID
        
    Returns:
        该讲座下的所有L3知识点列表
    """
    try:
        # 验证讲座是否存在
        lecture = db.query(Knowledge).filter(
            and_(
                Knowledge.id == lecture_id,
                Knowledge.knowledge_level == 'L2',
                Knowledge.is_active == True
            )
        ).first()
        
        if not lecture:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Lecture with id {lecture_id} not found"
            )
        
        # 获取父课程信息
        course = db.query(Knowledge).filter(
            Knowledge.id == lecture.parent_knowledge_id
        ).first()
        
        # 获取该讲座的所有知识点
        knowledge_points = db.query(Knowledge).filter(
            and_(
                Knowledge.parent_knowledge_id == lecture_id,
                Knowledge.knowledge_level == 'L3',
                Knowledge.is_active == True
            )
        ).order_by(Knowledge.difficulty_level, Knowledge.title).all()
        
        knowledge_point_data = []
        for kp in knowledge_points:
            knowledge_point_data.append({
                "id": kp.id,
                "title": kp.title,
                "description": kp.description,
                "difficulty_level": kp.difficulty_level,
                "estimated_hours": kp.estimated_hours
            })
        
        return {
            "course": {
                "id": course.id if course else None,
                "title": course.title if course else "Unknown Course"
            },
            "lecture": {
                "id": lecture.id,
                "title": lecture.title,
                "description": lecture.description
            },
            "knowledge_points": knowledge_point_data,
            "total_knowledge_points": len(knowledge_point_data)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get lecture knowledge points: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve lecture knowledge points: {str(e)}"
        )


@knowledge_hierarchy_router.get("/l3-atomic-points")
async def get_l3_atomic_points(
    domain: str = None,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """
    获取L3原子知识点列表（专门用于视频切片）
    
    Args:
        domain: 可选的领域过滤
        limit: 结果数量限制
        
    Returns:
        L3原子知识点列表，专门用于视频分析
    """
    try:
        l3_points = get_l3_atomic_knowledge_points(db, domain=domain, limit=limit)
        
        result = []
        for point in l3_points:
            # 获取父讲座和课程信息
            lecture = db.query(Knowledge).filter(
                Knowledge.id == point.parent_knowledge_id
            ).first()
            
            course = None
            if lecture and lecture.parent_knowledge_id:
                course = db.query(Knowledge).filter(
                    Knowledge.id == lecture.parent_knowledge_id
                ).first()
            
            result.append({
                "id": point.id,
                "title": point.title,
                "description": point.description,
                "domain": point.domain,
                "difficulty_level": point.difficulty_level,
                "estimated_hours": point.estimated_hours,
                "lecture": {
                    "id": lecture.id if lecture else None,
                    "title": lecture.title if lecture else "Unknown Lecture"
                },
                "course": {
                    "id": course.id if course else None,
                    "title": course.title if course else "Unknown Course"
                }
            })
        
        return {
            "l3_atomic_points": result,
            "total_count": len(result),
            "filtered_by_domain": domain,
            "usage": "These L3 atomic knowledge points are specifically designed for video segmentation analysis"
        }
        
    except Exception as e:
        logger.error(f"Failed to get L3 atomic points: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve L3 atomic points: {str(e)}"
        )


@knowledge_hierarchy_router.get("/statistics")
async def get_hierarchy_statistics(db: Session = Depends(get_db)):
    """
    获取知识层级的统计信息
    
    Returns:
        详细的层级统计数据
    """
    try:
        # 按域和层级统计
        domain_stats = db.query(
            Knowledge.domain,
            Knowledge.knowledge_level,
            func.count(Knowledge.id).label('count')
        ).filter(
            Knowledge.is_active == True
        ).group_by(
            Knowledge.domain,
            Knowledge.knowledge_level
        ).order_by(
            Knowledge.domain,
            Knowledge.knowledge_level
        ).all()
        
        # 格式化统计结果
        stats_by_domain = {}
        for stat in domain_stats:
            domain = stat.domain
            if domain not in stats_by_domain:
                stats_by_domain[domain] = {'L1': 0, 'L2': 0, 'L3': 0}
            stats_by_domain[domain][stat.knowledge_level] = stat.count
        
        # 总体统计
        total_stats = {
            'total_courses': db.query(Knowledge).filter(
                and_(Knowledge.knowledge_level == 'L1', Knowledge.is_active == True)
            ).count(),
            'total_lectures': db.query(Knowledge).filter(
                and_(Knowledge.knowledge_level == 'L2', Knowledge.is_active == True)
            ).count(),
            'total_knowledge_points': db.query(Knowledge).filter(
                and_(Knowledge.knowledge_level == 'L3', Knowledge.is_active == True)
            ).count(),
            'total_active': db.query(Knowledge).filter(Knowledge.is_active == True).count()
        }
        
        return {
            "domain_statistics": stats_by_domain,
            "total_statistics": total_stats,
            "hierarchy_health": {
                "courses_with_lectures": len([d for d, stats in stats_by_domain.items() if stats['L2'] > 0]),
                "lectures_with_knowledge_points": db.query(Knowledge.id).filter(
                    and_(
                        Knowledge.knowledge_level == 'L2',
                        Knowledge.is_active == True,
                        Knowledge.id.in_(
                            db.query(Knowledge.parent_knowledge_id).filter(
                                and_(Knowledge.knowledge_level == 'L3', Knowledge.is_active == True)
                            ).distinct()
                        )
                    )
                ).count()
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to get hierarchy statistics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve hierarchy statistics: {str(e)}"
        ) 