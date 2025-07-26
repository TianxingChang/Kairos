#!/usr/bin/env python3
"""
批量同步视频文件和VTT字幕文件到数据库的脚本
将视频文件路径和对应的VTT字幕内容关联存储到learning_resource表中
"""

import os
import sys
import logging
from pathlib import Path
from typing import List, Tuple, Dict
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

# 添加backend目录到Python路径
sys.path.append('/Users/doris/Product🔥/Kairos/backend')

# 加载环境变量
from dotenv import load_dotenv
load_dotenv(dotenv_path="/Users/doris/Product🔥/Kairos/backend/.env")

from db.url import get_db_url
from db.session import SessionLocal

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('sync_video_transcripts.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def find_video_vtt_pairs(base_dirs: List[str]) -> List[Tuple[str, str]]:
    """
    在指定目录中查找视频文件和对应的VTT字幕文件对
    
    Args:
        base_dirs: 要搜索的基础目录列表
        
    Returns:
        List of (video_path, vtt_path) tuples
    """
    pairs = []
    
    for base_dir in base_dirs:
        if not os.path.exists(base_dir):
            logger.warning(f"Directory not found: {base_dir}")
            continue
            
        logger.info(f"Scanning directory: {base_dir}")
        
        # 递归查找所有VTT文件
        for root, dirs, files in os.walk(base_dir):
            vtt_files = [f for f in files if f.endswith('.vtt')]
            
            for vtt_file in vtt_files:
                vtt_path = os.path.join(root, vtt_file)
                
                # 尝试找到对应的视频文件
                # 移除语言标识和.vtt后缀，添加.mp4后缀
                base_name = vtt_file
                for lang_suffix in ['.zh-TW.vtt', '.zh-CN.vtt', '.en.vtt', '.vtt']:
                    if base_name.endswith(lang_suffix):
                        base_name = base_name[:-len(lang_suffix)]
                        break
                
                # 检查可能的视频文件扩展名
                video_extensions = ['.mp4', '.avi', '.mkv', '.mov', '.webm']
                for ext in video_extensions:
                    video_path = os.path.join(root, base_name + ext)
                    if os.path.exists(video_path):
                        pairs.append((video_path, vtt_path))
                        logger.info(f"Found pair: {base_name}{ext} <-> {vtt_file}")
                        break
                else:
                    logger.warning(f"No video file found for VTT: {vtt_file}")
    
    logger.info(f"Total video-VTT pairs found: {len(pairs)}")
    return pairs


def load_vtt_content(vtt_path: str) -> str:
    """
    读取VTT文件内容
    
    Args:
        vtt_path: VTT文件路径
        
    Returns:
        VTT文件内容字符串
    """
    try:
        with open(vtt_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return content
    except Exception as e:
        logger.error(f"Failed to read VTT file {vtt_path}: {e}")
        return ""


def get_video_title_from_path(video_path: str) -> str:
    """
    从视频文件路径提取标题
    
    Args:
        video_path: 视频文件路径
        
    Returns:
        提取的标题
    """
    filename = os.path.basename(video_path)
    title = os.path.splitext(filename)[0]
    return title


def find_existing_resource_by_path(db: Session, video_path: str) -> int:
    """
    通过视频路径查找已存在的资源ID
    
    Args:
        db: 数据库会话
        video_path: 视频文件路径
        
    Returns:
        资源ID，如果不存在返回None
    """
    try:
        # 标准化路径比较
        normalized_path = os.path.normpath(video_path)
        
        result = db.execute(text("""
            SELECT id FROM learning_resource 
            WHERE resource_url = :video_path 
            OR resource_url = :normalized_path
        """), {
            'video_path': video_path,
            'normalized_path': normalized_path
        })
        
        row = result.fetchone()
        return row[0] if row else None
        
    except Exception as e:
        logger.error(f"Failed to find existing resource: {e}")
        return None


def create_or_update_resource(db: Session, video_path: str, vtt_path: str, vtt_content: str) -> bool:
    """
    创建或更新学习资源记录
    
    Args:
        db: 数据库会话
        video_path: 视频文件路径
        vtt_path: VTT文件路径
        vtt_content: VTT文件内容
        
    Returns:
        操作是否成功
    """
    try:
        title = get_video_title_from_path(video_path)
        
        # 检查是否已存在该资源
        existing_id = find_existing_resource_by_path(db, video_path)
        
        if existing_id:
            # 更新现有资源的transcript
            db.execute(text("""
                UPDATE learning_resource 
                SET transcript = :transcript,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = :resource_id
            """), {
                'transcript': vtt_content,
                'resource_id': existing_id
            })
            logger.info(f"Updated existing resource ID {existing_id}: {title}")
            return True
        else:
            # 创建新资源记录
            db.execute(text("""
                INSERT INTO learning_resource 
                (title, resource_type, resource_url, transcript, description, language, is_available)
                VALUES (:title, 'video', :resource_url, :transcript, :description, 'zh-TW', true)
            """), {
                'title': title,
                'resource_url': video_path,
                'transcript': vtt_content,
                'description': f'Video lecture with transcript from {os.path.basename(vtt_path)}'
            })
            logger.info(f"Created new resource: {title}")
            return True
            
    except Exception as e:
        logger.error(f"Failed to create/update resource for {video_path}: {e}")
        return False


def sync_video_transcripts(base_dirs: List[str], dry_run: bool = False) -> Dict[str, int]:
    """
    主函数：同步视频文件和VTT字幕到数据库
    
    Args:
        base_dirs: 要扫描的基础目录列表
        dry_run: 是否只模拟运行不实际更新数据库
        
    Returns:
        统计信息字典
    """
    stats = {
        'pairs_found': 0,
        'successful_updates': 0,
        'failed_updates': 0,
        'skipped': 0
    }
    
    try:
        # 查找视频-VTT对
        logger.info("Starting video-VTT synchronization...")
        pairs = find_video_vtt_pairs(base_dirs)
        stats['pairs_found'] = len(pairs)
        
        if not pairs:
            logger.warning("No video-VTT pairs found!")
            return stats
        
        # 连接数据库
        if not dry_run:
            db = SessionLocal()
        
        # 处理每个视频-VTT对
        for i, (video_path, vtt_path) in enumerate(pairs, 1):
            logger.info(f"Processing {i}/{len(pairs)}: {os.path.basename(video_path)}")
            
            # 读取VTT内容
            vtt_content = load_vtt_content(vtt_path)
            if not vtt_content:
                logger.warning(f"Empty VTT content, skipping: {vtt_path}")
                stats['skipped'] += 1
                continue
            
            if dry_run:
                logger.info(f"[DRY RUN] Would process: {video_path}")
                logger.info(f"[DRY RUN] VTT content length: {len(vtt_content)} characters")
                stats['successful_updates'] += 1
            else:
                try:
                    # 创建或更新数据库记录
                    success = create_or_update_resource(db, video_path, vtt_path, vtt_content)
                    if success:
                        db.commit()  # 每个操作后立即提交
                        stats['successful_updates'] += 1
                        logger.info(f"✅ Successfully processed: {os.path.basename(video_path)}")
                    else:
                        db.rollback()  # 回滚失败的事务
                        stats['failed_updates'] += 1
                except Exception as e:
                    logger.error(f"❌ Exception processing {video_path}: {e}")
                    db.rollback()  # 回滚异常的事务
                    stats['failed_updates'] += 1
        
        # 关闭数据库连接
        if not dry_run:
            db.close()
            logger.info("Database operations completed")
        
    except Exception as e:
        if not dry_run and 'db' in locals():
            db.rollback()
            db.close()
        logger.error(f"Synchronization failed: {e}")
        raise
    
    return stats


def main():
    """主函数"""
    # 环境变量已通过dotenv加载，无需手动设置
    
    # 定义要扫描的目录
    base_directories = [
        '/Users/doris/Product🔥/Kairos/data/firecrawl',
        '/Users/doris/Product🔥/Steep/downloads',  # 如果存在的话
    ]
    
    try:
        logger.info("=" * 60)
        logger.info("Video-VTT Synchronization Script Started")
        logger.info("=" * 60)
        
        # 首先进行干运行，查看会处理什么
        logger.info("Performing dry run...")
        dry_stats = sync_video_transcripts(base_directories, dry_run=True)
        
        logger.info("\nDry run results:")
        logger.info(f"  Pairs found: {dry_stats['pairs_found']}")
        logger.info(f"  Would update: {dry_stats['successful_updates']}")
        logger.info(f"  Would skip: {dry_stats['skipped']}")
        
        # 询问用户是否继续
        if dry_stats['pairs_found'] > 0:
            proceed = input(f"\nProceed with updating {dry_stats['successful_updates']} resources? (y/N): ")
            if proceed.lower() in ['y', 'yes']:
                logger.info("Performing actual synchronization...")
                stats = sync_video_transcripts(base_directories, dry_run=False)
                
                logger.info("\n" + "=" * 60)
                logger.info("SYNCHRONIZATION COMPLETED")
                logger.info("=" * 60)
                logger.info(f"Pairs found: {stats['pairs_found']}")
                logger.info(f"Successful updates: {stats['successful_updates']}")
                logger.info(f"Failed updates: {stats['failed_updates']}")
                logger.info(f"Skipped: {stats['skipped']}")
                
                if stats['failed_updates'] > 0:
                    logger.warning("Some updates failed. Check the log for details.")
                else:
                    logger.info("✅ All video-VTT pairs synchronized successfully!")
            else:
                logger.info("Synchronization cancelled by user.")
        else:
            logger.warning("No video-VTT pairs found. Nothing to synchronize.")
        
    except Exception as e:
        logger.error(f"Script execution failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()