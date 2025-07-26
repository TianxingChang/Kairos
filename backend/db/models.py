"""Database models for knowledge and learning resources with optimized schema."""

from datetime import datetime
from typing import List, Optional
from sqlalchemy import (
    Column, Integer, String, Text, DateTime, ForeignKey, Table, Boolean, Float
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, Mapped
from sqlalchemy.sql import func

Base = declarative_base()

# 多对多关系表：知识点与学习资源的关联
knowledge_resource_association = Table(
    'knowledge_resource_association',
    Base.metadata,
    Column('knowledge_id', Integer, ForeignKey('knowledge.id'), primary_key=True),
    Column('resource_id', Integer, ForeignKey('learning_resource.id'), primary_key=True),
    Column('created_at', DateTime(timezone=True), server_default=func.now())
)

# 知识点前置关系表（自引用多对多）
knowledge_prerequisites = Table(
    'knowledge_prerequisites',
    Base.metadata,
    Column('knowledge_id', Integer, ForeignKey('knowledge.id'), primary_key=True),
    Column('prerequisite_id', Integer, ForeignKey('knowledge.id'), primary_key=True),
    Column('created_at', DateTime(timezone=True), server_default=func.now())
)

# 知识点标签关联表
knowledge_tags_association = Table(
    'knowledge_tags',
    Base.metadata,
    Column('knowledge_id', Integer, ForeignKey('knowledge.id'), primary_key=True),
    Column('tag_id', Integer, ForeignKey('tags.id'), primary_key=True),
    Column('created_at', DateTime(timezone=True), server_default=func.now())
)


class Tags(Base):
    """标签表 - 规范化管理标签"""
    
    __tablename__ = "tags"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False, index=True, comment="标签名称")
    description = Column(Text, comment="标签描述")
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # 与知识点的多对多关系
    knowledge_points: Mapped[List["Knowledge"]] = relationship(
        "Knowledge",
        secondary=knowledge_tags_association,
        back_populates="tags"
    )


class Knowledge(Base):
    """知识表 - 存储1小时粒度的知识点"""
    
    __tablename__ = "knowledge"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False, index=True, comment="知识点标题")
    description = Column(Text, comment="知识点详细描述")
    domain = Column(String(100), nullable=False, index=True, comment="知识领域")
    difficulty_level = Column(String(20), default="beginner", comment="难度等级: beginner, intermediate, advanced")
    estimated_hours = Column(Integer, default=1, comment="预计学习时间（小时）")
    is_active = Column(Boolean, default=True, comment="是否激活")
    
    # 层级相关字段
    knowledge_level = Column(String(2), default="L3", comment="知识层级: L1(课程), L2(讲座), L3(知识点)")
    parent_knowledge_id = Column(Integer, ForeignKey('knowledge.id'), comment="父级知识点ID")
    
    # 搜索相关字段 - 暂时不使用向量，先用标准字段
    search_keywords = Column(Text, comment="搜索关键词，用于匹配LLM输出")
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # 与学习资源的多对多关系
    resources: Mapped[List["LearningResource"]] = relationship(
        "LearningResource",
        secondary=knowledge_resource_association,
        back_populates="knowledge_points"
    )
    
    # 前置知识关系（自引用多对多）
    prerequisites: Mapped[List["Knowledge"]] = relationship(
        "Knowledge",
        secondary=knowledge_prerequisites,
        primaryjoin=id == knowledge_prerequisites.c.knowledge_id,
        secondaryjoin=id == knowledge_prerequisites.c.prerequisite_id,
        back_populates="dependent_knowledge"
    )
    
    # 依赖于此知识点的其他知识点
    dependent_knowledge: Mapped[List["Knowledge"]] = relationship(
        "Knowledge", 
        secondary=knowledge_prerequisites,
        primaryjoin=id == knowledge_prerequisites.c.prerequisite_id,
        secondaryjoin=id == knowledge_prerequisites.c.knowledge_id,
        back_populates="prerequisites"
    )
    
    # 与标签的多对多关系
    tags: Mapped[List["Tags"]] = relationship(
        "Tags",
        secondary=knowledge_tags_association,
        back_populates="knowledge_points"
    )


class LearningResource(Base):
    """学习资源表 - 存储学习资源的URL和描述信息"""
    
    __tablename__ = "learning_resource"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False, comment="资源标题")
    resource_type = Column(String(50), nullable=False, index=True, comment="资源类型: video, document, url, local_file")
    resource_url = Column(Text, nullable=False, comment="资源URL或本地路径")
    description = Column(Text, comment="资源描述或内容摘要")
    transcript = Column(Text, comment="视频的转录文本或文档的文本内容")
    duration_minutes = Column(Integer, comment="资源时长（分钟）")
    language = Column(String(10), default="zh-CN", comment="语言")
    quality_score = Column(Integer, default=0, comment="质量评分 0-10")
    is_available = Column(Boolean, default=True, comment="资源是否可用")
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # 与知识点的多对多关系
    knowledge_points: Mapped[List["Knowledge"]] = relationship(
        "Knowledge",
        secondary=knowledge_resource_association,
        back_populates="resources"
    )


class VideoSegment(Base):
    """视频片段表 - 用于存储切割后的视频段"""
    
    __tablename__ = "video_segment"
    
    id = Column(Integer, primary_key=True, index=True)
    resource_id = Column(Integer, ForeignKey('learning_resource.id'), nullable=False)
    knowledge_id = Column(Integer, ForeignKey('knowledge.id'), nullable=False)
    
    # 时间信息
    start_time = Column(String(20), nullable=False, comment="开始时间 格式: HH:MM:SS.mmm")
    end_time = Column(String(20), nullable=False, comment="结束时间 格式: HH:MM:SS.mmm")
    start_seconds = Column(Integer, nullable=False, comment="开始时间秒数")
    end_seconds = Column(Integer, nullable=False, comment="结束时间秒数")
    
    # 内容信息
    segment_title = Column(String(255), nullable=False, comment="片段标题")
    segment_description = Column(Text, comment="片段描述/摘要")
    importance_level = Column(Integer, default=3, comment="重要级别 1-5, 5最重要")
    keywords = Column(Text, comment="关键词列表，JSON格式存储")
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # 关系
    resource: Mapped["LearningResource"] = relationship("LearningResource")
    knowledge: Mapped["Knowledge"] = relationship("Knowledge")


class VideoPrerequisiteHistory(Base):
    """视频前置知识查询历史表"""
    
    __tablename__ = "video_prerequisite_history"
    
    id = Column(Integer, primary_key=True, index=True)
    resource_id = Column(Integer, ForeignKey('learning_resource.id'), nullable=True)
    video_title = Column(String(255), comment="视频标题")
    video_url = Column(Text, comment="视频URL")
    extracted_knowledge_ids = Column(Text, comment="提取的主要知识点ID列表，JSON格式")
    prerequisite_knowledge_ids = Column(Text, comment="前置知识点ID列表，JSON格式")
    analysis_model = Column(String(50), comment="使用的分析模型")
    confidence_score = Column(Integer, default=0, comment="置信度评分 0-100")
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # 关联到学习资源（可选）
    resource: Mapped[Optional["LearningResource"]] = relationship("LearningResource") 