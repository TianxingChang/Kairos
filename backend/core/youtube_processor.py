import re
from typing import List, Dict, Optional, Tuple
from urllib.parse import urlparse, parse_qs
from datetime import datetime

import requests
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.formatters import TextFormatter


def extract_video_id(youtube_url: str) -> Optional[str]:
    """
    从YouTube URL中提取视频ID
    
    支持的URL格式:
    - https://www.youtube.com/watch?v=VIDEO_ID
    - https://youtu.be/VIDEO_ID
    - https://www.youtube.com/embed/VIDEO_ID
    """
    if not youtube_url:
        return None
    
    # 标准youtube.com URL
    if "youtube.com/watch" in youtube_url:
        parsed_url = urlparse(youtube_url)
        query_params = parse_qs(parsed_url.query)
        return query_params.get('v', [None])[0]
    
    # 短链接 youtu.be
    elif "youtu.be/" in youtube_url:
        parsed_url = urlparse(youtube_url)
        return parsed_url.path.lstrip('/')
    
    # embed URL
    elif "youtube.com/embed/" in youtube_url:
        parsed_url = urlparse(youtube_url)
        return parsed_url.path.split('/')[-1]
    
    # 直接输入视频ID
    elif re.match(r'^[a-zA-Z0-9_-]{11}$', youtube_url):
        return youtube_url
    
    return None


def validate_youtube_url(youtube_url: str) -> bool:
    """验证YouTube URL是否有效"""
    video_id = extract_video_id(youtube_url)
    if not video_id:
        return False
    
    # 简单验证视频ID格式
    return re.match(r'^[a-zA-Z0-9_-]{11}$', video_id) is not None


def get_video_info(video_id: str) -> Optional[Dict]:
    """
    获取YouTube视频基本信息
    注意：这里使用简化的方法，实际项目中建议使用YouTube Data API
    """
    try:
        # 这里可以使用YouTube Data API获取更详细的信息
        # 目前使用简化版本，仅返回基本结构
        return {
            "video_id": video_id,
            "title": None,  # 需要YouTube Data API
            "duration": None,
            "upload_date": None,
            "channel_name": None,
            "description": None
        }
    except Exception as e:
        print(f"获取视频信息失败: {e}")
        return None


def get_youtube_transcript(video_id: str, languages: List[str] = None) -> List[Dict]:
    """
    获取YouTube视频的转录文本（带时间戳）
    
    Args:
        video_id: YouTube视频ID
        languages: 语言列表，默认为['en', 'zh', 'zh-cn']
    
    Returns:
        转录文本列表，每个元素包含：
        {
            'text': '文本内容',
            'start': 开始时间(秒),
            'duration': 持续时间(秒)
        }
    """
    if languages is None:
        languages = ['en', 'zh', 'zh-cn', 'zh-tw']
    
    try:
        # 实例化API对象
        api = YouTubeTranscriptApi()
        
        # 尝试获取转录文本，先尝试指定语言
        transcript_data = None
        language_used = None
        
        for lang in languages:
            try:
                fetched_transcript = api.fetch(video_id, languages=[lang])
                # FetchedTranscript对象本身就包含数据
                transcript_data = list(fetched_transcript)
                language_used = lang
                break
            except:
                continue
        
        # 如果没有找到指定语言，尝试获取英文转录
        if transcript_data is None:
            try:
                fetched_transcript = api.fetch(video_id, languages=['en'])
                transcript_data = list(fetched_transcript)
                language_used = 'en'
            except:
                # 最后尝试获取任何可用的转录
                try:
                    fetched_transcript = api.fetch(video_id)
                    transcript_data = list(fetched_transcript)
                    language_used = 'auto'
                except:
                    return []
        
        # 格式化转录数据
        formatted_transcript = []
        for entry in transcript_data:
            formatted_transcript.append({
                'text': entry.text.strip(),
                'start': entry.start,
                'duration': entry.duration,
                'language': language_used
            })
        
        return formatted_transcript
        
    except Exception as e:
        print(f"获取转录文本失败: {e}")
        return []


def merge_short_segments(transcript: List[Dict], min_duration: float = 2.0) -> List[Dict]:
    """
    合并过短的转录片段以提高可读性
    
    Args:
        transcript: 原始转录数据
        min_duration: 最小片段时长（秒）
    
    Returns:
        合并后的转录数据
    """
    if not transcript:
        return []
    
    merged = []
    current_segment = transcript[0].copy()
    
    for i in range(1, len(transcript)):
        segment = transcript[i]
        
        # 如果当前片段太短，与下一个片段合并
        if current_segment['duration'] < min_duration:
            current_segment['text'] += ' ' + segment['text']
            current_segment['duration'] = segment['start'] + segment['duration'] - current_segment['start']
        else:
            merged.append(current_segment)
            current_segment = segment.copy()
    
    # 添加最后一个片段
    merged.append(current_segment)
    
    return merged