from typing import Dict, List, Optional
from sqlalchemy.orm import Session

from core.youtube_processor import (
    extract_video_id,
    validate_youtube_url,
    get_video_info,
    get_youtube_transcript,
    merge_short_segments
)
from db.youtube_service import (
    save_video_info,
    save_transcript_to_file,
    get_video_transcript_from_file,
    get_video_info as db_get_video_info
)


class YouTubeTranscriptError(Exception):
    """YouTube转录处理异常"""
    pass


async def process_youtube_url(db: Session, youtube_url: str, merge_segments: bool = True) -> Dict:
    """
    处理YouTube URL，下载转录文本并保存到数据库
    
    Args:
        db: 数据库会话
        youtube_url: YouTube视频URL
        merge_segments: 是否合并短片段
    
    Returns:
        处理结果字典
        {
            'success': bool,
            'video_id': str,
            'message': str,
            'transcript_count': int,
            'video_info': dict
        }
    """
    try:
        # 1. 验证URL并提取视频ID
        if not validate_youtube_url(youtube_url):
            return {
                'success': False,
                'video_id': None,
                'message': '无效的YouTube URL',
                'transcript_count': 0,
                'video_info': None
            }
        
        video_id = extract_video_id(youtube_url)
        if not video_id:
            return {
                'success': False,
                'video_id': None,
                'message': '无法提取视频ID',
                'transcript_count': 0,
                'video_info': None
            }
        
        # 2. 检查数据库中是否已存在转录文本
        existing_transcript = get_video_transcript_from_file(db, video_id)
        if existing_transcript:
            video_info = db_get_video_info(db, video_id)
            return {
                'success': True,
                'video_id': video_id,
                'message': '转录文本已存在',
                'transcript_count': len(existing_transcript),
                'video_info': {
                    'title': video_info.title if video_info else None,
                    'duration': video_info.duration if video_info else None,
                    'channel_name': video_info.channel_name if video_info else None
                }
            }
        
        # 3. 获取视频基本信息
        video_info_data = get_video_info(video_id)
        if video_info_data:
            saved_video = save_video_info(db, video_info_data)
        
        # 4. 获取转录文本
        transcript_data = get_youtube_transcript(video_id)
        if not transcript_data:
            return {
                'success': False,
                'video_id': video_id,
                'message': '无法获取转录文本，该视频可能没有字幕',
                'transcript_count': 0,
                'video_info': video_info_data
            }
        
        # 5. 可选：合并短片段
        if merge_segments:
            transcript_data = merge_short_segments(transcript_data)
        
        # 6. 保存转录文本到文件
        success = save_transcript_to_file(db, video_id, transcript_data)
        if not success:
            return {
                'success': False,
                'video_id': video_id,
                'message': '保存转录文本失败',
                'transcript_count': 0,
                'video_info': video_info_data
            }
        
        return {
            'success': True,
            'video_id': video_id,
            'message': '转录文本处理完成',
            'transcript_count': len(transcript_data),
            'video_info': video_info_data
        }
        
    except Exception as e:
        return {
            'success': False,
            'video_id': video_id if 'video_id' in locals() else None,
            'message': f'处理失败: {str(e)}',
            'transcript_count': 0,
            'video_info': None
        }


async def get_transcript_with_timestamps(db: Session, video_id: str) -> Optional[List[Dict]]:
    """
    获取带时间戳的转录文本
    
    Args:
        db: 数据库会话
        video_id: YouTube视频ID
    
    Returns:
        转录文本列表，包含时间戳信息
    """
    try:
        transcript_data = get_video_transcript_from_file(db, video_id)
        if not transcript_data:
            return None
        
        return [
            {
                'id': i + 1,
                'start_time': segment['start'],
                'duration': segment['duration'],
                'text': segment['text'],
                'language': segment.get('language', 'en'),
                'end_time': segment['start'] + segment['duration']
            }
            for i, segment in enumerate(transcript_data)
        ]
        
    except Exception as e:
        print(f"获取转录文本失败: {e}")
        return None


async def search_in_transcript(db: Session, video_id: str, query: str) -> List[Dict]:
    """
    在转录文本中搜索关键词
    
    Args:
        db: 数据库会话
        video_id: YouTube视频ID
        query: 搜索查询
    
    Returns:
        匹配的转录片段列表
    """
    try:
        from db.youtube_service import search_transcript_by_text
        
        results = search_transcript_by_text(db, video_id, query)
        return results  # 新的函数已经返回正确格式的字典列表
        
    except Exception as e:
        print(f"搜索转录文本失败: {e}")
        return []


async def get_transcript_by_time(db: Session, video_id: str, start_time: float, end_time: float) -> List[Dict]:
    """
    获取指定时间范围的转录文本
    
    Args:
        db: 数据库会话
        video_id: YouTube视频ID
        start_time: 开始时间（秒）
        end_time: 结束时间（秒）
    
    Returns:
        指定时间范围的转录片段列表
    """
    try:
        from db.youtube_service import get_transcript_by_time_range
        
        results = get_transcript_by_time_range(db, video_id, start_time, end_time)
        return results  # 新的函数已经返回正确格式的字典列表
        
    except Exception as e:
        print(f"获取时间范围转录文本失败: {e}")
        return []