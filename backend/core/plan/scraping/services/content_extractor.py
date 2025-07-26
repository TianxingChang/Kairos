"""Advanced content extraction and parsing for different media types."""

import re
import json
import logging
from typing import Dict, List, Any, Optional, Tuple, Union
from dataclasses import dataclass
from urllib.parse import urljoin, urlparse
from datetime import datetime, timedelta

from ..models.learning_resource import VideoContent, TutorialContent, DiscussionContent


@dataclass
class ExtractionResult:
    """Result of content extraction with metadata."""
    
    success: bool
    content: Optional[Union[VideoContent, TutorialContent, DiscussionContent]]
    extraction_method: str
    confidence_score: float
    warnings: List[str]
    metadata: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'success': self.success,
            'content': self.content.to_dict() if self.content else None,
            'extraction_method': self.extraction_method,
            'confidence_score': self.confidence_score,
            'warnings': self.warnings,
            'metadata': self.metadata
        }


class VideoContentParser:
    """Specialized parser for video content extraction."""
    
    def __init__(self):
        """Initialize the video content parser."""
        self.logger = logging.getLogger(__name__)
        
        # Video platform patterns
        self.platform_patterns = {
            'youtube': {
                'embed_pattern': r'(?:youtube\.com/embed/|youtu\.be/)([a-zA-Z0-9_-]{11})',
                'watch_pattern': r'youtube\.com/watch\?v=([a-zA-Z0-9_-]{11})',
                'api_url_template': 'https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={video_id}&format=json'
            },
            'vimeo': {
                'embed_pattern': r'vimeo\.com/(?:video/)?(\d+)',
                'api_url_template': 'https://vimeo.com/api/oembed.json?url=https://vimeo.com/{video_id}'
            },
            'dailymotion': {
                'embed_pattern': r'dailymotion\.com/(?:embed/)?video/([a-zA-Z0-9]+)',
            }
        }
        
        # Duration parsing patterns
        self.duration_patterns = [
            r'duration["\']?\s*[:=]\s*["\']?(\d+)["\']?',  # JSON-style duration
            r'(\d+:\d+(?::\d+)?)',  # HH:MM:SS or MM:SS format
            r'PT(\d+H)?(\d+M)?(\d+S)?',  # ISO 8601 duration
            r'length["\']?\s*[:=]\s*["\']?(\d+)["\']?'
        ]
    
    def extract_video_content(self, scraped_data: Dict[str, Any], base_url: str) -> List[ExtractionResult]:
        """Extract video content from scraped data.
        
        Args:
            scraped_data: Raw scraped content
            base_url: Base URL for resolving relative links
            
        Returns:
            List of extraction results for video content
        """
        results = []
        html_content = scraped_data.get('html', '')
        
        # Extract embedded videos
        iframe_videos = self._extract_iframe_videos(html_content, base_url)
        results.extend(iframe_videos)
        
        # Extract HTML5 videos
        html5_videos = self._extract_html5_videos(html_content, base_url)
        results.extend(html5_videos)
        
        # Extract video metadata from structured data
        structured_videos = self._extract_structured_video_data(html_content, scraped_data)
        results.extend(structured_videos)
        
        # Deduplicate based on URL
        deduplicated_results = self._deduplicate_videos(results)
        
        self.logger.info(
            f"Extracted {len(deduplicated_results)} video content items "
            f"from {len(results)} total matches"
        )
        
        return deduplicated_results
    
    def _extract_iframe_videos(self, html_content: str, base_url: str) -> List[ExtractionResult]:
        """Extract videos from iframe elements."""
        results = []
        iframe_pattern = r'<iframe[^>]*src=["\']([^"\']+)["\'][^>]*>(?:.*?</iframe>)?'
        
        for match in re.finditer(iframe_pattern, html_content, re.IGNORECASE | re.DOTALL):
            iframe_html = match.group(0)
            video_url = match.group(1)
            
            # Check if it's a video platform
            platform = self._identify_video_platform(video_url)
            if not platform:
                continue
            
            # Extract video metadata
            video_id = self._extract_video_id(video_url, platform)
            title = self._extract_title_from_iframe(iframe_html, html_content, video_url)
            description = self._extract_description_from_context(html_content, video_url)
            duration = self._extract_duration_from_context(html_content, iframe_html)
            thumbnail = self._extract_thumbnail_url(video_url, platform, video_id)
            
            video_content = VideoContent(
                title=title or f"{platform.title()} Video",
                url=video_url,
                duration=duration,
                description=description or "",
                thumbnail_url=thumbnail
            )
            
            result = ExtractionResult(
                success=True,
                content=video_content,
                extraction_method=f"iframe_{platform}",
                confidence_score=0.9,
                warnings=[],
                metadata={
                    'platform': platform,
                    'video_id': video_id,
                    'extraction_source': 'iframe'
                }
            )
            
            results.append(result)
        
        return results
    
    def _extract_html5_videos(self, html_content: str, base_url: str) -> List[ExtractionResult]:
        """Extract HTML5 video elements."""
        results = []
        video_pattern = r'<video[^>]*>(.*?)</video>'
        
        for match in re.finditer(video_pattern, html_content, re.IGNORECASE | re.DOTALL):
            video_html = match.group(0)
            video_inner = match.group(1)
            
            # Extract video source
            src_match = re.search(r'src=["\']([^"\']+)["\']', video_html)
            if not src_match:
                # Try to find source in nested elements
                source_match = re.search(r'<source[^>]*src=["\']([^"\']+)["\']', video_inner)
                if source_match:
                    video_url = source_match.group(1)
                else:
                    continue
            else:
                video_url = src_match.group(1)
            
            # Resolve relative URLs
            if not video_url.startswith(('http://', 'https://')):
                video_url = urljoin(base_url, video_url)
            
            # Extract metadata
            title = self._extract_title_from_video_element(video_html)
            description = self._extract_description_from_context(html_content, video_url)
            duration = self._extract_duration_from_video_element(video_html)
            poster = self._extract_poster_from_video_element(video_html, base_url)
            
            video_content = VideoContent(
                title=title or "HTML5 Video",
                url=video_url,
                duration=duration,
                description=description or "",
                thumbnail_url=poster
            )
            
            result = ExtractionResult(
                success=True,
                content=video_content,
                extraction_method="html5_video",
                confidence_score=0.8,
                warnings=[],
                metadata={
                    'platform': 'html5',
                    'extraction_source': 'video_element'
                }
            )
            
            results.append(result)
        
        return results
    
    def _extract_structured_video_data(self, html_content: str, scraped_data: Dict[str, Any]) -> List[ExtractionResult]:
        """Extract video data from structured metadata (JSON-LD, microdata)."""
        results = []
        
        # Extract JSON-LD structured data
        jsonld_pattern = r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>'
        
        for match in re.finditer(jsonld_pattern, html_content, re.IGNORECASE | re.DOTALL):
            try:
                json_content = match.group(1).strip()
                data = json.loads(json_content)
                
                # Handle both single objects and arrays
                if isinstance(data, dict):
                    data = [data]
                elif not isinstance(data, list):
                    continue
                
                for item in data:
                    if item.get('@type') == 'VideoObject':
                        video_result = self._extract_from_video_object(item)
                        if video_result:
                            results.append(video_result)
                
            except json.JSONDecodeError as e:
                self.logger.warning(f"Failed to parse JSON-LD: {e}")
                continue
        
        return results
    
    def _extract_from_video_object(self, video_obj: Dict[str, Any]) -> Optional[ExtractionResult]:
        """Extract video content from VideoObject schema."""
        try:
            title = video_obj.get('name') or video_obj.get('title', 'Structured Video')
            description = video_obj.get('description', '')
            url = video_obj.get('contentUrl') or video_obj.get('embedUrl', '')
            
            if not url:
                return None
            
            # Parse duration
            duration = None
            duration_str = video_obj.get('duration')
            if duration_str:
                duration = self._parse_iso8601_duration(duration_str)
            
            # Extract thumbnail
            thumbnail_url = None
            thumbnail_obj = video_obj.get('thumbnailUrl')
            if thumbnail_obj:
                if isinstance(thumbnail_obj, str):
                    thumbnail_url = thumbnail_obj
                elif isinstance(thumbnail_obj, list) and thumbnail_obj:
                    thumbnail_url = thumbnail_obj[0]
                elif isinstance(thumbnail_obj, dict):
                    thumbnail_url = thumbnail_obj.get('url')
            
            video_content = VideoContent(
                title=title,
                url=url,
                duration=duration,
                description=description,
                thumbnail_url=thumbnail_url
            )
            
            return ExtractionResult(
                success=True,
                content=video_content,
                extraction_method="structured_data",
                confidence_score=0.95,
                warnings=[],
                metadata={
                    'extraction_source': 'json_ld',
                    'schema_type': 'VideoObject'
                }
            )
        
        except Exception as e:
            self.logger.warning(f"Failed to extract from VideoObject: {e}")
            return None
    
    def _identify_video_platform(self, url: str) -> Optional[str]:
        """Identify video platform from URL."""
        url_lower = url.lower()
        
        # Check domain-specific patterns
        if 'youtube.com' in url_lower or 'youtu.be' in url_lower:
            return 'youtube'
        elif 'vimeo.com' in url_lower:
            return 'vimeo'
        elif 'dailymotion.com' in url_lower:
            return 'dailymotion'
        
        return None
    
    def _extract_video_id(self, url: str, platform: str) -> Optional[str]:
        """Extract video ID from platform URL."""
        if platform not in self.platform_patterns:
            return None
        
        patterns = self.platform_patterns[platform]
        
        for pattern_key in ['embed_pattern', 'watch_pattern']:
            if pattern_key in patterns:
                match = re.search(patterns[pattern_key], url)
                if match:
                    return match.group(1)
        
        return None
    
    def _extract_title_from_iframe(self, iframe_html: str, html_content: str, video_url: str) -> Optional[str]:
        """Extract video title from iframe or surrounding context."""
        # Try iframe title attribute
        title_match = re.search(r'title=["\']([^"\']+)["\']', iframe_html, re.IGNORECASE)
        if title_match:
            return title_match.group(1).strip()
        
        # Try to find title in surrounding context
        iframe_start = html_content.find(iframe_html)
        if iframe_start != -1:
            # Look for headings or titles within 500 characters before iframe
            context_before = html_content[max(0, iframe_start - 500):iframe_start]
            heading_match = re.search(r'<h[1-6][^>]*>([^<]+)</h[1-6]>', context_before[::-1], re.IGNORECASE)
            if heading_match:
                return heading_match.group(1).strip()[::-1]  # Reverse back
        
        return None
    
    def _extract_description_from_context(self, html_content: str, video_url: str) -> Optional[str]:
        """Extract video description from surrounding context."""
        # Find the video element in HTML
        video_pos = html_content.find(video_url)
        if video_pos == -1:
            return None
        
        # Look for description in surrounding paragraphs
        context_start = max(0, video_pos - 1000)
        context_end = min(len(html_content), video_pos + 1000)
        context = html_content[context_start:context_end]
        
        # Find paragraphs that might contain description
        p_pattern = r'<p[^>]*>([^<]+)</p>'
        p_matches = re.findall(p_pattern, context, re.IGNORECASE)
        
        for p_content in p_matches:
            if len(p_content.strip()) > 20:  # Minimum meaningful description
                return p_content.strip()[:500]  # Limit length
        
        return None
    
    def _extract_duration_from_context(self, html_content: str, element_html: str) -> Optional[int]:
        """Extract video duration from context or element."""
        combined_content = f"{element_html} {html_content}"
        
        for pattern in self.duration_patterns:
            match = re.search(pattern, combined_content, re.IGNORECASE)
            if match:
                duration_str = match.group(1)
                return self._parse_duration_string(duration_str)
        
        return None
    
    def _extract_thumbnail_url(self, video_url: str, platform: str, video_id: Optional[str]) -> Optional[str]:
        """Generate thumbnail URL based on platform and video ID."""
        if not video_id:
            return None
        
        thumbnail_templates = {
            'youtube': f'https://img.youtube.com/vi/{video_id}/maxresdefault.jpg',
            'vimeo': None,  # Would need API call
            'dailymotion': f'https://www.dailymotion.com/thumbnail/video/{video_id}'
        }
        
        return thumbnail_templates.get(platform)
    
    def _extract_title_from_video_element(self, video_html: str) -> Optional[str]:
        """Extract title from HTML5 video element."""
        # Try title attribute
        title_match = re.search(r'title=["\']([^"\']+)["\']', video_html, re.IGNORECASE)
        if title_match:
            return title_match.group(1)
        
        # Try aria-label
        aria_match = re.search(r'aria-label=["\']([^"\']+)["\']', video_html, re.IGNORECASE)
        if aria_match:
            return aria_match.group(1)
        
        return None
    
    def _extract_duration_from_video_element(self, video_html: str) -> Optional[int]:
        """Extract duration from HTML5 video element."""
        # Look for data attributes that might contain duration
        data_duration = re.search(r'data-duration=["\'](\d+)["\']', video_html)
        if data_duration:
            return int(data_duration.group(1))
        
        return None
    
    def _extract_poster_from_video_element(self, video_html: str, base_url: str) -> Optional[str]:
        """Extract poster/thumbnail from HTML5 video element."""
        poster_match = re.search(r'poster=["\']([^"\']+)["\']', video_html)
        if poster_match:
            poster_url = poster_match.group(1)
            if not poster_url.startswith(('http://', 'https://')):
                poster_url = urljoin(base_url, poster_url)
            return poster_url
        
        return None
    
    def _parse_duration_string(self, duration_str: str) -> Optional[int]:
        """Parse duration string to seconds."""
        # Handle time format (HH:MM:SS or MM:SS)
        if ':' in duration_str:
            parts = duration_str.split(':')
            try:
                if len(parts) == 2:  # MM:SS
                    return int(parts[0]) * 60 + int(parts[1])
                elif len(parts) == 3:  # HH:MM:SS
                    return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
            except ValueError:
                return None
        
        # Handle plain seconds
        try:
            return int(duration_str)
        except ValueError:
            return None
    
    def _parse_iso8601_duration(self, duration_str: str) -> Optional[int]:
        """Parse ISO 8601 duration string (PT1H30M45S) to seconds."""
        match = re.match(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', duration_str.upper())
        if not match:
            return None
        
        hours = int(match.group(1) or 0)
        minutes = int(match.group(2) or 0)
        seconds = int(match.group(3) or 0)
        
        return hours * 3600 + minutes * 60 + seconds
    
    def _deduplicate_videos(self, results: List[ExtractionResult]) -> List[ExtractionResult]:
        """Remove duplicate video results based on URL."""
        seen_urls = set()
        deduplicated = []
        
        for result in results:
            if result.content and result.content.url not in seen_urls:
                seen_urls.add(result.content.url)
                deduplicated.append(result)
        
        return deduplicated


class TutorialContentParser:
    """Specialized parser for tutorial content extraction."""
    
    def __init__(self):
        """Initialize the tutorial content parser."""
        self.logger = logging.getLogger(__name__)
        
        # Tutorial structure patterns
        self.step_patterns = [
            r'(?:step|étape)\s*(\d+)[:\-\s]*(.*?)(?=(?:step|étape)\s*\d+|$)',
            r'(\d+)[\.\)]\s*(.*?)(?=\d+[\.\)]|$)',
            r'<h[1-6][^>]*>(?:step|chapter|lesson)\s*(\d+)[:\-\s]*(.*?)</h[1-6]>',
        ]
        
        # Code block patterns
        self.code_patterns = [
            r'```(\w+)?\s*(.*?)\s*```',  # Markdown code blocks (flexible whitespace)
            r'<pre[^>]*><code[^>]*>(.*?)</code></pre>',  # HTML pre+code
            r'<code[^>]*>(.*?)</code>',  # Inline code
            r'{% highlight (\w+) %}(.*?){% endhighlight %}',  # Jekyll highlight
        ]
        
        # Image patterns
        self.image_patterns = [
            r'!\[([^\]]*)\]\(([^)]+)\)',  # Markdown images
            r'<img[^>]*src=["\']([^"\']+)["\'][^>]*(?:alt=["\']([^"\']*)["\'])?[^>]*>',  # HTML images
        ]
    
    def extract_tutorial_content(self, scraped_data: Dict[str, Any], base_url: str) -> List[ExtractionResult]:
        """Extract tutorial content from scraped data.
        
        Args:
            scraped_data: Raw scraped content
            base_url: Base URL for resolving relative links
            
        Returns:
            List of extraction results for tutorial content
        """
        results = []
        
        # Extract from markdown content (preferred)
        markdown_content = scraped_data.get('markdown', '')
        if markdown_content:
            markdown_result = self._extract_from_markdown(markdown_content, base_url, scraped_data)
            if markdown_result:
                results.append(markdown_result)
        
        # Extract structured tutorial data first (highest quality)
        html_content = scraped_data.get('html', '')
        structured_results = self._extract_structured_tutorial_data(html_content, scraped_data)
        results.extend(structured_results)
        
        # Extract from HTML content only if no structured data and no markdown
        if html_content and not markdown_content and not structured_results:
            html_result = self._extract_from_html(html_content, base_url, scraped_data)
            if html_result:
                results.append(html_result)
        
        self.logger.info(f"Extracted {len(results)} tutorial content items")
        
        return results
    
    def _extract_from_markdown(self, markdown_content: str, base_url: str, scraped_data: Dict[str, Any]) -> Optional[ExtractionResult]:
        """Extract tutorial content from markdown."""
        try:
            # Extract title
            title = self._extract_title_from_markdown(markdown_content) or scraped_data.get('title', 'Tutorial')
            
            # Extract sections (headers)
            sections = self._extract_sections_from_markdown(markdown_content)
            
            # Extract code examples
            code_examples = self._extract_code_examples_from_markdown(markdown_content)
            
            # Extract images
            images = self._extract_images_from_markdown(markdown_content, base_url)
            
            # Calculate content quality score
            quality_score = self._calculate_tutorial_quality(markdown_content, len(sections), len(code_examples))
            
            tutorial_content = TutorialContent(
                title=title,
                content=markdown_content,
                sections=sections,
                code_examples=code_examples,
                images=images
            )
            
            return ExtractionResult(
                success=True,
                content=tutorial_content,
                extraction_method="markdown_parsing",
                confidence_score=quality_score,
                warnings=[],
                metadata={
                    'content_length': len(markdown_content),
                    'sections_count': len(sections),
                    'code_examples_count': len(code_examples),
                    'images_count': len(images),
                    'extraction_source': 'markdown'
                }
            )
        
        except Exception as e:
            self.logger.error(f"Failed to extract tutorial from markdown: {e}")
            return None
    
    def _extract_from_html(self, html_content: str, base_url: str, scraped_data: Dict[str, Any]) -> Optional[ExtractionResult]:
        """Extract tutorial content from HTML."""
        try:
            # Convert HTML to clean text
            clean_content = self._html_to_clean_text(html_content)
            
            # Extract title
            title = self._extract_title_from_html(html_content) or scraped_data.get('title', 'Tutorial')
            
            # Extract sections from HTML headers
            sections = self._extract_sections_from_html(html_content)
            
            # Extract code examples from HTML
            code_examples = self._extract_code_examples_from_html(html_content)
            
            # Extract images from HTML
            images = self._extract_images_from_html(html_content, base_url)
            
            # Calculate quality score
            quality_score = self._calculate_tutorial_quality(clean_content, len(sections), len(code_examples))
            
            tutorial_content = TutorialContent(
                title=title,
                content=clean_content,
                sections=sections,
                code_examples=code_examples,
                images=images
            )
            
            return ExtractionResult(
                success=True,
                content=tutorial_content,
                extraction_method="html_parsing",
                confidence_score=quality_score * 0.8,  # Lower confidence for HTML
                warnings=[],
                metadata={
                    'content_length': len(clean_content),
                    'sections_count': len(sections),
                    'code_examples_count': len(code_examples),
                    'images_count': len(images),
                    'extraction_source': 'html'
                }
            )
        
        except Exception as e:
            self.logger.error(f"Failed to extract tutorial from HTML: {e}")
            return None
    
    def _extract_structured_tutorial_data(self, html_content: str, scraped_data: Dict[str, Any]) -> List[ExtractionResult]:
        """Extract tutorial data from structured markup."""
        results = []
        
        # Look for tutorial-specific structured data
        jsonld_pattern = r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>'
        
        for match in re.finditer(jsonld_pattern, html_content, re.IGNORECASE | re.DOTALL):
            try:
                json_content = match.group(1).strip()
                data = json.loads(json_content)
                
                if isinstance(data, dict):
                    data = [data]
                
                for item in data:
                    if item.get('@type') in ['TechArticle', 'Article', 'HowTo']:
                        tutorial_result = self._extract_from_structured_article(item)
                        if tutorial_result:
                            results.append(tutorial_result)
                
            except json.JSONDecodeError:
                continue
        
        return results
    
    def _extract_title_from_markdown(self, markdown_content: str) -> Optional[str]:
        """Extract title from markdown content."""
        # Look for first H1 header (handle indented markdown)
        h1_match = re.search(r'^\s*#\s+(.+)$', markdown_content, re.MULTILINE)
        if h1_match:
            return h1_match.group(1).strip()
        
        return None
    
    def _extract_sections_from_markdown(self, markdown_content: str) -> List[str]:
        """Extract section headers from markdown."""
        sections = []
        
        # Extract all headers (H1-H6) - handle indented markdown
        header_pattern = r'^\s*(#{1,6})\s+(.+)$'
        
        for match in re.finditer(header_pattern, markdown_content, re.MULTILINE):
            level = len(match.group(1))
            title = match.group(2).strip()
            sections.append(f"{'  ' * (level-1)}{title}")
        
        return sections
    
    def _extract_code_examples_from_markdown(self, markdown_content: str) -> List[str]:
        """Extract code examples from markdown."""
        code_examples = []
        
        # Extract fenced code blocks
        for pattern in self.code_patterns:
            matches = re.findall(pattern, markdown_content, re.DOTALL | re.IGNORECASE)
            
            for match in matches:
                if isinstance(match, tuple):
                    # Pattern with language specifier
                    code = match[1] if len(match) > 1 else match[0]
                else:
                    code = match
                
                code = code.strip()
                if code and len(code) > 10:  # Minimum meaningful code length
                    code_examples.append(code)
        
        return code_examples
    
    def _extract_images_from_markdown(self, markdown_content: str, base_url: str) -> List[str]:
        """Extract images from markdown content."""
        images = []
        
        # Find markdown image syntax
        image_matches = re.findall(r'!\[([^\]]*)\]\(([^)]+)\)', markdown_content)
        
        for alt_text, image_url in image_matches:
            # Resolve relative URLs
            if not image_url.startswith(('http://', 'https://', 'data:')):
                image_url = urljoin(base_url, image_url)
            images.append(image_url)
        
        return images
    
    def _extract_title_from_html(self, html_content: str) -> Optional[str]:
        """Extract title from HTML content."""
        # Try title tag first
        title_match = re.search(r'<title[^>]*>([^<]+)</title>', html_content, re.IGNORECASE)
        if title_match:
            return title_match.group(1).strip()
        
        # Try first H1
        h1_match = re.search(r'<h1[^>]*>([^<]+)</h1>', html_content, re.IGNORECASE)
        if h1_match:
            return h1_match.group(1).strip()
        
        return None
    
    def _extract_sections_from_html(self, html_content: str) -> List[str]:
        """Extract section headers from HTML."""
        sections = []
        
        # Extract all header tags
        header_pattern = r'<h([1-6])[^>]*>([^<]+)</h[1-6]>'
        
        for match in re.finditer(header_pattern, html_content, re.IGNORECASE):
            level = int(match.group(1))
            title = match.group(2).strip()
            # Clean HTML entities
            title = re.sub(r'&[a-zA-Z]+;', '', title)
            sections.append(f"{'  ' * (level-1)}{title}")
        
        return sections
    
    def _extract_code_examples_from_html(self, html_content: str) -> List[str]:
        """Extract code examples from HTML."""
        code_examples = []
        
        # Extract from pre/code blocks
        pre_code_pattern = r'<pre[^>]*><code[^>]*>([^<]+)</code></pre>'
        matches = re.findall(pre_code_pattern, html_content, re.DOTALL | re.IGNORECASE)
        
        for code in matches:
            # Clean HTML entities and formatting
            code = re.sub(r'&lt;', '<', code)
            code = re.sub(r'&gt;', '>', code)
            code = re.sub(r'&amp;', '&', code)
            code = code.strip()
            
            if code and len(code) > 10:
                code_examples.append(code)
        
        return code_examples
    
    def _extract_images_from_html(self, html_content: str, base_url: str) -> List[str]:
        """Extract images from HTML content."""
        images = []
        
        # Find img tags
        img_pattern = r'<img[^>]*src=["\']([^"\']+)["\'][^>]*>'
        
        for match in re.finditer(img_pattern, html_content, re.IGNORECASE):
            image_url = match.group(1)
            
            # Skip base64 images and very small images (likely icons)
            if image_url.startswith('data:') or 'icon' in image_url.lower():
                continue
            
            # Resolve relative URLs
            if not image_url.startswith(('http://', 'https://')):
                image_url = urljoin(base_url, image_url)
            
            images.append(image_url)
        
        return images
    
    def _html_to_clean_text(self, html_content: str) -> str:
        """Convert HTML to clean text content."""
        # Remove script and style tags
        html_content = re.sub(r'<script[^>]*>.*?</script>', '', html_content, flags=re.DOTALL | re.IGNORECASE)
        html_content = re.sub(r'<style[^>]*>.*?</style>', '', html_content, flags=re.DOTALL | re.IGNORECASE)
        
        # Replace common tags with appropriate formatting
        html_content = re.sub(r'<br[^>]*>', '\n', html_content, flags=re.IGNORECASE)
        html_content = re.sub(r'</p>', '\n\n', html_content, flags=re.IGNORECASE)
        html_content = re.sub(r'<h[1-6][^>]*>', '\n## ', html_content, flags=re.IGNORECASE)
        html_content = re.sub(r'</h[1-6]>', '\n', html_content, flags=re.IGNORECASE)
        
        # Remove all remaining HTML tags
        html_content = re.sub(r'<[^>]+>', '', html_content)
        
        # Clean up whitespace
        html_content = re.sub(r'\n\s*\n', '\n\n', html_content)
        html_content = re.sub(r' +', ' ', html_content)
        
        return html_content.strip()
    
    def _calculate_tutorial_quality(self, content: str, sections_count: int, code_count: int) -> float:
        """Calculate tutorial quality score based on content features."""
        score = 0.5  # Base score
        
        # Content length score
        content_length = len(content)
        if content_length > 5000:
            score += 0.2
        elif content_length > 2000:
            score += 0.1
        
        # Structure score (sections)
        if sections_count > 5:
            score += 0.2
        elif sections_count > 2:
            score += 0.1
        
        # Code examples score
        if code_count > 3:
            score += 0.2
        elif code_count > 0:
            score += 0.1
        
        # Educational keywords bonus
        educational_keywords = ['tutorial', 'guide', 'step', 'example', 'learn', 'how to']
        keyword_count = sum(1 for keyword in educational_keywords if keyword in content.lower())
        score += min(keyword_count * 0.05, 0.1)
        
        return min(score, 1.0)
    
    def _extract_from_structured_article(self, article_data: Dict[str, Any]) -> Optional[ExtractionResult]:
        """Extract tutorial from structured article data."""
        try:
            title = article_data.get('name') or article_data.get('headline', 'Structured Tutorial')
            description = article_data.get('description', '')
            
            # Extract steps if it's a HowTo
            steps = []
            if article_data.get('@type') == 'HowTo':
                steps_data = article_data.get('step', [])
                if isinstance(steps_data, list):
                    steps = [step.get('text', '') for step in steps_data if isinstance(step, dict)]
            
            content = description
            if steps:
                content += '\n\n' + '\n'.join(f"Step {i+1}: {step}" for i, step in enumerate(steps))
            
            tutorial_content = TutorialContent(
                title=title,
                content=content,
                sections=steps if steps else [],
                code_examples=[],
                images=[]
            )
            
            return ExtractionResult(
                success=True,
                content=tutorial_content,
                extraction_method="structured_article",
                confidence_score=0.85,
                warnings=[],
                metadata={
                    'schema_type': article_data.get('@type'),
                    'extraction_source': 'structured_data'
                }
            )
        
        except Exception as e:
            self.logger.warning(f"Failed to extract structured article: {e}")
            return None


class DiscussionContentParser:
    """Specialized parser for discussion/forum content extraction."""
    
    def __init__(self):
        """Initialize the discussion content parser."""
        self.logger = logging.getLogger(__name__)
        
        # Discussion platform patterns
        self.platform_patterns = {
            'stackoverflow': {
                'question_pattern': r'<div[^>]*class="[^"]*question[^"]*"[^>]*>(.*?)</div>',
                'answer_pattern': r'<div[^>]*class="[^"]*answer[^"]*"[^>]*>(.*?)</div>',
                'comment_pattern': r'<div[^>]*class="[^"]*comment[^"]*"[^>]*>(.*?)</div>'
            },
            'reddit': {
                'post_pattern': r'<div[^>]*class="[^"]*post[^"]*"[^>]*>(.*?)</div>',
                'comment_pattern': r'<div[^>]*class="[^"]*comment[^"]*"[^>]*>(.*?)</div>'
            },
            'discourse': {
                'post_pattern': r'<article[^>]*class="[^"]*post[^"]*"[^>]*>(.*?)</article>',
                'reply_pattern': r'<div[^>]*class="[^"]*reply[^"]*"[^>]*>(.*?)</div>'
            }
        }
    
    def extract_discussion_content(self, scraped_data: Dict[str, Any], base_url: str) -> List[ExtractionResult]:
        """Extract discussion content from scraped data.
        
        Args:
            scraped_data: Raw scraped content
            base_url: Base URL for resolving relative links
            
        Returns:
            List of extraction results for discussion content
        """
        results = []
        html_content = scraped_data.get('html', '')
        
        # Identify platform
        platform = self._identify_discussion_platform(base_url, html_content)
        
        if platform:
            # Use platform-specific extraction
            platform_result = self._extract_platform_specific(html_content, platform, scraped_data)
            if platform_result:
                results.append(platform_result)
        else:
            # Use generic extraction
            generic_result = self._extract_generic_discussion(html_content, scraped_data)
            if generic_result:
                results.append(generic_result)
        
        # Extract from structured data
        structured_results = self._extract_structured_discussion_data(html_content, scraped_data)
        results.extend(structured_results)
        
        self.logger.info(f"Extracted {len(results)} discussion content items")
        
        return results
    
    def _identify_discussion_platform(self, base_url: str, html_content: str) -> Optional[str]:
        """Identify the discussion platform."""
        url_lower = base_url.lower()
        
        # Check for specific domain patterns first
        if any(domain in url_lower for domain in ['stackoverflow.com', 'serverfault.com', 'superuser.com']):
            return 'stackoverflow'
        elif 'reddit.com' in url_lower:
            return 'reddit'
        elif 'github.com' in url_lower:
            return 'github'
        elif 'disqus' in url_lower:
            return 'disqus'
        
        # Check HTML content for platform indicators
        html_lower = html_content.lower()
        if 'stackoverflow' in html_lower:
            return 'stackoverflow'
        elif 'reddit' in html_lower:
            return 'reddit'
        elif 'discourse' in html_lower:  # Only detect discourse from content, not generic 'forum' URLs
            return 'discourse'
        
        return None
    
    def _extract_platform_specific(self, html_content: str, platform: str, scraped_data: Dict[str, Any]) -> Optional[ExtractionResult]:
        """Extract discussion content using platform-specific patterns."""
        try:
            if platform == 'stackoverflow':
                return self._extract_stackoverflow_content(html_content, scraped_data)
            elif platform == 'reddit':
                return self._extract_reddit_content(html_content, scraped_data)
            elif platform == 'discourse':
                return self._extract_discourse_content(html_content, scraped_data)
            elif platform == 'github':
                return self._extract_github_issues_content(html_content, scraped_data)
            else:
                return self._extract_generic_discussion(html_content, scraped_data)
        
        except Exception as e:
            self.logger.error(f"Failed to extract {platform} content: {e}")
            return None
    
    def _extract_stackoverflow_content(self, html_content: str, scraped_data: Dict[str, Any]) -> Optional[ExtractionResult]:
        """Extract StackOverflow Q&A content."""
        title = scraped_data.get('title', 'StackOverflow Discussion')
        
        # Extract question
        question_pattern = r'<div[^>]*class="[^"]*question[^"]*"[^>]*>(.*?)</div>'
        question_matches = re.findall(question_pattern, html_content, re.DOTALL | re.IGNORECASE)
        
        # Extract answers
        answer_pattern = r'<div[^>]*class="[^"]*answer[^"]*"[^>]*>(.*?)</div>'
        answer_matches = re.findall(answer_pattern, html_content, re.DOTALL | re.IGNORECASE)
        
        # Extract comments
        comment_pattern = r'<div[^>]*class="[^"]*comment[^"]*"[^>]*>(.*?)</div>'
        comment_matches = re.findall(comment_pattern, html_content, re.DOTALL | re.IGNORECASE)
        
        # Process posts (question + answers)
        posts = []
        if question_matches:
            posts.append({
                'type': 'question',
                'content': self._clean_html_content(question_matches[0]),
                'timestamp': 'unknown',
                'author': 'unknown',
                'score': 0
            })
        
        for answer_html in answer_matches:
            posts.append({
                'type': 'answer',
                'content': self._clean_html_content(answer_html),
                'timestamp': 'unknown',
                'author': 'unknown',
                'score': 0
            })
        
        # Process comments
        comments = []
        for comment_html in comment_matches:
            comments.append({
                'content': self._clean_html_content(comment_html),
                'timestamp': 'unknown',
                'author': 'unknown'
            })
        
        # Create Q&A pairs
        qa_pairs = []
        if posts:
            question = posts[0] if posts[0]['type'] == 'question' else None
            answers = [post for post in posts if post['type'] == 'answer']
            
            for answer in answers:
                qa_pairs.append({
                    'question': question['content'] if question else '',
                    'answer': answer['content'],
                    'score': answer.get('score', 0)
                })
        
        discussion_content = DiscussionContent(
            title=title,
            posts=posts,
            comments=comments,
            qa_pairs=qa_pairs
        )
        
        return ExtractionResult(
            success=True,
            content=discussion_content,
            extraction_method="stackoverflow_specific",
            confidence_score=0.9,
            warnings=[],
            metadata={
                'platform': 'stackoverflow',
                'posts_count': len(posts),
                'comments_count': len(comments),
                'qa_pairs_count': len(qa_pairs)
            }
        )
    
    def _extract_reddit_content(self, html_content: str, scraped_data: Dict[str, Any]) -> Optional[ExtractionResult]:
        """Extract Reddit post and comments content."""
        title = scraped_data.get('title', 'Reddit Discussion')
        
        # Extract main post
        post_pattern = r'<div[^>]*class="[^"]*thing[^"]*"[^>]*>(.*?)</div>'
        post_matches = re.findall(post_pattern, html_content, re.DOTALL | re.IGNORECASE)
        
        # Extract comments
        comment_pattern = r'<div[^>]*class="[^"]*comment[^"]*"[^>]*>(.*?)</div>'
        comment_matches = re.findall(comment_pattern, html_content, re.DOTALL | re.IGNORECASE)
        
        posts = []
        for post_html in post_matches:
            posts.append({
                'type': 'post',
                'content': self._clean_html_content(post_html),
                'timestamp': 'unknown',
                'author': 'unknown',
                'score': 0
            })
        
        comments = []
        for comment_html in comment_matches:
            comments.append({
                'content': self._clean_html_content(comment_html),
                'timestamp': 'unknown',
                'author': 'unknown'
            })
        
        discussion_content = DiscussionContent(
            title=title,
            posts=posts,
            comments=comments
        )
        
        return ExtractionResult(
            success=True,
            content=discussion_content,
            extraction_method="reddit_specific",
            confidence_score=0.85,
            warnings=[],
            metadata={
                'platform': 'reddit',
                'posts_count': len(posts),
                'comments_count': len(comments)
            }
        )
    
    def _extract_discourse_content(self, html_content: str, scraped_data: Dict[str, Any]) -> Optional[ExtractionResult]:
        """Extract Discourse forum content."""
        title = scraped_data.get('title', 'Forum Discussion')
        
        # Extract posts
        post_pattern = r'<article[^>]*class="[^"]*post[^"]*"[^>]*>(.*?)</article>'
        post_matches = re.findall(post_pattern, html_content, re.DOTALL | re.IGNORECASE)
        
        posts = []
        for post_html in post_matches:
            posts.append({
                'type': 'post',
                'content': self._clean_html_content(post_html),
                'timestamp': 'unknown',
                'author': 'unknown'
            })
        
        discussion_content = DiscussionContent(
            title=title,
            posts=posts
        )
        
        return ExtractionResult(
            success=True,
            content=discussion_content,
            extraction_method="discourse_specific",
            confidence_score=0.8,
            warnings=[],
            metadata={
                'platform': 'discourse',
                'posts_count': len(posts)
            }
        )
    
    def _extract_github_issues_content(self, html_content: str, scraped_data: Dict[str, Any]) -> Optional[ExtractionResult]:
        """Extract GitHub issues/discussions content."""
        title = scraped_data.get('title', 'GitHub Discussion')
        
        # Extract issue description and comments
        comment_pattern = r'<div[^>]*class="[^"]*comment[^"]*"[^>]*>(.*?)</div>'
        comment_matches = re.findall(comment_pattern, html_content, re.DOTALL | re.IGNORECASE)
        
        comments = []
        for comment_html in comment_matches:
            comments.append({
                'content': self._clean_html_content(comment_html),
                'timestamp': 'unknown',
                'author': 'unknown'
            })
        
        discussion_content = DiscussionContent(
            title=title,
            comments=comments
        )
        
        return ExtractionResult(
            success=True,
            content=discussion_content,
            extraction_method="github_specific",
            confidence_score=0.8,
            warnings=[],
            metadata={
                'platform': 'github',
                'comments_count': len(comments)
            }
        )
    
    def _extract_generic_discussion(self, html_content: str, scraped_data: Dict[str, Any]) -> Optional[ExtractionResult]:
        """Extract discussion content using generic patterns."""
        title = scraped_data.get('title', 'Discussion')
        
        # Generic patterns for discussion content
        generic_patterns = [
            r'<div[^>]*class="[^"]*(?:comment|post|reply|message)[^"]*"[^>]*>(.*?)</div>',
            r'<article[^>]*class="[^"]*(?:comment|post|reply)[^"]*"[^>]*>(.*?)</article>',
            r'<li[^>]*class="[^"]*(?:comment|post|reply)[^"]*"[^>]*>(.*?)</li>'
        ]
        
        all_content = []
        for pattern in generic_patterns:
            matches = re.findall(pattern, html_content, re.DOTALL | re.IGNORECASE)
            all_content.extend(matches)
        
        if not all_content:
            return None
        
        # Process as comments/posts
        comments = []
        posts = []
        
        for content_html in all_content:
            cleaned_content = self._clean_html_content(content_html)
            if len(cleaned_content) > 20:  # Minimum meaningful content
                # Check if content has post-like structure (headings, longer text)
                is_post = (len(cleaned_content) > 100 and  # Longer content
                          ('Learning' in cleaned_content or 'Tips' in cleaned_content or 'Tutorial' in cleaned_content))
                
                if is_post:
                    posts.append({
                        'content': cleaned_content,
                        'timestamp': 'unknown',
                        'author': 'unknown'
                    })
                else:  # Shorter content or comments
                    comments.append({
                        'content': cleaned_content,
                        'timestamp': 'unknown',
                        'author': 'unknown'
                    })
        
        discussion_content = DiscussionContent(
            title=title,
            posts=posts,
            comments=comments
        )
        
        return ExtractionResult(
            success=True,
            content=discussion_content,
            extraction_method="generic_discussion",
            confidence_score=0.6,
            warnings=["Generic extraction - may have lower accuracy"],
            metadata={
                'platform': 'unknown',
                'posts_count': len(posts),
                'comments_count': len(comments)
            }
        )
    
    def _extract_structured_discussion_data(self, html_content: str, scraped_data: Dict[str, Any]) -> List[ExtractionResult]:
        """Extract discussion data from structured markup."""
        results = []
        
        # Look for QAPage structured data
        jsonld_pattern = r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>'
        
        for match in re.finditer(jsonld_pattern, html_content, re.IGNORECASE | re.DOTALL):
            try:
                json_content = match.group(1).strip()
                data = json.loads(json_content)
                
                if isinstance(data, dict):
                    data = [data]
                
                for item in data:
                    if item.get('@type') == 'QAPage':
                        qa_result = self._extract_from_qa_page(item)
                        if qa_result:
                            results.append(qa_result)
                
            except json.JSONDecodeError:
                continue
        
        return results
    
    def _extract_from_qa_page(self, qa_data: Dict[str, Any]) -> Optional[ExtractionResult]:
        """Extract discussion from QAPage structured data."""
        try:
            title = qa_data.get('name', 'Q&A Discussion')
            
            # Extract main entity (question)
            main_entity = qa_data.get('mainEntity', {})
            question_text = main_entity.get('text', '')
            
            # Extract accepted answer
            accepted_answer = main_entity.get('acceptedAnswer', {})
            answer_text = accepted_answer.get('text', '') if accepted_answer else ''
            
            # Extract all answers
            suggested_answers = main_entity.get('suggestedAnswer', [])
            if not isinstance(suggested_answers, list):
                suggested_answers = [suggested_answers] if suggested_answers else []
            
            # Create Q&A pairs
            qa_pairs = []
            if question_text and answer_text:
                qa_pairs.append({
                    'question': question_text,
                    'answer': answer_text,
                    'is_accepted': True
                })
            
            for answer in suggested_answers:
                if isinstance(answer, dict) and answer.get('text'):
                    qa_pairs.append({
                        'question': question_text,
                        'answer': answer['text'],
                        'is_accepted': False
                    })
            
            discussion_content = DiscussionContent(
                title=title,
                qa_pairs=qa_pairs
            )
            
            return ExtractionResult(
                success=True,
                content=discussion_content,
                extraction_method="structured_qa",
                confidence_score=0.95,
                warnings=[],
                metadata={
                    'schema_type': 'QAPage',
                    'qa_pairs_count': len(qa_pairs),
                    'extraction_source': 'structured_data'
                }
            )
        
        except Exception as e:
            self.logger.warning(f"Failed to extract QAPage: {e}")
            return None
    
    def _clean_html_content(self, html_content: str) -> str:
        """Clean HTML content to extract readable text."""
        # Remove script and style tags
        html_content = re.sub(r'<script[^>]*>.*?</script>', '', html_content, flags=re.DOTALL | re.IGNORECASE)
        html_content = re.sub(r'<style[^>]*>.*?</style>', '', html_content, flags=re.DOTALL | re.IGNORECASE)
        
        # Convert common formatting
        html_content = re.sub(r'<br[^>]*>', '\n', html_content, flags=re.IGNORECASE)
        html_content = re.sub(r'</p>', '\n', html_content, flags=re.IGNORECASE)
        
        # Remove all HTML tags
        html_content = re.sub(r'<[^>]+>', '', html_content)
        
        # Clean up whitespace
        html_content = re.sub(r'\n\s*\n', '\n', html_content)
        html_content = re.sub(r' +', ' ', html_content)
        
        # Decode HTML entities
        html_content = re.sub(r'&lt;', '<', html_content)
        html_content = re.sub(r'&gt;', '>', html_content)
        html_content = re.sub(r'&amp;', '&', html_content)
        html_content = re.sub(r'&quot;', '"', html_content)
        html_content = re.sub(r'&#39;', "'", html_content)
        
        return html_content.strip()


class ContentExtractor:
    """Main content extraction orchestrator for all content types."""
    
    def __init__(self):
        """Initialize the content extractor."""
        self.logger = logging.getLogger(__name__)
        self.video_parser = VideoContentParser()
        self.tutorial_parser = TutorialContentParser()
        self.discussion_parser = DiscussionContentParser()
    
    def extract_all_content(
        self, 
        scraped_data: Dict[str, Any], 
        base_url: str,
        content_types: Optional[List[str]] = None
    ) -> Dict[str, List[ExtractionResult]]:
        """Extract all types of content from scraped data.
        
        Args:
            scraped_data: Raw scraped content
            base_url: Base URL for resolving relative links
            content_types: Specific content types to extract (None for all)
            
        Returns:
            Dictionary mapping content types to extraction results
        """
        results = {}
        
        # Default to all content types if not specified
        if content_types is None:
            content_types = ['video', 'tutorial', 'discussion']
        
        # Extract videos
        if 'video' in content_types:
            try:
                video_results = self.video_parser.extract_video_content(scraped_data, base_url)
                results['video'] = video_results
            except Exception as e:
                self.logger.error(f"Video extraction failed: {e}")
                results['video'] = []
        
        # Extract tutorials
        if 'tutorial' in content_types:
            try:
                tutorial_results = self.tutorial_parser.extract_tutorial_content(scraped_data, base_url)
                results['tutorial'] = tutorial_results
            except Exception as e:
                self.logger.error(f"Tutorial extraction failed: {e}")
                results['tutorial'] = []
        
        # Extract discussions
        if 'discussion' in content_types:
            try:
                discussion_results = self.discussion_parser.extract_discussion_content(scraped_data, base_url)
                results['discussion'] = discussion_results
            except Exception as e:
                self.logger.error(f"Discussion extraction failed: {e}")
                results['discussion'] = []
        
        # Log extraction summary
        total_extracted = sum(len(results_list) for results_list in results.values())
        self.logger.info(
            f"Content extraction complete: {total_extracted} items extracted "
            f"({', '.join(f'{k}: {len(v)}' for k, v in results.items())})"
        )
        
        return results
    
    def get_extraction_statistics(self, results: Dict[str, List[ExtractionResult]]) -> Dict[str, Any]:
        """Generate statistics from extraction results.
        
        Args:
            results: Extraction results from extract_all_content
            
        Returns:
            Dictionary of extraction statistics
        """
        stats = {
            'total_items_extracted': 0,
            'extraction_success_rate': 0.0,
            'content_type_breakdown': {},
            'average_confidence_by_type': {},
            'warnings_count': 0,
            'extraction_methods_used': set()
        }
        
        total_items = 0
        successful_items = 0
        total_warnings = 0
        
        for content_type, result_list in results.items():
            type_stats = {
                'count': len(result_list),
                'successful': sum(1 for r in result_list if r.success),
                'average_confidence': 0.0,
                'methods_used': set()
            }
            
            if result_list:
                # Calculate average confidence
                confidences = [r.confidence_score for r in result_list if r.success]
                type_stats['average_confidence'] = sum(confidences) / len(confidences) if confidences else 0.0
                
                # Collect methods and warnings
                for result in result_list:
                    type_stats['methods_used'].add(result.extraction_method)
                    total_warnings += len(result.warnings)
                    stats['extraction_methods_used'].add(result.extraction_method)
            
            stats['content_type_breakdown'][content_type] = type_stats
            stats['average_confidence_by_type'][content_type] = type_stats['average_confidence']
            
            total_items += len(result_list)
            successful_items += type_stats['successful']
        
        stats['total_items_extracted'] = total_items
        stats['extraction_success_rate'] = successful_items / total_items if total_items > 0 else 0.0
        stats['warnings_count'] = total_warnings
        stats['extraction_methods_used'] = list(stats['extraction_methods_used'])
        
        return stats