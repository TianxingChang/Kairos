"""
学习资源和知识点数据库模型
"""

from datetime import datetime
from typing import List, Optional
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, Table
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, Mapped
from sqlalchemy.sql import func

Base = declarative_base()

# 多对多关联表
knowledge_resource_association = Table(
    'knowledge_resource_association',
    Base.metadata,
    Column('knowledge_id', Integer, ForeignKey('knowledge.id'), primary_key=True),
    Column('resource_id', Integer, ForeignKey('learning_resource.id'), primary_key=True),
    Column('created_at', DateTime(timezone=True), server_default=func.now())
)


class Knowledge(Base):
    """知识点表"""
    __tablename__ = 'knowledge'
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False, index=True)
    description = Column(Text)
    domain = Column(String(100), nullable=False, index=True)
    difficulty_level = Column(String(20))
    estimated_hours = Column(Integer)
    is_active = Column(Boolean, default=True)
    search_keywords = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # 关系
    resources: Mapped[List["LearningResource"]] = relationship(
        "LearningResource",
        secondary=knowledge_resource_association,
        back_populates="knowledge_points"
    )
    
    def __repr__(self):
        return f"<Knowledge(id={self.id}, title='{self.title}', domain='{self.domain}')>"


class LearningResource(Base):
    """学习资源表"""
    __tablename__ = 'learning_resource'
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    resource_type = Column(String(50), nullable=False, index=True)  # 'video', 'document', 'url' etc.
    resource_url = Column(Text, nullable=False)  # 本地路径或web url
    description = Column(Text)
    transcript = Column(Text)  # 视频的transcript或文档内容
    duration_minutes = Column(Integer)
    language = Column(String(10), default='zh')
    quality_score = Column(Integer)
    is_available = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # 关系
    knowledge_points: Mapped[List["Knowledge"]] = relationship(
        "Knowledge",
        secondary=knowledge_resource_association,
        back_populates="resources"
    )
    
    def __repr__(self):
        return f"<LearningResource(id={self.id}, title='{self.title}', type='{self.resource_type}')>"


class VideoSegment(Base):
    """视频片段表 - 用于存储切割后的视频段"""
    __tablename__ = 'video_segment'
    
    id = Column(Integer, primary_key=True, index=True)
    resource_id = Column(Integer, ForeignKey('learning_resource.id'), nullable=False)
    knowledge_id = Column(Integer, ForeignKey('knowledge.id'), nullable=False)
    
    # 时间信息
    start_time = Column(String(20), nullable=False)  # 格式: "00:01:23.456"
    end_time = Column(String(20), nullable=False)
    start_seconds = Column(Integer, nullable=False)
    end_seconds = Column(Integer, nullable=False)
    
    # 内容信息
    segment_title = Column(String(255), nullable=False)
    segment_description = Column(Text)
    importance_level = Column(Integer, default=3)  # 1-5, 5最重要
    keywords = Column(Text)  # JSON格式存储关键词列表
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # 关系
    resource: Mapped["LearningResource"] = relationship("LearningResource")
    knowledge: Mapped["Knowledge"] = relationship("Knowledge")
    
    def __repr__(self):
        return f"<VideoSegment(id={self.id}, knowledge='{self.knowledge.title if self.knowledge else 'N/A'}', time={self.start_time}-{self.end_time})>"