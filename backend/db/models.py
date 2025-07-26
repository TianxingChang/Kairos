from datetime import datetime
from typing import Optional

from sqlalchemy import Column, DateTime, Integer, String, Text, Float
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class YouTubeVideo(Base):
    """YouTube视频信息表"""
    __tablename__ = "youtube_videos"

    id = Column(Integer, primary_key=True, index=True)
    video_id = Column(String(20), unique=True, index=True, nullable=False)
    title = Column(String(500), nullable=True)
    duration = Column(Float, nullable=True)  # 视频时长（秒）
    upload_date = Column(DateTime, nullable=True)
    channel_name = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    
    # 转录文本文件相关字段
    transcript_file_path = Column(String(500), nullable=True)  # 转录文件相对路径
    transcript_language = Column(String(10), nullable=True)    # 转录语言
    transcript_segment_count = Column(Integer, default=0)      # 转录片段数量
    transcript_file_size = Column(Integer, default=0)         # 文件大小（字节）
    transcript_created_at = Column(DateTime, nullable=True)    # 转录文件创建时间
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# 注意：保留原来的 YouTubeTranscript 表定义以支持数据迁移
# 新的架构中不再使用这个表，但保留以免数据库迁移时出错
class YouTubeTranscript(Base):
    """YouTube转录文本表（已弃用，改用文件存储）"""
    __tablename__ = "youtube_transcripts"

    id = Column(Integer, primary_key=True, index=True)
    video_id = Column(String(20), index=True, nullable=False)
    start_time = Column(Float, nullable=False)  # 开始时间（秒）
    duration = Column(Float, nullable=False)   # 持续时间（秒）
    text = Column(Text, nullable=False)        # 转录文本内容
    language = Column(String(10), default="en") # 语言代码
    created_at = Column(DateTime, default=datetime.utcnow)