"""URL crawling service for extracting learning content."""

import asyncio
import logging
import re
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from urllib.parse import urlparse, urljoin, urlunparse
from datetime import datetime

from ..clients.firecrawl_mcp_client import FirecrawlMCPClient, MCPError
from ..models.learning_resource import CrawledContent, VideoContent, TutorialContent, DiscussionContent
from ..config.firecrawl_config import FirecrawlConfig


@dataclass
class CrawlingOptions:
    """Options for configuring crawling behavior."""
    
    extract_videos: bool = True
    extract_tutorials: bool = True
    extract_discussions: bool = True
    follow_links: bool = False
    max_depth: int = 1
    include_images: bool = True
    include_code_examples: bool = True
    timeout_seconds: int = 30
    wait_for_dynamic_content: int = 2000  # milliseconds
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API calls."""
        return {
            'formats': ['markdown', 'html'],
            'includeTags': self._get_include_tags(),
            'excludeTags': self._get_exclude_tags(),
            'waitFor': self.wait_for_dynamic_content,
            'timeout': self.timeout_seconds * 1000,
            'followLinks': self.follow_links,
            'maxDepth': self.max_depth,
            'extractMedia': self.extract_videos,
            'extractCode': self.include_code_examples
        }
    
    def _get_include_tags(self) -> List[str]:
        """Get HTML tags to include in extraction."""
        base_tags = ['title', 'meta', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'div', 'span', 'a', 'ul', 'ol', 'li']
        
        if self.include_code_examples:
            base_tags.extend(['pre', 'code', 'script[type="text/javascript"]'])
        
        if self.include_images:
            base_tags.extend(['img', 'figure', 'figcaption'])
        
        if self.extract_videos:
            base_tags.extend(['video', 'iframe', 'embed', 'object'])
        
        if self.extract_discussions:
            base_tags.extend(['article', 'section', 'aside', 'blockquote'])
        
        return base_tags
    
    def _get_exclude_tags(self) -> List[str]:
        """Get HTML tags to exclude from extraction."""
        return [
            'script', 'style', 'nav', 'header', 'footer', 'sidebar',
            'advertisement', 'popup', 'modal', 'cookie-banner'
        ]


class URLValidator:
    """Validates URLs for crawling and extracts metadata."""
    
    def __init__(self):
        """Initialize the URL validator."""
        self.logger = logging.getLogger(__name__)
        
        # Known educational domains with specific handling
        self.educational_domains = {
            'coursera.org', 'edx.org', 'udemy.com', 'khanacademy.org',
            'pluralsight.com', 'lynda.com', 'skillshare.com',
            'freecodecamp.org', 'codecademy.com', 'udacity.com',
            'mit.edu', 'stanford.edu', 'harvard.edu', 'berkeley.edu'
        }
        
        # Video platform domains
        self.video_domains = {
            'youtube.com', 'youtu.be', 'vimeo.com', 'dailymotion.com',
            'wistia.com', 'brightcove.com'
        }
        
        # Documentation domains
        self.docs_domains = {
            'docs.python.org', 'developer.mozilla.org', 'reactjs.org',
            'angular.io', 'vuejs.org', 'nodejs.org', 'django.readthedocs.io'
        }
    
    def validate_url(self, url: str) -> Tuple[bool, Optional[str], Dict[str, Any]]:
        """Validate URL and extract metadata.
        
        Args:
            url: URL to validate
            
        Returns:
            Tuple of (is_valid, error_message, metadata)
        """
        if not url or not url.strip():
            return False, "URL cannot be empty", {}
        
        url = url.strip()
        
        try:
            parsed = urlparse(url)
            
            # Basic URL structure validation
            if not parsed.scheme:
                return False, "URL must include protocol (http:// or https://)", {}
            
            if parsed.scheme not in ['http', 'https']:
                return False, "Only HTTP and HTTPS protocols are supported", {}
            
            if not parsed.netloc:
                return False, "URL must include domain name", {}
            
            # Extract metadata
            metadata = self._extract_url_metadata(parsed)
            
            # Check for potentially problematic URLs
            warning_message = self._check_url_warnings(parsed)
            if warning_message:
                metadata['warnings'] = [warning_message]
            
            return True, None, metadata
            
        except Exception as e:
            return False, f"Invalid URL format: {e}", {}
    
    def _extract_url_metadata(self, parsed_url) -> Dict[str, Any]:
        """Extract metadata from parsed URL.
        
        Args:
            parsed_url: urllib.parse.ParseResult object
            
        Returns:
            Dictionary of URL metadata
        """
        domain = parsed_url.netloc.lower()
        path = parsed_url.path.lower()
        
        metadata = {
            'domain': domain,
            'path': parsed_url.path,
            'is_educational_domain': (any(edu_domain in domain for edu_domain in self.educational_domains) or 
                                     domain.endswith('.edu')),
            'is_video_platform': any(video_domain in domain for video_domain in self.video_domains),
            'is_documentation': any(doc_domain in domain for doc_domain in self.docs_domains),
            'estimated_content_type': self._estimate_content_type(domain, path),
            'crawling_difficulty': self._estimate_crawling_difficulty(domain, path)
        }
        
        return metadata
    
    def _estimate_content_type(self, domain: str, path: str) -> str:
        """Estimate the primary content type of the URL.
        
        Args:
            domain: Domain name
            path: URL path
            
        Returns:
            Estimated content type
        """
        # Video platforms
        if any(video_domain in domain for video_domain in self.video_domains):
            return 'video'
        
        # Documentation sites
        if any(doc_domain in domain for doc_domain in self.docs_domains):
            return 'documentation'
        
        # Path-based detection
        if any(indicator in path for indicator in ['tutorial', 'guide', 'how-to', 'walkthrough']):
            return 'tutorial'
        
        if any(indicator in path for indicator in ['forum', 'discussion', 'community', 'questions']):
            return 'discussion'
        
        if any(indicator in path for indicator in ['docs', 'documentation', 'reference', 'api']):
            return 'documentation'
        
        if any(indicator in path for indicator in ['course', 'lesson', 'learn', 'training']):
            return 'course'
        
        return 'article'  # Default
    
    def _estimate_crawling_difficulty(self, domain: str, path: str) -> str:
        """Estimate the difficulty of crawling the URL.
        
        Args:
            domain: Domain name
            path: URL path
            
        Returns:
            Difficulty level ('easy', 'medium', 'hard')
        """
        # Easy: Static documentation and simple sites
        if any(doc_domain in domain for doc_domain in self.docs_domains):
            return 'easy'
        
        # Hard: Complex interactive platforms
        if any(complex_domain in domain for complex_domain in ['coursera.org', 'udemy.com', 'linkedin.com']):
            return 'hard'
        
        # Medium: Most other educational content
        if any(edu_domain in domain for edu_domain in self.educational_domains) or domain.endswith('.edu'):
            return 'medium'
        
        # Check for dynamic content indicators
        if any(indicator in path for indicator in ['app', 'dashboard', 'player', 'interactive']):
            return 'hard'
        
        return 'medium'  # Default
    
    def _check_url_warnings(self, parsed_url) -> Optional[str]:
        """Check for potential issues with the URL.
        
        Args:
            parsed_url: urllib.parse.ParseResult object
            
        Returns:
            Warning message if issues found, None otherwise
        """
        domain = parsed_url.netloc.lower()
        
        # Check for paywalled content
        paywall_indicators = ['premium', 'pro', 'subscription', 'paid']
        if any(indicator in parsed_url.path.lower() for indicator in paywall_indicators):
            return "URL may contain paywalled content"
        
        # Check for login-required content
        auth_indicators = ['login', 'signin', 'register', 'account', 'dashboard']
        if any(indicator in parsed_url.path.lower() for indicator in auth_indicators):
            return "URL may require authentication"
        
        # Check for potentially dynamic content
        if 'javascript' in domain or 'spa' in parsed_url.path.lower():
            return "URL may contain heavy JavaScript content that requires longer wait times"
        
        return None
    
    def suggest_crawling_options(self, url: str) -> CrawlingOptions:
        """Suggest optimal crawling options for the given URL.
        
        Args:
            url: URL to analyze
            
        Returns:
            Suggested crawling options
        """
        is_valid, _, metadata = self.validate_url(url)
        
        if not is_valid:
            return CrawlingOptions()  # Default options
        
        options = CrawlingOptions()
        
        # Adjust based on content type
        content_type = metadata.get('estimated_content_type', 'article')
        
        if content_type == 'video':
            options.extract_videos = True
            options.extract_tutorials = False
            options.extract_discussions = False
            options.wait_for_dynamic_content = 5000  # Longer wait for video platforms
        
        elif content_type == 'documentation':
            options.extract_tutorials = True
            options.extract_videos = False
            options.extract_discussions = False
            options.include_code_examples = True
            options.follow_links = True
            options.max_depth = 2
        
        elif content_type == 'discussion':
            options.extract_discussions = True
            options.extract_videos = False
            options.extract_tutorials = False
            options.wait_for_dynamic_content = 3000
        
        # Adjust based on crawling difficulty
        difficulty = metadata.get('crawling_difficulty', 'medium')
        
        if difficulty == 'hard':
            options.timeout_seconds = 60
            options.wait_for_dynamic_content = 8000
            options.follow_links = False
        
        elif difficulty == 'easy':
            options.timeout_seconds = 15
            options.wait_for_dynamic_content = 1000
            options.follow_links = True
        
        return options


class ContentTypeDetector:
    """Detects and classifies content types from scraped data."""
    
    def __init__(self):
        """Initialize the content type detector."""
        self.logger = logging.getLogger(__name__)
        
        # Pattern matching for different content types
        self.video_patterns = [
            r'<video[^>]*>',
            r'<iframe[^>]*(?:youtube|vimeo|dailymotion)[^>]*>',
            r'player|video-container|media-player',
            r'duration|play-button|video-thumbnail'
        ]
        
        self.tutorial_patterns = [
            r'step\s*\d+|chapter\s*\d+|lesson\s*\d+',
            r'tutorial|guide|walkthrough|how-to',
            r'<pre[^>]*>.*?<\/pre>|<code[^>]*>.*?<\/code>',
            r'example|sample|demo'
        ]
        
        self.discussion_patterns = [
            r'comment|reply|post|thread',
            r'author|posted|replied|answered',
            r'upvote|downvote|like|dislike',
            r'forum|discussion|community'
        ]
    
    def detect_content_types(self, scraped_content: Dict[str, Any]) -> List[str]:
        """Detect content types present in scraped data.
        
        Args:
            scraped_content: Raw scraped content from MCP client
            
        Returns:
            List of detected content types
        """
        content_html = scraped_content.get('html', '')
        content_text = scraped_content.get('markdown', '') or scraped_content.get('text', '')
        combined_content = f"{content_html} {content_text}".lower()
        
        detected_types = []
        
        # Check for video content
        if any(re.search(pattern, combined_content, re.IGNORECASE) for pattern in self.video_patterns):
            detected_types.append('video')
        
        # Check for tutorial content
        if any(re.search(pattern, combined_content, re.IGNORECASE) for pattern in self.tutorial_patterns):
            detected_types.append('tutorial')
        
        # Check for discussion content
        if any(re.search(pattern, combined_content, re.IGNORECASE) for pattern in self.discussion_patterns):
            detected_types.append('discussion')
        
        # Default to article if no specific type detected
        if not detected_types:
            detected_types.append('article')
        
        self.logger.debug(f"Detected content types: {detected_types}")
        return detected_types
    
    def extract_content_metadata(self, scraped_content: Dict[str, Any]) -> Dict[str, Any]:
        """Extract general metadata from scraped content.
        
        Args:
            scraped_content: Raw scraped content from MCP client
            
        Returns:
            Dictionary of extracted metadata
        """
        metadata = {}
        
        # Extract title
        title = self._extract_title(scraped_content)
        if title:
            metadata['title'] = title
        
        # Extract description/summary
        description = self._extract_description(scraped_content)
        if description:
            metadata['description'] = description
        
        # Extract word count
        text_content = scraped_content.get('markdown', '') or scraped_content.get('text', '')
        if text_content:
            metadata['word_count'] = len(text_content.split())
        
        # Extract language
        language = self._detect_language(text_content)
        if language:
            metadata['language'] = language
        
        # Extract reading time estimate
        if 'word_count' in metadata:
            metadata['estimated_reading_time_minutes'] = max(1, metadata['word_count'] // 200)
        
        return metadata
    
    def _extract_title(self, scraped_content: Dict[str, Any]) -> Optional[str]:
        """Extract title from scraped content."""
        # Try multiple sources for title
        title_sources = [
            scraped_content.get('title'),
            scraped_content.get('metadata', {}).get('title'),
            scraped_content.get('metadata', {}).get('og:title')
        ]
        
        for title in title_sources:
            if title and title.strip():
                return title.strip()
        
        # Try to extract from HTML
        html_content = scraped_content.get('html', '')
        if html_content:
            title_match = re.search(r'<title[^>]*>(.*?)</title>', html_content, re.IGNORECASE | re.DOTALL)
            if title_match:
                return title_match.group(1).strip()
        
        return None
    
    def _extract_description(self, scraped_content: Dict[str, Any]) -> Optional[str]:
        """Extract description from scraped content."""
        # Try multiple sources for description
        desc_sources = [
            scraped_content.get('metadata', {}).get('description'),
            scraped_content.get('metadata', {}).get('og:description'),
            scraped_content.get('description')
        ]
        
        for desc in desc_sources:
            if desc and desc.strip():
                return desc.strip()
        
        # Try to extract from content
        text_content = scraped_content.get('markdown', '') or scraped_content.get('text', '')
        if text_content:
            # Take first paragraph as description
            paragraphs = text_content.split('\n\n')
            for paragraph in paragraphs:
                if len(paragraph.strip()) > 50:  # Minimum length for meaningful description
                    return paragraph.strip()[:500]  # Limit length
        
        return None
    
    def _detect_language(self, text_content: str) -> Optional[str]:
        """Simple language detection based on common patterns."""
        if not text_content or len(text_content) < 50:  # Reduced from 100 to 50
            return None
        
        # Simple heuristic-based language detection
        english_indicators = ['the', 'and', 'or', 'is', 'are', 'was', 'were', 'have', 'has']
        english_count = sum(1 for word in english_indicators if f' {word} ' in text_content.lower())
        
        if english_count >= 3:
            return 'en'
        
        return 'unknown'


class CrawlingService:
    """Main service for URL crawling and content extraction orchestration."""
    
    def __init__(self, firecrawl_client: FirecrawlMCPClient):
        """Initialize the crawling service.
        
        Args:
            firecrawl_client: Configured Firecrawl MCP client
        """
        self.firecrawl_client = firecrawl_client
        self.logger = logging.getLogger(__name__)
        self.url_validator = URLValidator()
        self.content_detector = ContentTypeDetector()
        
        # Statistics tracking
        self._crawl_stats = {
            'total_crawls': 0,
            'successful_crawls': 0,
            'failed_crawls': 0,
            'total_content_extracted': 0
        }
    
    async def crawl_url(
        self, 
        url: str, 
        options: Optional[CrawlingOptions] = None
    ) -> Tuple[CrawledContent, Dict[str, Any]]:
        """Crawl a single URL and extract learning content.
        
        Args:
            url: URL to crawl
            options: Crawling configuration options
            
        Returns:
            Tuple of (crawled content, crawling metadata)
            
        Raises:
            MCPError: If crawling fails or URL is invalid
        """
        self._crawl_stats['total_crawls'] += 1
        
        # Validate URL
        is_valid, error_message, url_metadata = self.url_validator.validate_url(url)
        if not is_valid:
            self._crawl_stats['failed_crawls'] += 1
            raise MCPError(f"Invalid URL: {error_message}")
        
        # Use suggested options if none provided
        if options is None:
            options = self.url_validator.suggest_crawling_options(url)
        
        self.logger.info(f"Crawling URL: {url} (estimated difficulty: {url_metadata.get('crawling_difficulty', 'unknown')})")
        
        crawl_metadata = {
            'url': url,
            'start_time': datetime.now().isoformat(),
            'url_metadata': url_metadata,
            'crawling_options': options.to_dict(),
            'content_types_detected': [],
            'extraction_stats': {},
            'warnings': url_metadata.get('warnings', [])
        }
        
        try:
            # Perform the actual crawling
            scraped_data = await self.firecrawl_client.scrape_url(url, options.to_dict())
            
            if not scraped_data:
                raise MCPError("No data returned from crawling operation")
            
            # Detect content types
            detected_types = self.content_detector.detect_content_types(scraped_data)
            crawl_metadata['content_types_detected'] = detected_types
            
            # Extract general metadata
            content_metadata = self.content_detector.extract_content_metadata(scraped_data)
            
            # Create base crawled content
            crawled_content = CrawledContent(
                url=url,
                title=content_metadata.get('title', 'Untitled'),
                metadata=content_metadata
            )
            
            # Extract specific content types
            extraction_stats = {}
            
            if options.extract_videos and 'video' in detected_types:
                videos = await self._extract_video_content(scraped_data, url)
                crawled_content.videos.extend(videos)
                extraction_stats['videos_extracted'] = len(videos)
            
            if options.extract_tutorials and 'tutorial' in detected_types:
                tutorials = await self._extract_tutorial_content(scraped_data, url)
                crawled_content.tutorials.extend(tutorials)
                extraction_stats['tutorials_extracted'] = len(tutorials)
            
            if options.extract_discussions and 'discussion' in detected_types:
                discussions = await self._extract_discussion_content(scraped_data, url)
                crawled_content.discussions.extend(discussions)
                extraction_stats['discussions_extracted'] = len(discussions)
            
            crawl_metadata['extraction_stats'] = extraction_stats
            crawl_metadata['end_time'] = datetime.now().isoformat()
            
            # Update statistics
            self._crawl_stats['successful_crawls'] += 1
            self._crawl_stats['total_content_extracted'] += sum(extraction_stats.values())
            
            self.logger.info(
                f"Successfully crawled {url}: {len(crawled_content.videos)} videos, "
                f"{len(crawled_content.tutorials)} tutorials, {len(crawled_content.discussions)} discussions"
            )
            
            return crawled_content, crawl_metadata
            
        except MCPError:
            self._crawl_stats['failed_crawls'] += 1
            raise
        except Exception as e:
            self._crawl_stats['failed_crawls'] += 1
            self.logger.error(f"Unexpected error crawling {url}: {e}")
            raise MCPError(f"Crawling failed: {e}")
    
    async def _extract_video_content(self, scraped_data: Dict[str, Any], base_url: str) -> List[VideoContent]:
        """Extract video content from scraped data.
        
        Args:
            scraped_data: Raw scraped content
            base_url: Base URL for resolving relative links
            
        Returns:
            List of extracted video content
        """
        videos = []
        html_content = scraped_data.get('html', '')
        
        # Extract embedded videos (YouTube, Vimeo, etc.)
        iframe_pattern = r'<iframe[^>]*src=["\']([^"\']*(?:youtube|vimeo|dailymotion)[^"\']*)["\'][^>]*>'
        iframe_matches = re.findall(iframe_pattern, html_content, re.IGNORECASE)
        
        for video_url in iframe_matches:
            video = VideoContent(
                title=self._extract_video_title(html_content, video_url),
                url=video_url,
                description=self._extract_video_description(html_content, video_url)
            )
            videos.append(video)
        
        # Extract HTML5 video elements
        video_pattern = r'<video[^>]*>.*?</video>'
        video_matches = re.findall(video_pattern, html_content, re.IGNORECASE | re.DOTALL)
        
        for video_html in video_matches:
            src_match = re.search(r'src=["\']([^"\']+)["\']', video_html)
            if src_match:
                video_url = urljoin(base_url, src_match.group(1))
                video = VideoContent(
                    title=self._extract_video_title_from_element(video_html),
                    url=video_url,
                    description="HTML5 video content"
                )
                videos.append(video)
        
        return videos
    
    async def _extract_tutorial_content(self, scraped_data: Dict[str, Any], base_url: str) -> List[TutorialContent]:
        """Extract tutorial content from scraped data.
        
        Args:
            scraped_data: Raw scraped content
            base_url: Base URL for resolving relative links
            
        Returns:
            List of extracted tutorial content
        """
        tutorials = []
        markdown_content = scraped_data.get('markdown', '')
        html_content = scraped_data.get('html', '')
        
        if markdown_content:
            # Extract code examples (flexible pattern for various formatting)
            code_examples = re.findall(r'```[\w]*\s*(.*?)\s*```', markdown_content, re.DOTALL)
            
            # Extract sections (headers) - handle indented markdown
            sections = re.findall(r'^\s*#{1,6}\s+(.+)$', markdown_content, re.MULTILINE)
            
            # Extract images
            images = re.findall(r'!\[.*?\]\(([^)]+)\)', markdown_content)
            
            tutorial = TutorialContent(
                title=scraped_data.get('title', 'Tutorial Content'),
                content=markdown_content,
                sections=sections,
                code_examples=code_examples,
                images=[urljoin(base_url, img) for img in images]
            )
            tutorials.append(tutorial)
        
        return tutorials
    
    async def _extract_discussion_content(self, scraped_data: Dict[str, Any], base_url: str) -> List[DiscussionContent]:
        """Extract discussion content from scraped data.
        
        Args:
            scraped_data: Raw scraped content
            base_url: Base URL for resolving relative links
            
        Returns:
            List of extracted discussion content
        """
        discussions = []
        html_content = scraped_data.get('html', '')
        
        # Simple extraction of posts/comments (this would be more sophisticated in practice)
        comment_patterns = [
            r'<div[^>]*class="[^"]*comment[^"]*"[^>]*>(.*?)</div>',
            r'<article[^>]*class="[^"]*post[^"]*"[^>]*>(.*?)</article>',
            r'<div[^>]*class="[^"]*reply[^"]*"[^>]*>(.*?)</div>'
        ]
        
        posts = []
        comments = []
        
        for pattern in comment_patterns:
            matches = re.findall(pattern, html_content, re.IGNORECASE | re.DOTALL)
            for match in matches:
                # Clean HTML and extract text
                text_content = re.sub(r'<[^>]+>', '', match).strip()
                if len(text_content) > 20:  # Minimum content length
                    post_data = {
                        'content': text_content[:1000],  # Limit length
                        'timestamp': 'unknown',
                        'author': 'unknown'
                    }
                    
                    if 'comment' in pattern:
                        comments.append(post_data)
                    else:
                        posts.append(post_data)
        
        if posts or comments:
            discussion = DiscussionContent(
                title=scraped_data.get('title', 'Discussion Content'),
                posts=posts,
                comments=comments
            )
            discussions.append(discussion)
        
        return discussions
    
    def _extract_video_title(self, html_content: str, video_url: str) -> str:
        """Extract video title from HTML context."""
        # Try to find title near the video element
        patterns = [
            (r'<h[1-6][^>]*>([^<]*video[^<]*)</h[1-6]>', 1),  # Header with video mention
            (r'title=["\']([^"\']+)["\']', 1),                # Title attribute
            (r'<title[^>]*>([^<]+)</title>', 1)               # Page title
        ]
        
        for pattern, group_num in patterns:
            match = re.search(pattern, html_content, re.IGNORECASE)
            if match:
                try:
                    return match.group(group_num).strip()
                except IndexError:
                    continue
        
        return "Video Content"
    
    def _extract_video_description(self, html_content: str, video_url: str) -> str:
        """Extract video description from HTML context."""
        # Simple description extraction (would be more sophisticated in practice)
        return "Extracted video content"
    
    def _extract_video_title_from_element(self, video_html: str) -> str:
        """Extract title from video HTML element."""
        title_match = re.search(r'title=["\']([^"\']+)["\']', video_html)
        if title_match:
            return title_match.group(1)
        return "HTML5 Video"
    
    async def validate_url_batch(self, urls: List[str]) -> Dict[str, Tuple[bool, Optional[str], Dict[str, Any]]]:
        """Validate multiple URLs in batch.
        
        Args:
            urls: List of URLs to validate
            
        Returns:
            Dictionary mapping URLs to validation results
        """
        results = {}
        
        for url in urls:
            try:
                results[url] = self.url_validator.validate_url(url)
            except Exception as e:
                results[url] = (False, f"Validation error: {e}", {})
        
        return results
    
    def get_crawling_statistics(self) -> Dict[str, Any]:
        """Get crawling service statistics.
        
        Returns:
            Dictionary of service statistics
        """
        stats = self._crawl_stats.copy()
        
        if stats['total_crawls'] > 0:
            stats['success_rate'] = stats['successful_crawls'] / stats['total_crawls']
            stats['average_content_per_crawl'] = stats['total_content_extracted'] / stats['successful_crawls'] if stats['successful_crawls'] > 0 else 0
        else:
            stats['success_rate'] = 0.0
            stats['average_content_per_crawl'] = 0.0
        
        return stats
    
    def reset_statistics(self) -> None:
        """Reset crawling statistics."""
        self._crawl_stats = {
            'total_crawls': 0,
            'successful_crawls': 0,
            'failed_crawls': 0,
            'total_content_extracted': 0
        }