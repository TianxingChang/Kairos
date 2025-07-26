"""
文件存储服务
用于管理YouTube转录文本的文件存储
"""

import os
import json
import hashlib
from datetime import datetime
from typing import List, Dict, Optional, Any
from pathlib import Path


class TranscriptFileStorage:
    """转录文本文件存储管理器"""
    
    def __init__(self, base_path: str = "/app/data/transcripts"):
        """
        初始化文件存储管理器
        
        Args:
            base_path: 基础存储路径
        """
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
        
        # 文件格式配置
        self.file_extension = ".json"
        self.encoding = "utf-8"
    
    def get_file_path(self, video_id: str) -> str:
        """
        获取视频转录文件的完整路径
        
        Args:
            video_id: YouTube视频ID
            
        Returns:
            文件完整路径
        """
        # 使用视频ID的前两个字符作为子目录，避免单目录文件过多
        subdir = video_id[:2] if len(video_id) >= 2 else "misc"
        file_path = self.base_path / subdir / f"{video_id}{self.file_extension}"
        
        # 确保子目录存在
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        return str(file_path)
    
    def get_relative_path(self, video_id: str) -> str:
        """
        获取相对于基础路径的文件路径（用于数据库存储）
        
        Args:
            video_id: YouTube视频ID
            
        Returns:
            相对路径
        """
        full_path = self.get_file_path(video_id)
        return os.path.relpath(full_path, self.base_path)
    
    def save_transcript(self, video_id: str, transcript_data: List[Dict], metadata: Optional[Dict] = None) -> str:
        """
        保存转录文本到文件
        
        Args:
            video_id: YouTube视频ID
            transcript_data: 转录文本数据列表
            metadata: 可选的元数据
            
        Returns:
            相对文件路径
        """
        file_path = self.get_file_path(video_id)
        
        # 准备文件内容
        file_content = {
            "video_id": video_id,
            "created_at": datetime.utcnow().isoformat(),
            "segment_count": len(transcript_data),
            "metadata": metadata or {},
            "transcript": transcript_data
        }
        
        # 写入文件
        with open(file_path, 'w', encoding=self.encoding) as f:
            json.dump(file_content, f, ensure_ascii=False, indent=2)
        
        return self.get_relative_path(video_id)
    
    def load_transcript(self, video_id: str) -> Optional[Dict]:
        """
        从文件加载转录文本
        
        Args:
            video_id: YouTube视频ID
            
        Returns:
            转录文本数据，如果文件不存在返回None
        """
        file_path = self.get_file_path(video_id)
        
        if not os.path.exists(file_path):
            return None
        
        try:
            with open(file_path, 'r', encoding=self.encoding) as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            print(f"读取转录文件失败 {file_path}: {e}")
            return None
    
    def load_transcript_by_path(self, relative_path: str) -> Optional[Dict]:
        """
        通过相对路径加载转录文本
        
        Args:
            relative_path: 相对于base_path的路径
            
        Returns:
            转录文本数据，如果文件不存在返回None
        """
        full_path = self.base_path / relative_path
        
        if not os.path.exists(full_path):
            return None
        
        try:
            with open(full_path, 'r', encoding=self.encoding) as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            print(f"读取转录文件失败 {full_path}: {e}")
            return None
    
    def file_exists(self, video_id: str) -> bool:
        """
        检查转录文件是否存在
        
        Args:
            video_id: YouTube视频ID
            
        Returns:
            文件是否存在
        """
        file_path = self.get_file_path(video_id)
        return os.path.exists(file_path)
    
    def delete_transcript(self, video_id: str) -> bool:
        """
        删除转录文件
        
        Args:
            video_id: YouTube视频ID
            
        Returns:
            是否删除成功
        """
        file_path = self.get_file_path(video_id)
        
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                
                # 如果子目录为空，删除子目录
                parent_dir = Path(file_path).parent
                if parent_dir != self.base_path and not any(parent_dir.iterdir()):
                    parent_dir.rmdir()
                
                return True
            return False
        except OSError as e:
            print(f"删除转录文件失败 {file_path}: {e}")
            return False
    
    def get_file_info(self, video_id: str) -> Optional[Dict]:
        """
        获取文件信息（大小、修改时间等）
        
        Args:
            video_id: YouTube视频ID
            
        Returns:
            文件信息字典
        """
        file_path = self.get_file_path(video_id)
        
        if not os.path.exists(file_path):
            return None
        
        try:
            stat = os.stat(file_path)
            return {
                "file_path": file_path,
                "relative_path": self.get_relative_path(video_id),
                "size_bytes": stat.st_size,
                "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "created_at": datetime.fromtimestamp(stat.st_ctime).isoformat()
            }
        except OSError as e:
            print(f"获取文件信息失败 {file_path}: {e}")
            return None
    
    def list_all_transcripts(self) -> List[Dict]:
        """
        列出所有转录文件
        
        Returns:
            文件信息列表
        """
        transcript_files = []
        
        for file_path in self.base_path.glob(f"**/*{self.file_extension}"):
            try:
                video_id = file_path.stem
                relative_path = os.path.relpath(file_path, self.base_path)
                
                stat = os.stat(file_path)
                transcript_files.append({
                    "video_id": video_id,
                    "relative_path": relative_path,
                    "size_bytes": stat.st_size,
                    "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat()
                })
            except OSError:
                continue
        
        return sorted(transcript_files, key=lambda x: x["modified_at"], reverse=True)
    
    def cleanup_orphaned_files(self, existing_video_ids: List[str]) -> int:
        """
        清理孤立的转录文件（数据库中不存在对应记录的文件）
        
        Args:
            existing_video_ids: 数据库中存在的视频ID列表
            
        Returns:
            删除的文件数量
        """
        deleted_count = 0
        
        for file_path in self.base_path.glob(f"**/*{self.file_extension}"):
            video_id = file_path.stem
            if video_id not in existing_video_ids:
                try:
                    os.remove(file_path)
                    deleted_count += 1
                    print(f"删除孤立文件: {file_path}")
                except OSError as e:
                    print(f"删除文件失败 {file_path}: {e}")
        
        return deleted_count
    
    def get_storage_stats(self) -> Dict:
        """
        获取存储统计信息
        
        Returns:
            存储统计信息
        """
        total_files = 0
        total_size = 0
        
        for file_path in self.base_path.glob(f"**/*{self.file_extension}"):
            try:
                stat = os.stat(file_path)
                total_files += 1
                total_size += stat.st_size
            except OSError:
                continue
        
        return {
            "total_files": total_files,
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "storage_path": str(self.base_path)
        }


# 全局实例 - 使用本地开发路径
import os
current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
local_data_path = os.path.join(current_dir, "data", "transcripts")
transcript_storage = TranscriptFileStorage(base_path=local_data_path)