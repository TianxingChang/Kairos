from typing import List, Optional, Dict
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from db.models import YouTubeVideo, YouTubeTranscript
from core.file_storage import transcript_storage


def save_video_info(db: Session, video_data: Dict) -> Optional[YouTubeVideo]:
    """
    保存YouTube视频信息到数据库
    
    Args:
        db: 数据库会话
        video_data: 视频信息字典
    
    Returns:
        保存的视频对象，如果已存在则返回现有对象
    """
    try:
        # 检查视频是否已存在
        existing_video = db.query(YouTubeVideo).filter(
            YouTubeVideo.video_id == video_data['video_id']
        ).first()
        
        if existing_video:
            return existing_video
        
        # 创建新的视频记录
        video = YouTubeVideo(
            video_id=video_data['video_id'],
            title=video_data.get('title'),
            duration=video_data.get('duration'),
            upload_date=video_data.get('upload_date'),
            channel_name=video_data.get('channel_name'),
            description=video_data.get('description')
        )
        
        db.add(video)
        db.commit()
        db.refresh(video)
        
        return video
        
    except IntegrityError:
        db.rollback()
        # 如果出现唯一约束错误，返回现有记录
        return db.query(YouTubeVideo).filter(
            YouTubeVideo.video_id == video_data['video_id']
        ).first()
    except Exception as e:
        db.rollback()
        print(f"保存视频信息失败: {e}")
        return None


def save_transcript_to_file(db: Session, video_id: str, transcript_data: List[Dict]) -> bool:
    """
    保存转录文本到文件，并更新数据库中的文件信息
    
    Args:
        db: 数据库会话
        video_id: YouTube视频ID
        transcript_data: 转录文本数据列表
    
    Returns:
        保存是否成功
    """
    try:
        # 准备元数据
        metadata = {
            "video_id": video_id,
            "language": transcript_data[0].get('language', 'en') if transcript_data else 'en',
            "segment_count": len(transcript_data)
        }
        
        # 保存转录文本到文件
        relative_path = transcript_storage.save_transcript(video_id, transcript_data, metadata)
        
        # 获取文件信息
        file_info = transcript_storage.get_file_info(video_id)
        if not file_info:
            print(f"无法获取文件信息: {video_id}")
            return False
        
        # 更新数据库中的视频记录
        video = db.query(YouTubeVideo).filter(YouTubeVideo.video_id == video_id).first()
        if video:
            video.transcript_file_path = relative_path
            video.transcript_language = metadata['language']
            video.transcript_segment_count = len(transcript_data)
            video.transcript_file_size = file_info['size_bytes']
            video.transcript_created_at = datetime.utcnow()
            video.updated_at = datetime.utcnow()
        else:
            # 如果视频记录不存在，创建新记录
            video = YouTubeVideo(
                video_id=video_id,
                transcript_file_path=relative_path,
                transcript_language=metadata['language'],
                transcript_segment_count=len(transcript_data),
                transcript_file_size=file_info['size_bytes'],
                transcript_created_at=datetime.utcnow()
            )
            db.add(video)
        
        db.commit()
        return True
        
    except Exception as e:
        db.rollback()
        print(f"保存转录文本失败: {e}")
        # 如果数据库操作失败，尝试清理文件
        try:
            transcript_storage.delete_transcript(video_id)
        except:
            pass
        return False


# 保留原函数以兼容现有代码
def save_transcript(db: Session, video_id: str, transcript_data: List[Dict]) -> bool:
    """兼容性函数，重定向到新的文件存储函数"""
    return save_transcript_to_file(db, video_id, transcript_data)


def get_video_transcript_from_file(db: Session, video_id: str) -> Optional[List[Dict]]:
    """
    从文件获取视频的转录文本
    
    Args:
        db: 数据库会话
        video_id: YouTube视频ID
    
    Returns:
        转录文本列表，如果不存在返回None
    """
    try:
        # 首先检查数据库中是否有文件路径
        try:
            video = db.query(YouTubeVideo).filter(YouTubeVideo.video_id == video_id).first()
            if video and video.transcript_file_path:
                # 从文件加载转录文本
                file_data = transcript_storage.load_transcript_by_path(video.transcript_file_path)
                if file_data and 'transcript' in file_data:
                    return file_data['transcript']
        except Exception as db_error:
            print(f"数据库查询失败，回退到直接文件加载: {db_error}")
        
        # 如果数据库中没有文件路径或数据库连接失败，直接尝试加载文件
        file_data = transcript_storage.load_transcript(video_id)
        if file_data and 'transcript' in file_data:
            return file_data['transcript']
        
        return None
        
    except Exception as e:
        print(f"获取转录文本失败: {e}")
        return None


# 保留原函数以兼容现有代码，但现在从文件读取
def get_video_transcript(db: Session, video_id: str) -> List[Dict]:
    """
    兼容性函数，从文件获取转录文本
    
    Returns:
        转录文本字典列表（兼容原有格式）
    """
    transcript_data = get_video_transcript_from_file(db, video_id)
    return transcript_data if transcript_data else []


def get_video_info(db: Session, video_id: str) -> Optional[YouTubeVideo]:
    """
    获取视频信息
    
    Args:
        db: 数据库会话
        video_id: YouTube视频ID
    
    Returns:
        视频信息对象，如果数据库连接失败但有转录文件，返回基本信息
    """
    try:
        return db.query(YouTubeVideo).filter(
            YouTubeVideo.video_id == video_id
        ).first()
    except Exception as db_error:
        print(f"数据库查询视频信息失败: {db_error}")
        
        # 如果数据库连接失败，但有转录文件，创建一个基本的视频信息对象
        if transcript_storage.file_exists(video_id):
            # 创建一个模拟的视频对象（不保存到数据库）
            class MockYouTubeVideo:
                def __init__(self, video_id):
                    self.video_id = video_id
                    self.title = "未知标题"
                    self.duration = None
                    self.channel_name = "未知频道"
                    self.transcript_file_path = None
                    self.created_at = None
                    
            return MockYouTubeVideo(video_id)
        
        return None


def search_transcript_by_text(db: Session, video_id: str, search_text: str) -> List[Dict]:
    """
    在转录文本中搜索特定文本
    
    Args:
        db: 数据库会话
        video_id: YouTube视频ID
        search_text: 搜索的文本
    
    Returns:
        包含搜索文本的转录片段列表
    """
    try:
        transcript_data = get_video_transcript_from_file(db, video_id)
        if not transcript_data:
            return []
        
        # 在转录文本中搜索
        search_results = []
        search_lower = search_text.lower()
        
        for i, segment in enumerate(transcript_data):
            if search_lower in segment.get('text', '').lower():
                # 添加ID字段以兼容原有API
                result_segment = segment.copy()
                result_segment['id'] = i + 1
                result_segment['start_time'] = segment['start']
                result_segment['end_time'] = segment['start'] + segment['duration']
                search_results.append(result_segment)
        
        return search_results
        
    except Exception as e:
        print(f"搜索转录文本失败: {e}")
        return []


def get_transcript_by_time_range(db: Session, video_id: str, start_time: float, end_time: float) -> List[Dict]:
    """
    获取指定时间范围内的转录文本
    
    Args:
        db: 数据库会话
        video_id: YouTube视频ID
        start_time: 开始时间（秒）
        end_time: 结束时间（秒）
    
    Returns:
        指定时间范围内的转录片段列表
    """
    try:
        transcript_data = get_video_transcript_from_file(db, video_id)
        if not transcript_data:
            return []
        
        # 筛选时间范围内的片段
        time_range_results = []
        
        for i, segment in enumerate(transcript_data):
            segment_start = segment.get('start', 0)
            if start_time <= segment_start <= end_time:
                # 添加ID字段以兼容原有API
                result_segment = segment.copy()
                result_segment['id'] = i + 1
                result_segment['start_time'] = segment['start']
                result_segment['end_time'] = segment['start'] + segment['duration']
                time_range_results.append(result_segment)
        
        return time_range_results
        
    except Exception as e:
        print(f"获取时间范围转录文本失败: {e}")
        return []


def get_transcript_file_stats(db: Session) -> Dict:
    """
    获取转录文件的统计信息
    
    Args:
        db: 数据库会话
    
    Returns:
        统计信息字典
    """
    try:
        # 数据库统计
        total_videos = db.query(YouTubeVideo).count()
        videos_with_transcript = db.query(YouTubeVideo).filter(
            YouTubeVideo.transcript_file_path.isnot(None)
        ).count()
        
        # 文件存储统计
        storage_stats = transcript_storage.get_storage_stats()
        
        return {
            "total_videos": total_videos,
            "videos_with_transcript": videos_with_transcript,
            "transcript_coverage": round(videos_with_transcript / total_videos * 100, 2) if total_videos > 0 else 0,
            **storage_stats
        }
        
    except Exception as e:
        print(f"获取统计信息失败: {e}")
        return {}