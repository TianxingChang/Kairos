from typing import Optional
import logging

logger = logging.getLogger(__name__)

async def _extract_transcript_with_ytdlp_safe(
    video_url: str,
    preferred_language: Optional[str] = "en"
) -> Optional[str]:
    """
    使用yt-dlp从视频URL提取字幕内容 - 安全版本
    添加了互斥锁防止内存双重释放问题
    """
    import tempfile
    import os
    import yt_dlp
    import threading
    
    # 全局锁防止并发问题
    _ytdlp_lock = threading.Lock()
    
    try:
        # 创建临时目录来保存字幕文件
        with tempfile.TemporaryDirectory() as temp_dir:
            logger.info(f"Extracting subtitles from {video_url} using yt-dlp (safe mode)")
            logger.info(f"Temporary directory: {temp_dir}")
            
            # 配置yt-dlp选项 - 更安全的配置
            ydl_opts = {
                'skip_download': True,
                'writesubtitles': True,
                'writeautomaticsub': True,
                'subtitleslangs': [preferred_language, 'en', 'zh-Hans', 'zh-TW', 'zh'],
                'outtmpl': os.path.join(temp_dir, '%(title)s.%(ext)s'),
                'quiet': True,
                'no_warnings': True,
                'ignoreerrors': True,
                'concurrent_fragment_downloads': 1,
                'retries': 1,  # 减少重试
                'fragment_retries': 0,  # 禁用片段重试
                'abort_on_unavailable_fragment': False,
                'extract_flat': False,
            }
            
            # 使用锁保护yt-dlp操作
            with _ytdlp_lock:
                try:
                    logger.info(f"Getting video info for {video_url}")
                    
                    # 分步操作，先获取信息
                    with yt_dlp.YoutubeDL({'quiet': True, 'no_warnings': True}) as info_ydl:
                        info = info_ydl.extract_info(video_url, download=False)
                        
                    if not info:
                        logger.error(f"Could not extract video info for {video_url}")
                        return None
                        
                    video_title = info.get('title', 'video')
                    logger.info(f"Video title: {video_title}")
                    
                    # 检查可用字幕
                    subtitles_available = False
                    if info.get('subtitles'):
                        logger.info(f"Manual subtitles available: {list(info['subtitles'].keys())}")
                        subtitles_available = True
                    if info.get('automatic_captions'):
                        logger.info(f"Automatic captions available: {list(info['automatic_captions'].keys())}")
                        subtitles_available = True
                    
                    if not subtitles_available:
                        logger.warning(f"No subtitles or captions available for {video_url}")
                        return None
                    
                    # 单独下载字幕
                    logger.info(f"Downloading subtitles for {video_url}")
                    with yt_dlp.YoutubeDL(ydl_opts) as download_ydl:
                        download_ydl.download([video_url])
                    
                    # 查找生成的字幕文件
                    logger.info("Searching for subtitle files")
                    subtitle_files = []
                    for file in os.listdir(temp_dir):
                        if file.endswith(('.vtt', '.srt', '.ass', '.ttml')):
                            subtitle_files.append(file)
                            logger.info(f"Found subtitle file: {file}")
                    
                    if not subtitle_files:
                        logger.warning(f"No subtitle files found in {temp_dir}")
                        logger.info(f"All files in temp dir: {os.listdir(temp_dir)}")
                        return None
                    
                    # 选择首选语言的字幕文件
                    preferred_file = None
                    for file in subtitle_files:
                        if preferred_language in file.lower():
                            preferred_file = file
                            break
                    
                    # 如果没有找到首选语言，使用第一个可用的字幕文件
                    if not preferred_file:
                        preferred_file = subtitle_files[0]
                        logger.info(f"Using first available subtitle file: {preferred_file}")
                    
                    subtitle_path = os.path.join(temp_dir, preferred_file)
                    with open(subtitle_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    logger.info(f"Successfully extracted subtitles from {video_url}, content length: {len(content)}")
                    return content
                    
                except Exception as e:
                    logger.error(f"yt-dlp extraction failed for {video_url}: {e}")
                    import traceback
                    logger.error(f"Full traceback: {traceback.format_exc()}")
                    return None
    
    except Exception as e:
        logger.error(f"Failed to extract transcript with yt-dlp (safe mode): {e}")
        import traceback
        logger.error(f"Full traceback: {traceback.format_exc()}")
        return None