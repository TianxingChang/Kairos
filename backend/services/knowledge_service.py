"""
知识点服务模块
提供知识点相关的业务逻辑和数据访问功能
"""

import json
import re
from typing import List, Optional, Dict, Tuple, Any
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, func
from difflib import SequenceMatcher
import logging

logger = logging.getLogger(__name__)

from db.models import Knowledge, LearningResource
from models.learning import VideoSegment
from db.session import get_db


class KnowledgeService:
    """知识点管理服务"""
    
    def __init__(self, db: Session):
        self.db = db
        
    def find_or_create_knowledge(
        self, 
        title: str, 
        description: str, 
        domain: str = "深度学习",
        difficulty_level: str = "中级",
        estimated_hours: int = 1,
        keywords: List[str] = None
    ) -> Tuple[Knowledge, bool]:
        """
        查找或创建知识点
        
        Returns:
            Tuple[Knowledge, bool]: (知识点对象, 是否新创建)
        """
        # 1. 首先尝试精确匹配标题
        existing = self.db.query(Knowledge).filter(
            Knowledge.title == title,
            Knowledge.domain == domain,
            Knowledge.is_active == True
        ).first()
        
        if existing:
            return existing, False
            
        # 2. 尝试模糊匹配
        similar_knowledge = self._find_similar_knowledge(title, domain, keywords or [])
        if similar_knowledge:
            return similar_knowledge, False
            
        # 3. 创建新知识点
        search_keywords = self._generate_search_keywords(title, description, keywords or [])
        
        new_knowledge = Knowledge(
            title=title,
            description=description,
            domain=domain,
            difficulty_level=difficulty_level,
            estimated_hours=estimated_hours,
            search_keywords=search_keywords,
            is_active=True
        )
        
        self.db.add(new_knowledge)
        self.db.commit()
        self.db.refresh(new_knowledge)
        
        return new_knowledge, True
    
    def _find_similar_knowledge(
        self, 
        title: str, 
        domain: str, 
        keywords: List[str],
        similarity_threshold: float = 0.7
    ) -> Optional[Knowledge]:
        """查找相似的知识点"""
        
        # 获取同领域的所有知识点
        candidates = self.db.query(Knowledge).filter(
            Knowledge.domain == domain,
            Knowledge.is_active == True
        ).all()
        
        best_match = None
        best_score = 0
        
        for candidate in candidates:
            # 计算标题相似度
            title_similarity = SequenceMatcher(None, title.lower(), candidate.title.lower()).ratio()
            
            # 计算关键词重叠度
            candidate_keywords = self._extract_keywords_from_text(candidate.search_keywords or "")
            keyword_overlap = self._calculate_keyword_overlap(keywords, candidate_keywords)
            
            # 综合得分
            combined_score = title_similarity * 0.7 + keyword_overlap * 0.3
            
            if combined_score > best_score and combined_score >= similarity_threshold:
                best_score = combined_score
                best_match = candidate
                
        return best_match
    
    def _calculate_keyword_overlap(self, keywords1: List[str], keywords2: List[str]) -> float:
        """计算关键词重叠度"""
        if not keywords1 or not keywords2:
            return 0.0
            
        set1 = set(k.lower() for k in keywords1)
        set2 = set(k.lower() for k in keywords2)
        
        intersection = len(set1.intersection(set2))
        union = len(set1.union(set2))
        
        return intersection / union if union > 0 else 0.0
    
    def _generate_search_keywords(self, title: str, description: str, keywords: List[str]) -> str:
        """生成搜索关键词"""
        all_keywords = set(keywords)
        
        # 从标题提取关键词
        title_keywords = self._extract_keywords_from_text(title)
        all_keywords.update(title_keywords)
        
        # 从描述提取关键词
        if description:
            desc_keywords = self._extract_keywords_from_text(description)
            all_keywords.update(desc_keywords)
        
        return " ".join(all_keywords)
    
    def _extract_keywords_from_text(self, text: str) -> List[str]:
        """从文本中提取关键词"""
        if not text:
            return []
            
        # 简单的关键词提取（可以用更复杂的NLP方法替换）
        # 移除标点符号，分割单词
        words = re.findall(r'\b\w+\b', text.lower())
        
        # 过滤掉常见停用词
        stop_words = {'的', '是', '在', '和', '与', '或', '但', '因为', '所以', '如果', '那么', '这个', '那个', '一个'}
        keywords = [word for word in words if len(word) > 1 and word not in stop_words]
        
        return list(set(keywords))  # 去重
    
    def search_knowledge(
        self, 
        query: str, 
        domain: str = None, 
        limit: int = 10
    ) -> List[Knowledge]:
        """搜索知识点"""
        
        base_query = self.db.query(Knowledge).filter(Knowledge.is_active == True)
        
        if domain:
            base_query = base_query.filter(Knowledge.domain == domain)
        
        # 构建搜索条件
        search_conditions = []
        
        # 标题匹配
        search_conditions.append(Knowledge.title.ilike(f"%{query}%"))
        
        # 描述匹配
        search_conditions.append(Knowledge.description.ilike(f"%{query}%"))
        
        # 关键词匹配
        search_conditions.append(Knowledge.search_keywords.ilike(f"%{query}%"))
        
        results = base_query.filter(or_(*search_conditions)).limit(limit).all()
        
        return results


def get_l3_atomic_knowledge_points(
    db: Session, 
    domain: Optional[str] = None,
    limit: Optional[int] = None
) -> List[Knowledge]:
    """
    获取L3原子知识点列表，专门用于视频切片分析
    
    Args:
        db: 数据库会话
        domain: 可选的领域过滤
        limit: 可选的数量限制
    
    Returns:
        L3原子知识点列表
    """
    query = db.query(Knowledge).filter(
        and_(
            Knowledge.is_active == True,
            Knowledge.knowledge_level == 'L3'
        )
    )
    
    if domain:
        query = query.filter(Knowledge.domain == domain)
    
    # 按难度和估计时间排序，优先返回核心的原子知识点
    query = query.order_by(
        Knowledge.difficulty_level.asc(),
        Knowledge.estimated_hours.asc(),
        Knowledge.title.asc()
    )
    
    if limit:
        query = query.limit(limit)
    
    l3_points = query.all()
    logger.info(f"Found {len(l3_points)} L3 atomic knowledge points" + 
                (f" in domain '{domain}'" if domain else ""))
    
    return l3_points


def get_knowledge_hierarchy_summary(db: Session) -> Dict[str, Any]:
    """
    获取知识层级结构的汇总信息
    
    Returns:
        包含各层级统计信息的字典
    """
    from sqlalchemy import func
    
    # 按域和层级统计
    hierarchy_stats = db.query(
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
    summary = {
        'total_knowledge_points': db.query(Knowledge).filter(Knowledge.is_active == True).count(),
        'l3_atomic_count': db.query(Knowledge).filter(
            and_(Knowledge.is_active == True, Knowledge.knowledge_level == 'L3')
        ).count(),
        'hierarchy_distribution': []
    }
    
    for stat in hierarchy_stats:
        summary['hierarchy_distribution'].append({
            'domain': stat.domain,
            'level': stat.knowledge_level,
            'count': stat.count
        })
    
    return summary


def validate_knowledge_hierarchy(db: Session) -> Dict[str, Any]:
    """
    验证知识层级结构的完整性
    
    Returns:
        验证结果，包含问题列表和建议
    """
    issues = []
    suggestions = []
    
    # 检查是否有L3知识点没有L2父级
    orphan_l3_count = db.query(Knowledge).filter(
        and_(
            Knowledge.knowledge_level == 'L3',
            Knowledge.parent_knowledge_id.is_(None),
            Knowledge.is_active == True
        )
    ).count()
    
    if orphan_l3_count > 0:
        issues.append(f"发现 {orphan_l3_count} 个L3知识点没有L2父级")
        suggestions.append("为孤立的L3知识点设置正确的L2父级关系")
    
    # 检查是否有域缺少L2层级
    domains_without_l2 = db.query(Knowledge.domain).filter(
        Knowledge.is_active == True
    ).distinct().all()
    
    for (domain,) in domains_without_l2:
        l2_count = db.query(Knowledge).filter(
            and_(
                Knowledge.domain == domain,
                Knowledge.knowledge_level == 'L2',
                Knowledge.is_active == True
            )
        ).count()
        
        if l2_count == 0:
            l3_count = db.query(Knowledge).filter(
                and_(
                    Knowledge.domain == domain,
                    Knowledge.knowledge_level == 'L3',
                    Knowledge.is_active == True
                )
            ).count()
            
            if l3_count > 0:
                issues.append(f"域 '{domain}' 有 {l3_count} 个L3知识点但没有L2层级")
                suggestions.append(f"为域 '{domain}' 添加适当的L2中间层级知识点")
    
    return {
        'is_valid': len(issues) == 0,
        'issues': issues,
        'suggestions': suggestions,
        'orphan_l3_count': orphan_l3_count
    }


class LearningResourceService:
    """学习资源管理服务"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_or_update_resource(
        self,
        title: str,
        resource_type: str,
        resource_url: str,
        description: str = None,
        transcript: str = None,
        duration_minutes: int = None,
        language: str = "zh"
    ) -> LearningResource:
        """创建或更新学习资源"""
        
        # 检查是否已存在相同URL的资源
        existing = self.db.query(LearningResource).filter(
            LearningResource.resource_url == resource_url
        ).first()
        
        if existing:
            # 更新现有资源
            existing.title = title
            existing.description = description
            existing.transcript = transcript
            existing.duration_minutes = duration_minutes
            self.db.commit()
            self.db.refresh(existing)
            return existing
        else:
            # 创建新资源
            new_resource = LearningResource(
                title=title,
                resource_type=resource_type,
                resource_url=resource_url,
                description=description,
                transcript=transcript,
                duration_minutes=duration_minutes,
                language=language,
                is_available=True
            )
            
            self.db.add(new_resource)
            self.db.commit()
            self.db.refresh(new_resource)
            return new_resource
    
    def create_video_segment(
        self,
        resource_id: int,
        knowledge_id: int,
        start_time: str,
        end_time: str,
        start_seconds: int,
        end_seconds: int,
        segment_title: str,
        segment_description: str = None,
        importance_level: int = 3,
        keywords: List[str] = None
    ) -> VideoSegment:
        """创建视频片段"""
        
        segment = VideoSegment(
            resource_id=resource_id,
            knowledge_id=knowledge_id,
            start_time=start_time,
            end_time=end_time,
            start_seconds=start_seconds,
            end_seconds=end_seconds,
            segment_title=segment_title,
            segment_description=segment_description,
            importance_level=importance_level,
            keywords=json.dumps(keywords or [], ensure_ascii=False)
        )
        
        self.db.add(segment)
        self.db.commit()
        self.db.refresh(segment)
        
        return segment
    
    def link_resource_to_knowledge(self, resource_id: int, knowledge_ids: List[int]):
        """将资源链接到知识点"""
        
        resource = self.db.query(LearningResource).filter(
            LearningResource.id == resource_id
        ).first()
        
        if not resource:
            raise ValueError(f"Resource with id {resource_id} not found")
        
        # 获取知识点
        knowledge_points = self.db.query(Knowledge).filter(
            Knowledge.id.in_(knowledge_ids)
        ).all()
        
        # 建立关联
        for knowledge in knowledge_points:
            if knowledge not in resource.knowledge_points:
                resource.knowledge_points.append(knowledge)
        
        self.db.commit()


def get_knowledge_service(db: Session = None) -> KnowledgeService:
    """获取知识点服务实例"""
    if db is None:
        db = next(get_db())
    return KnowledgeService(db)


def get_learning_resource_service(db: Session = None) -> LearningResourceService:
    """获取学习资源服务实例"""
    if db is None:
        db = next(get_db())
    return LearningResourceService(db)