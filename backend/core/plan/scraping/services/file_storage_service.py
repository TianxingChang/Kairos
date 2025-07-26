"""File storage and organization service for downloaded learning content."""

import json
import shutil
import hashlib
import logging
from typing import Dict, List, Any, Optional, Set, Tuple
from dataclasses import dataclass, field
from pathlib import Path
from datetime import datetime, timezone
from urllib.parse import urlparse
import re

from ..models.learning_resource import CrawledContent, VideoContent, TutorialContent, DiscussionContent


@dataclass
class StorageConfig:
    """Configuration for file storage."""
    
    base_storage_path: Path
    organize_by_topic: bool = True
    organize_by_source: bool = True
    organize_by_date: bool = False
    max_filename_length: int = 100
    generate_thumbnails: bool = True
    create_index_files: bool = True
    backup_metadata: bool = True
    
    def __post_init__(self):
        """Ensure base path is a Path object."""
        if isinstance(self.base_storage_path, str):
            self.base_storage_path = Path(self.base_storage_path)


@dataclass
class StoredItem:
    """Represents a stored learning item with metadata."""
    
    item_id: str
    title: str
    content_type: str  # video, tutorial, discussion
    topic: str
    source_domain: str
    original_url: str
    file_paths: List[str] = field(default_factory=list)
    metadata_path: Optional[str] = None
    storage_date: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    file_size_bytes: int = 0
    checksum: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'item_id': self.item_id,
            'title': self.title,
            'content_type': self.content_type,
            'topic': self.topic,
            'source_domain': self.source_domain,
            'original_url': self.original_url,
            'file_paths': self.file_paths,
            'metadata_path': self.metadata_path,
            'storage_date': self.storage_date.isoformat(),
            'file_size_bytes': self.file_size_bytes,
            'checksum': self.checksum,
            'tags': self.tags
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'StoredItem':
        """Create instance from dictionary."""
        # Parse storage_date
        storage_date = datetime.fromisoformat(data['storage_date'])
        
        return cls(
            item_id=data['item_id'],
            title=data['title'],
            content_type=data['content_type'],
            topic=data['topic'],
            source_domain=data['source_domain'],
            original_url=data['original_url'],
            file_paths=data.get('file_paths', []),
            metadata_path=data.get('metadata_path'),
            storage_date=storage_date,
            file_size_bytes=data.get('file_size_bytes', 0),
            checksum=data.get('checksum'),
            tags=data.get('tags', [])
        )


class FileStorageService:
    """Service for organizing and managing downloaded learning content."""
    
    def __init__(self, config: StorageConfig):
        """Initialize the file storage service.
        
        Args:
            config: Storage configuration
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Storage index
        self._storage_index: Dict[str, StoredItem] = {}
        self._index_file_path = self.config.base_storage_path / "storage_index.json"
        
        # Initialize storage structure
        self._initialize_storage()
        self._load_storage_index()
    
    def _initialize_storage(self):
        """Initialize the storage directory structure."""
        self.config.base_storage_path.mkdir(parents=True, exist_ok=True)
        
        # Create standard subdirectories
        subdirs = ['videos', 'tutorials', 'discussions', 'metadata', 'thumbnails', 'backups']
        
        for subdir in subdirs:
            (self.config.base_storage_path / subdir).mkdir(exist_ok=True)
        
        self.logger.info(f"Initialized storage at: {self.config.base_storage_path}")
    
    def _load_storage_index(self):
        """Load storage index from disk."""
        if self._index_file_path.exists():
            try:
                with open(self._index_file_path, 'r', encoding='utf-8') as f:
                    index_data = json.load(f)
                
                # Convert to StoredItem objects
                for item_id, item_data in index_data.items():
                    self._storage_index[item_id] = StoredItem.from_dict(item_data)
                
                self.logger.info(f"Loaded {len(self._storage_index)} items from storage index")
                
            except Exception as e:
                self.logger.error(f"Failed to load storage index: {e}")
                self._storage_index = {}
        else:
            self.logger.info("No existing storage index found, starting fresh")
    
    def _save_storage_index(self):
        """Save storage index to disk."""
        try:
            # Convert to serializable format
            index_data = {
                item_id: item.to_dict() 
                for item_id, item in self._storage_index.items()
            }
            
            # Create backup if exists
            if self._index_file_path.exists() and self.config.backup_metadata:
                backup_path = self.config.base_storage_path / "backups" / f"storage_index_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                shutil.copy2(self._index_file_path, backup_path)
            
            # Save index
            with open(self._index_file_path, 'w', encoding='utf-8') as f:
                json.dump(index_data, f, indent=2, ensure_ascii=False)
            
            self.logger.debug("Storage index saved successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to save storage index: {e}")
    
    def store_crawled_content(
        self, 
        crawled_content: CrawledContent,
        topic: str,
        downloaded_files: Optional[Dict[str, str]] = None
    ) -> List[StoredItem]:
        """Store crawled content in organized directory structure.
        
        Args:
            crawled_content: The crawled content to store
            topic: Topic/category for organization
            downloaded_files: Optional mapping of URLs to downloaded file paths
            
        Returns:
            List of stored items
        """
        stored_items = []
        
        # Store videos
        for video in crawled_content.videos:
            stored_item = self._store_video_content(video, topic, downloaded_files)
            if stored_item:
                stored_items.append(stored_item)
        
        # Store tutorials
        for tutorial in crawled_content.tutorials:
            stored_item = self._store_tutorial_content(tutorial, topic, crawled_content.url)
            if stored_item:
                stored_items.append(stored_item)
        
        # Store discussions
        for discussion in crawled_content.discussions:
            stored_item = self._store_discussion_content(discussion, topic, crawled_content.url)
            if stored_item:
                stored_items.append(stored_item)
        
        # Update index
        self._save_storage_index()
        
        # Generate summary index if enabled
        if self.config.create_index_files:
            self._generate_topic_index(topic)
        
        self.logger.info(f"Stored {len(stored_items)} items for topic '{topic}'")
        
        return stored_items
    
    def _store_video_content(
        self, 
        video: VideoContent, 
        topic: str,
        downloaded_files: Optional[Dict[str, str]] = None
    ) -> Optional[StoredItem]:
        """Store video content."""
        try:
            # Generate item ID
            item_id = self._generate_item_id(video.url, 'video')
            
            # Check if already stored
            if item_id in self._storage_index:
                self.logger.info(f"Video already stored: {video.title}")
                return self._storage_index[item_id]
            
            # Determine storage path
            storage_dir = self._get_storage_directory('video', topic, video.url)
            storage_dir.mkdir(parents=True, exist_ok=True)
            
            # Generate filename
            filename = self._generate_safe_filename(video.title or "video", item_id, ".json")
            
            # Store metadata
            metadata_path = storage_dir / filename
            video_metadata = {
                'content_type': 'video',
                'title': video.title,
                'url': video.url,
                'duration': video.duration,
                'description': video.description,
                'download_path': video.download_path,
                'thumbnail_url': video.thumbnail_url,
                'file_size_mb': video.file_size_mb,
                'topic': topic,
                'storage_date': datetime.now(timezone.utc).isoformat(),
                'item_id': item_id
            }
            
            with open(metadata_path, 'w', encoding='utf-8') as f:
                json.dump(video_metadata, f, indent=2, ensure_ascii=False)
            
            # Handle downloaded file if provided
            file_paths = []
            file_size = 0
            checksum = None
            
            if downloaded_files and video.url in downloaded_files:
                source_path = Path(downloaded_files[video.url])
                if source_path.exists():
                    # Move file to organized location
                    target_filename = self._generate_safe_filename(
                        video.title or "video", 
                        item_id, 
                        source_path.suffix
                    )
                    target_path = storage_dir / target_filename
                    
                    shutil.move(str(source_path), str(target_path))
                    file_paths.append(str(target_path))
                    
                    # Calculate file info
                    file_size = target_path.stat().st_size
                    checksum = self._calculate_file_checksum(target_path)
            
            # Extract source domain
            source_domain = urlparse(video.url).netloc.lower()
            
            # Create stored item
            stored_item = StoredItem(
                item_id=item_id,
                title=video.title or "Untitled Video",
                content_type="video",
                topic=topic,
                source_domain=source_domain,
                original_url=video.url,
                file_paths=file_paths,
                metadata_path=str(metadata_path),
                file_size_bytes=file_size,
                checksum=checksum,
                tags=self._extract_tags_from_content(video.title, video.description)
            )
            
            # Add to index
            self._storage_index[item_id] = stored_item
            
            return stored_item
            
        except Exception as e:
            self.logger.error(f"Failed to store video content: {e}")
            return None
    
    def _store_tutorial_content(
        self, 
        tutorial: TutorialContent, 
        topic: str,
        source_url: str
    ) -> Optional[StoredItem]:
        """Store tutorial content."""
        try:
            # Generate item ID
            item_id = self._generate_item_id(source_url + tutorial.title, 'tutorial')
            
            # Check if already stored
            if item_id in self._storage_index:
                self.logger.info(f"Tutorial already stored: {tutorial.title}")
                return self._storage_index[item_id]
            
            # Determine storage path
            storage_dir = self._get_storage_directory('tutorial', topic, source_url)
            storage_dir.mkdir(parents=True, exist_ok=True)
            
            # Generate filenames
            base_filename = self._generate_safe_filename(tutorial.title, item_id, "")
            
            # Store tutorial content as markdown
            content_path = storage_dir / f"{base_filename}.md"
            with open(content_path, 'w', encoding='utf-8') as f:
                f.write(f"# {tutorial.title}\n\n")
                f.write(f"**Source:** {source_url}\n")
                f.write(f"**Topic:** {topic}\n")
                f.write(f"**Stored:** {datetime.now(timezone.utc).isoformat()}\n\n")
                f.write("---\n\n")
                f.write(tutorial.content)
                
                # Add code examples section
                if tutorial.code_examples:
                    f.write("\n\n## Code Examples\n\n")
                    for i, code in enumerate(tutorial.code_examples, 1):
                        f.write(f"### Example {i}\n\n")
                        f.write("```\n")
                        f.write(code)
                        f.write("\n```\n\n")
            
            # Store metadata
            metadata_path = storage_dir / f"{base_filename}_metadata.json"
            tutorial_metadata = {
                'content_type': 'tutorial',
                'title': tutorial.title,
                'source_url': source_url,
                'sections': tutorial.sections,
                'code_examples_count': len(tutorial.code_examples),
                'images_count': len(tutorial.images),
                'images': tutorial.images,
                'topic': topic,
                'storage_date': datetime.now(timezone.utc).isoformat(),
                'item_id': item_id,
                'content_file': str(content_path)
            }
            
            with open(metadata_path, 'w', encoding='utf-8') as f:
                json.dump(tutorial_metadata, f, indent=2, ensure_ascii=False)
            
            # Calculate file info
            file_size = content_path.stat().st_size
            checksum = self._calculate_file_checksum(content_path)
            
            # Extract source domain
            source_domain = urlparse(source_url).netloc.lower()
            
            # Create stored item
            stored_item = StoredItem(
                item_id=item_id,
                title=tutorial.title,
                content_type="tutorial",
                topic=topic,
                source_domain=source_domain,
                original_url=source_url,
                file_paths=[str(content_path)],
                metadata_path=str(metadata_path),
                file_size_bytes=file_size,
                checksum=checksum,
                tags=self._extract_tags_from_content(tutorial.title, tutorial.content)
            )
            
            # Add to index
            self._storage_index[item_id] = stored_item
            
            return stored_item
            
        except Exception as e:
            self.logger.error(f"Failed to store tutorial content: {e}")
            return None
    
    def _store_discussion_content(
        self, 
        discussion: DiscussionContent, 
        topic: str,
        source_url: str
    ) -> Optional[StoredItem]:
        """Store discussion content."""
        try:
            # Generate item ID
            item_id = self._generate_item_id(source_url + discussion.title, 'discussion')
            
            # Check if already stored
            if item_id in self._storage_index:
                self.logger.info(f"Discussion already stored: {discussion.title}")
                return self._storage_index[item_id]
            
            # Determine storage path
            storage_dir = self._get_storage_directory('discussion', topic, source_url)
            storage_dir.mkdir(parents=True, exist_ok=True)
            
            # Generate filenames
            base_filename = self._generate_safe_filename(discussion.title, item_id, "")
            
            # Store discussion content as markdown
            content_path = storage_dir / f"{base_filename}.md"
            with open(content_path, 'w', encoding='utf-8') as f:
                f.write(f"# {discussion.title}\n\n")
                f.write(f"**Source:** {source_url}\n")
                f.write(f"**Topic:** {topic}\n")
                f.write(f"**Stored:** {datetime.now(timezone.utc).isoformat()}\n\n")
                f.write("---\n\n")
                
                # Add posts
                if discussion.posts:
                    f.write("## Posts\n\n")
                    for i, post in enumerate(discussion.posts, 1):
                        content = post.get('content', '') if isinstance(post, dict) else str(post)
                        author = post.get('author', 'Unknown') if isinstance(post, dict) else 'Unknown'
                        f.write(f"### Post {i} - {author}\n\n")
                        f.write(f"{content}\n\n")
                
                # Add comments
                if discussion.comments:
                    f.write("## Comments\n\n")
                    for i, comment in enumerate(discussion.comments, 1):
                        content = comment.get('content', '') if isinstance(comment, dict) else str(comment)
                        author = comment.get('author', 'Unknown') if isinstance(comment, dict) else 'Unknown'
                        f.write(f"**Comment {i} - {author}:**\n")
                        f.write(f"{content}\n\n")
                
                # Add Q&A pairs
                if discussion.qa_pairs:
                    f.write("## Q&A Pairs\n\n")
                    for i, qa in enumerate(discussion.qa_pairs, 1):
                        question = qa.get('question', '') if isinstance(qa, dict) else ''
                        answer = qa.get('answer', '') if isinstance(qa, dict) else str(qa)
                        f.write(f"### Q&A {i}\n\n")
                        if question:
                            f.write(f"**Question:** {question}\n\n")
                        f.write(f"**Answer:** {answer}\n\n")
            
            # Store metadata
            metadata_path = storage_dir / f"{base_filename}_metadata.json"
            discussion_metadata = {
                'content_type': 'discussion',
                'title': discussion.title,
                'source_url': source_url,
                'posts_count': len(discussion.posts),
                'comments_count': len(discussion.comments),
                'qa_pairs_count': len(discussion.qa_pairs),
                'topic': topic,
                'storage_date': datetime.now(timezone.utc).isoformat(),
                'item_id': item_id,
                'content_file': str(content_path)
            }
            
            with open(metadata_path, 'w', encoding='utf-8') as f:
                json.dump(discussion_metadata, f, indent=2, ensure_ascii=False)
            
            # Calculate file info
            file_size = content_path.stat().st_size
            checksum = self._calculate_file_checksum(content_path)
            
            # Extract source domain
            source_domain = urlparse(source_url).netloc.lower()
            
            # Create stored item
            stored_item = StoredItem(
                item_id=item_id,
                title=discussion.title,
                content_type="discussion",
                topic=topic,
                source_domain=source_domain,
                original_url=source_url,
                file_paths=[str(content_path)],
                metadata_path=str(metadata_path),
                file_size_bytes=file_size,
                checksum=checksum,
                tags=self._extract_tags_from_content(discussion.title, "")
            )
            
            # Add to index
            self._storage_index[item_id] = stored_item
            
            return stored_item
            
        except Exception as e:
            self.logger.error(f"Failed to store discussion content: {e}")
            return None
    
    def _get_storage_directory(self, content_type: str, topic: str, source_url: str) -> Path:
        """Determine storage directory based on organization preferences."""
        base_dir = self.config.base_storage_path / content_type + "s"  # videos, tutorials, discussions
        
        # Organize by topic
        if self.config.organize_by_topic:
            safe_topic = self._sanitize_directory_name(topic)
            base_dir = base_dir / safe_topic
        
        # Organize by source domain
        if self.config.organize_by_source:
            source_domain = urlparse(source_url).netloc.lower()
            safe_domain = self._sanitize_directory_name(source_domain)
            base_dir = base_dir / safe_domain
        
        # Organize by date
        if self.config.organize_by_date:
            date_dir = datetime.now().strftime("%Y-%m")
            base_dir = base_dir / date_dir
        
        return base_dir
    
    def _generate_item_id(self, content_identifier: str, content_type: str) -> str:
        """Generate unique ID for stored item."""
        # Create hash from content identifier and type
        hasher = hashlib.md5()
        hasher.update(f"{content_type}:{content_identifier}".encode('utf-8'))
        return hasher.hexdigest()[:12]  # Use first 12 characters
    
    def _generate_safe_filename(self, title: str, item_id: str, extension: str) -> str:
        """Generate safe filename from title."""
        # Sanitize title
        safe_title = self._sanitize_filename(title)
        
        # Truncate if too long
        max_title_length = self.config.max_filename_length - len(item_id) - len(extension) - 1
        if len(safe_title) > max_title_length:
            safe_title = safe_title[:max_title_length]
        
        # Combine parts
        if extension:
            return f"{safe_title}_{item_id}{extension}"
        else:
            return f"{safe_title}_{item_id}"
    
    def _sanitize_filename(self, filename: str) -> str:
        """Sanitize filename for filesystem compatibility."""
        # Remove or replace invalid characters
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            filename = filename.replace(char, '_')
        
        # Replace whitespace with underscores
        filename = re.sub(r'\s+', '_', filename)
        
        # Remove control characters
        filename = ''.join(char for char in filename if ord(char) >= 32)
        
        # Remove leading/trailing spaces, dots, and underscores
        filename = filename.strip(' ._')
        
        # Ensure it's not empty
        if not filename:
            filename = "untitled"
        
        return filename
    
    def _sanitize_directory_name(self, dirname: str) -> str:
        """Sanitize directory name for filesystem compatibility."""
        # Similar to filename but allow forward slashes for subdirectories
        invalid_chars = '<>:"|?*\\'
        for char in invalid_chars:
            dirname = dirname.replace(char, '_')
        
        # Replace whitespace with underscores
        dirname = re.sub(r'\s+', '_', dirname)
        
        # Remove control characters
        dirname = ''.join(char for char in dirname if ord(char) >= 32)
        
        # Remove leading/trailing spaces, dots, and underscores
        dirname = dirname.strip(' ._')
        
        # Ensure it's not empty
        if not dirname:
            dirname = "uncategorized"
        
        return dirname
    
    def _calculate_file_checksum(self, file_path: Path) -> str:
        """Calculate MD5 checksum of file."""
        try:
            hasher = hashlib.md5()
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hasher.update(chunk)
            return hasher.hexdigest()
        except Exception as e:
            self.logger.warning(f"Failed to calculate checksum for {file_path}: {e}")
            return ""
    
    def _extract_tags_from_content(self, title: str, content: str) -> List[str]:
        """Extract relevant tags from content."""
        tags = set()
        
        # Combine title and content
        text = f"{title} {content}".lower()
        
        # Programming languages
        programming_tags = [
            'python', 'javascript', 'java', 'c++', 'c#', 'go', 'rust', 'php',
            'ruby', 'swift', 'kotlin', 'typescript', 'scala', 'r', 'matlab'
        ]
        
        # Technologies and frameworks
        tech_tags = [
            'react', 'angular', 'vue', 'node', 'django', 'flask', 'spring',
            'docker', 'kubernetes', 'aws', 'azure', 'gcp', 'git', 'linux',
            'machine learning', 'data science', 'artificial intelligence',
            'web development', 'mobile development', 'devops', 'database'
        ]
        
        # Check for matches
        all_tags = programming_tags + tech_tags
        for tag in all_tags:
            if tag in text:
                tags.add(tag)
        
        return list(tags)[:10]  # Limit to 10 tags
    
    def _generate_topic_index(self, topic: str):
        """Generate index file for a specific topic."""
        try:
            # Get all items for this topic
            topic_items = [
                item for item in self._storage_index.values() 
                if item.topic.lower() == topic.lower()
            ]
            
            if not topic_items:
                return
            
            # Group by content type
            grouped_items = {
                'videos': [item for item in topic_items if item.content_type == 'video'],
                'tutorials': [item for item in topic_items if item.content_type == 'tutorial'],
                'discussions': [item for item in topic_items if item.content_type == 'discussion']
            }
            
            # Create index content
            index_content = f"# {topic.title()} - Learning Resources Index\n\n"
            index_content += f"Generated: {datetime.now(timezone.utc).isoformat()}\n\n"
            
            # Statistics
            total_items = len(topic_items)
            total_size_mb = sum(item.file_size_bytes for item in topic_items) / (1024 * 1024)
            
            index_content += f"**Total Items:** {total_items}\n"
            index_content += f"**Total Size:** {total_size_mb:.1f} MB\n\n"
            
            # Content breakdown
            for content_type, items in grouped_items.items():
                if items:
                    index_content += f"## {content_type.title()} ({len(items)} items)\n\n"
                    
                    for item in sorted(items, key=lambda x: x.storage_date, reverse=True):
                        index_content += f"### {item.title}\n\n"
                        index_content += f"- **Source:** {item.source_domain}\n"
                        index_content += f"- **URL:** {item.original_url}\n"
                        index_content += f"- **Stored:** {item.storage_date.strftime('%Y-%m-%d %H:%M')}\n"
                        if item.file_size_bytes > 0:
                            index_content += f"- **Size:** {item.file_size_bytes / (1024 * 1024):.1f} MB\n"
                        if item.tags:
                            index_content += f"- **Tags:** {', '.join(item.tags)}\n"
                        if item.file_paths:
                            index_content += f"- **Files:** {len(item.file_paths)} file(s)\n"
                        index_content += "\n"
            
            # Save index file
            safe_topic = self._sanitize_directory_name(topic)
            index_path = self.config.base_storage_path / f"{safe_topic}_index.md"
            
            with open(index_path, 'w', encoding='utf-8') as f:
                f.write(index_content)
            
            self.logger.info(f"Generated topic index: {index_path}")
            
        except Exception as e:
            self.logger.error(f"Failed to generate topic index for '{topic}': {e}")
    
    def search_stored_content(
        self,
        query: str = "",
        content_type: Optional[str] = None,
        topic: Optional[str] = None,
        source_domain: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> List[StoredItem]:
        """Search stored content by various criteria.
        
        Args:
            query: Text query to search in titles and content
            content_type: Filter by content type (video, tutorial, discussion)
            topic: Filter by topic
            source_domain: Filter by source domain
            tags: Filter by tags
            
        Returns:
            List of matching stored items
        """
        results = []
        
        for item in self._storage_index.values():
            # Apply filters
            if content_type and item.content_type != content_type:
                continue
            
            if topic and topic.lower() not in item.topic.lower():
                continue
            
            if source_domain and source_domain.lower() not in item.source_domain:
                continue
            
            if tags and not any(tag.lower() in [t.lower() for t in item.tags] for tag in tags):
                continue
            
            # Apply text query
            if query:
                query_lower = query.lower()
                if not (query_lower in item.title.lower() or 
                       any(query_lower in tag.lower() for tag in item.tags)):
                    continue
            
            results.append(item)
        
        # Sort by storage date (newest first)
        results.sort(key=lambda x: x.storage_date, reverse=True)
        
        return results
    
    def get_storage_statistics(self) -> Dict[str, Any]:
        """Get storage statistics."""
        total_items = len(self._storage_index)
        
        if total_items == 0:
            return {
                'total_items': 0,
                'total_size_mb': 0.0,
                'content_type_breakdown': {},
                'topic_breakdown': {},
                'source_breakdown': {},
                'storage_path': str(self.config.base_storage_path)
            }
        
        # Calculate statistics
        total_size_bytes = sum(item.file_size_bytes for item in self._storage_index.values())
        
        # Content type breakdown
        content_types = {}
        for item in self._storage_index.values():
            content_types[item.content_type] = content_types.get(item.content_type, 0) + 1
        
        # Topic breakdown
        topics = {}
        for item in self._storage_index.values():
            topics[item.topic] = topics.get(item.topic, 0) + 1
        
        # Source breakdown
        sources = {}
        for item in self._storage_index.values():
            sources[item.source_domain] = sources.get(item.source_domain, 0) + 1
        
        return {
            'total_items': total_items,
            'total_size_mb': total_size_bytes / (1024 * 1024),
            'content_type_breakdown': content_types,
            'topic_breakdown': topics,
            'source_breakdown': sources,
            'storage_path': str(self.config.base_storage_path),
            'oldest_item': min(item.storage_date for item in self._storage_index.values()).isoformat(),
            'newest_item': max(item.storage_date for item in self._storage_index.values()).isoformat()
        }
    
    def cleanup_orphaned_files(self) -> Dict[str, int]:
        """Clean up files that are no longer referenced in the index."""
        cleanup_stats = {
            'files_checked': 0,
            'orphaned_files_found': 0,
            'orphaned_files_removed': 0,
            'bytes_freed': 0
        }
        
        try:
            # Get all files referenced in index
            referenced_files = set()
            for item in self._storage_index.values():
                for file_path in item.file_paths:
                    referenced_files.add(Path(file_path))
                if item.metadata_path:
                    referenced_files.add(Path(item.metadata_path))
            
            # Scan storage directories
            for content_dir in ['videos', 'tutorials', 'discussions', 'metadata']:
                content_path = self.config.base_storage_path / content_dir
                if not content_path.exists():
                    continue
                
                for file_path in content_path.rglob('*'):
                    if file_path.is_file():
                        cleanup_stats['files_checked'] += 1
                        
                        if file_path not in referenced_files:
                            cleanup_stats['orphaned_files_found'] += 1
                            
                            try:
                                file_size = file_path.stat().st_size
                                file_path.unlink()
                                cleanup_stats['orphaned_files_removed'] += 1
                                cleanup_stats['bytes_freed'] += file_size
                                
                            except Exception as e:
                                self.logger.warning(f"Failed to remove orphaned file {file_path}: {e}")
            
            self.logger.info(
                f"Cleanup complete: removed {cleanup_stats['orphaned_files_removed']} "
                f"orphaned files, freed {cleanup_stats['bytes_freed'] / (1024 * 1024):.1f} MB"
            )
            
        except Exception as e:
            self.logger.error(f"Cleanup failed: {e}")
        
        return cleanup_stats
    
    def export_storage_index(self, export_path: Path) -> bool:
        """Export storage index to external file."""
        try:
            # Create comprehensive export
            export_data = {
                'export_timestamp': datetime.now(timezone.utc).isoformat(),
                'storage_path': str(self.config.base_storage_path),
                'total_items': len(self._storage_index),
                'statistics': self.get_storage_statistics(),
                'items': {
                    item_id: item.to_dict()
                    for item_id, item in self._storage_index.items()
                }
            }
            
            with open(export_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"Storage index exported to: {export_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to export storage index: {e}")
            return False