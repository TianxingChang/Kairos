"""Content processing service for formatting and structure preservation."""

import re
import json
import html
import logging
from typing import Dict, List, Any, Optional, Tuple, Union
from dataclasses import dataclass, field
from pathlib import Path
from datetime import datetime, timezone
from urllib.parse import urljoin, urlparse
import hashlib

from ..models.learning_resource import CrawledContent, VideoContent, TutorialContent, DiscussionContent


@dataclass
class ProcessingOptions:
    """Configuration options for content processing."""
    
    preserve_formatting: bool = True
    convert_to_markdown: bool = True
    extract_code_blocks: bool = True
    process_links: bool = True
    download_images: bool = False
    generate_table_of_contents: bool = True
    add_metadata_headers: bool = True
    clean_html: bool = True
    normalize_whitespace: bool = True
    extract_quotes: bool = True
    
    # Markdown formatting options
    use_github_flavored_markdown: bool = True
    code_fence_language_detection: bool = True
    convert_tables: bool = True
    convert_lists: bool = True
    
    # Content enhancement options
    add_reading_time: bool = True
    add_word_count: bool = True
    highlight_key_terms: bool = False
    generate_summary: bool = False


@dataclass
class ProcessedContent:
    """Represents processed content with enhanced structure."""
    
    title: str
    content: str
    format: str  # markdown, html, plain_text
    metadata: Dict[str, Any] = field(default_factory=dict)
    table_of_contents: List[Dict[str, Any]] = field(default_factory=list)
    code_blocks: List[Dict[str, Any]] = field(default_factory=list)
    images: List[Dict[str, Any]] = field(default_factory=list)
    links: List[Dict[str, Any]] = field(default_factory=list)
    quotes: List[str] = field(default_factory=list)
    statistics: Dict[str, Any] = field(default_factory=dict)
    processing_notes: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'title': self.title,
            'content': self.content,
            'format': self.format,
            'metadata': self.metadata,
            'table_of_contents': self.table_of_contents,
            'code_blocks': self.code_blocks,
            'images': self.images,
            'links': self.links,
            'quotes': self.quotes,
            'statistics': self.statistics,
            'processing_notes': self.processing_notes
        }


class MarkdownConverter:
    """Converts HTML content to well-formatted Markdown."""
    
    def __init__(self, options: ProcessingOptions):
        """Initialize the markdown converter."""
        self.options = options
        self.logger = logging.getLogger(__name__)
        
        # HTML to Markdown conversion rules
        self.conversion_rules = [
            # Headers
            (r'<h1[^>]*>(.*?)</h1>', r'# \1\n\n'),
            (r'<h2[^>]*>(.*?)</h2>', r'## \1\n\n'),
            (r'<h3[^>]*>(.*?)</h3>', r'### \1\n\n'),
            (r'<h4[^>]*>(.*?)</h4>', r'#### \1\n\n'),
            (r'<h5[^>]*>(.*?)</h5>', r'##### \1\n\n'),
            (r'<h6[^>]*>(.*?)</h6>', r'###### \1\n\n'),
            
            # Text formatting
            (r'<strong[^>]*>(.*?)</strong>', r'**\1**'),
            (r'<b[^>]*>(.*?)</b>', r'**\1**'),
            (r'<em[^>]*>(.*?)</em>', r'*\1*'),
            (r'<i[^>]*>(.*?)</i>', r'*\1*'),
            (r'<u[^>]*>(.*?)</u>', r'<u>\1</u>'),
            (r'<del[^>]*>(.*?)</del>', r'~~\1~~'),
            (r'<strike[^>]*>(.*?)</strike>', r'~~\1~~'),
            
            # Code
            (r'<code[^>]*>(.*?)</code>', r'`\1`'),
            (r'<pre[^>]*><code[^>]*>(.*?)</code></pre>', self._handle_code_block),
            (r'<pre[^>]*>(.*?)</pre>', r'```\n\1\n```\n\n'),
            
            # Links
            (r'<a[^>]*href=["\']([^"\']*)["\'][^>]*>(.*?)</a>', r'[\2](\1)'),
            
            # Images
            (r'<img[^>]*src=["\']([^"\']*)["\'][^>]*alt=["\']([^"\']*)["\'][^>]*/?>', r'![\2](\1)'),
            (r'<img[^>]*src=["\']([^"\']*)["\'][^>]*/?>', r'![](\1)'),
            
            # Lists
            (r'<ul[^>]*>', '\n'),
            (r'</ul>', '\n'),
            (r'<ol[^>]*>', '\n'),
            (r'</ol>', '\n'),
            (r'<li[^>]*>(.*?)</li>', r'- \1\n'),
            
            # Paragraphs and line breaks
            (r'<p[^>]*>(.*?)</p>', r'\1\n\n'),
            (r'<br[^>]*/?>', '\n'),
            (r'<hr[^>]*/?>', '\n---\n\n'),
            
            # Blockquotes
            (r'<blockquote[^>]*>(.*?)</blockquote>', self._handle_blockquote),
            
            # Tables (basic conversion)
            (r'<table[^>]*>', '\n'),
            (r'</table>', '\n'),
            (r'<tr[^>]*>', ''),
            (r'</tr>', '|\n'),
            (r'<th[^>]*>(.*?)</th>', r'| \1 '),
            (r'<td[^>]*>(.*?)</td>', r'| \1 '),
            
            # Divs and spans
            (r'<div[^>]*>(.*?)</div>', r'\1\n'),
            (r'<span[^>]*>(.*?)</span>', r'\1'),
            
            # Remove other HTML tags
            (r'<[^>]+>', ''),
        ]
    
    def convert_to_markdown(self, html_content: str) -> str:
        """Convert HTML content to Markdown."""
        if not html_content:
            return ""
        
        # Clean up the HTML first
        content = self._clean_html(html_content)
        
        # Apply conversion rules
        for pattern, replacement in self.conversion_rules:
            if callable(replacement):
                content = re.sub(pattern, replacement, content, flags=re.DOTALL | re.IGNORECASE)
            else:
                content = re.sub(pattern, replacement, content, flags=re.DOTALL | re.IGNORECASE)
        
        # Clean up the resulting markdown
        content = self._clean_markdown(content)
        
        return content
    
    def _clean_html(self, html_content: str) -> str:
        """Clean HTML content before conversion."""
        # Remove script and style tags
        content = re.sub(r'<script[^>]*>.*?</script>', '', html_content, flags=re.DOTALL | re.IGNORECASE)
        content = re.sub(r'<style[^>]*>.*?</style>', '', content, flags=re.DOTALL | re.IGNORECASE)
        
        # Remove HTML comments
        content = re.sub(r'<!--.*?-->', '', content, flags=re.DOTALL)
        
        # Decode HTML entities
        content = html.unescape(content)
        
        return content
    
    def _clean_markdown(self, markdown_content: str) -> str:
        """Clean up markdown content."""
        # Normalize whitespace
        if self.options.normalize_whitespace:
            # Remove extra whitespace
            content = re.sub(r' +', ' ', markdown_content)
            
            # Normalize line breaks
            content = re.sub(r'\n\s*\n\s*\n+', '\n\n', content)
            
            # Remove trailing whitespace
            content = re.sub(r' +$', '', content, flags=re.MULTILINE)
        else:
            content = markdown_content
        
        # Clean up markdown artifacts
        content = re.sub(r'\*\*\s*\*\*', '', content)  # Empty bold
        content = re.sub(r'\*\s*\*', '', content)  # Empty italic
        content = re.sub(r'`\s*`', '', content)  # Empty code
        
        return content.strip()
    
    def _handle_code_block(self, match) -> str:
        """Handle code block conversion with language detection."""
        code_content = match.group(1)
        
        if self.options.code_fence_language_detection:
            # Try to detect language from code content
            language = self._detect_code_language(code_content)
            return f"```{language}\n{code_content}\n```\n\n"
        else:
            return f"```\n{code_content}\n```\n\n"
    
    def _handle_blockquote(self, match) -> str:
        """Handle blockquote conversion."""
        quote_content = match.group(1)
        # Add > prefix to each line
        lines = quote_content.split('\n')
        quoted_lines = [f"> {line}" if line.strip() else ">" for line in lines]
        return '\n'.join(quoted_lines) + '\n\n'
    
    def _detect_code_language(self, code_content: str) -> str:
        """Detect programming language from code content."""
        code_lower = code_content.lower()
        
        # Language detection patterns
        language_patterns = {
            'python': [r'def\s+\w+', r'import\s+\w+', r'from\s+\w+\s+import', r'print\s*\('],
            'javascript': [r'function\s+\w+', r'var\s+\w+', r'let\s+\w+', r'const\s+\w+', r'console\.log'],
            'java': [r'public\s+class', r'public\s+static\s+void\s+main', r'System\.out\.println'],
            'html': [r'<html', r'<div', r'<p>', r'<!DOCTYPE'],
            'css': [r'\w+\s*{', r'color\s*:', r'background\s*:', r'margin\s*:'],
            'sql': [r'SELECT\s+', r'FROM\s+', r'WHERE\s+', r'INSERT\s+INTO'],
            'bash': [r'#!/bin/bash', r'\$\w+', r'echo\s+', r'cd\s+'],
            'json': [r'{\s*"', r'"\s*:\s*"', r'"\s*:\s*\{'],
            'xml': [r'<\?xml', r'<\w+[^>]*>', r'</\w+>'],
            'markdown': [r'^#+\s+', r'\*\*\w+\*\*', r'\[.*\]\(.*\)'],
        }
        
        for language, patterns in language_patterns.items():
            if any(re.search(pattern, code_content, re.IGNORECASE | re.MULTILINE) for pattern in patterns):
                return language
        
        return ''  # No language detected


class ContentStructureAnalyzer:
    """Analyzes and extracts structure from content."""
    
    def __init__(self, options: ProcessingOptions):
        """Initialize the structure analyzer."""
        self.options = options
        self.logger = logging.getLogger(__name__)
    
    def analyze_structure(self, content: str, format_type: str = 'markdown') -> Dict[str, Any]:
        """Analyze content structure and extract components."""
        analysis = {
            'table_of_contents': [],
            'code_blocks': [],
            'images': [],
            'links': [],
            'quotes': [],
            'statistics': {}
        }
        
        if format_type == 'markdown':
            analysis['table_of_contents'] = self._extract_markdown_toc(content)
            analysis['code_blocks'] = self._extract_markdown_code_blocks(content)
            analysis['images'] = self._extract_markdown_images(content)
            analysis['links'] = self._extract_markdown_links(content)
            analysis['quotes'] = self._extract_markdown_quotes(content)
        
        # Calculate statistics
        analysis['statistics'] = self._calculate_content_statistics(content)
        
        return analysis
    
    def _extract_markdown_toc(self, content: str) -> List[Dict[str, Any]]:
        """Extract table of contents from markdown headers."""
        toc = []
        header_pattern = r'^(#{1,6})\s+(.+)$'
        
        for match in re.finditer(header_pattern, content, re.MULTILINE):
            level = len(match.group(1))
            title = match.group(2).strip()
            
            # Generate anchor
            anchor = re.sub(r'[^\w\s-]', '', title.lower())
            anchor = re.sub(r'[\s_]+', '-', anchor)
            
            toc.append({
                'level': level,
                'title': title,
                'anchor': anchor,
                'line_number': content[:match.start()].count('\n') + 1
            })
        
        return toc
    
    def _extract_markdown_code_blocks(self, content: str) -> List[Dict[str, Any]]:
        """Extract code blocks from markdown content."""
        code_blocks = []
        
        # Fenced code blocks
        fenced_pattern = r'```(\w+)?\n(.*?)\n```'
        for i, match in enumerate(re.finditer(fenced_pattern, content, re.DOTALL), 1):
            language = match.group(1) or 'text'
            code = match.group(2)
            
            code_blocks.append({
                'type': 'fenced',
                'language': language,
                'code': code,
                'line_count': code.count('\n') + 1,
                'character_count': len(code),
                'block_number': i
            })
        
        # Inline code
        inline_pattern = r'`([^`]+)`'
        inline_matches = re.findall(inline_pattern, content)
        
        for i, code in enumerate(inline_matches, 1):
            code_blocks.append({
                'type': 'inline',
                'language': 'text',
                'code': code,
                'line_count': 1,
                'character_count': len(code),
                'block_number': i
            })
        
        return code_blocks
    
    def _extract_markdown_images(self, content: str) -> List[Dict[str, Any]]:
        """Extract images from markdown content."""
        images = []
        image_pattern = r'!\[([^\]]*)\]\(([^)]+)\)'
        
        for i, match in enumerate(re.finditer(image_pattern, content), 1):
            alt_text = match.group(1)
            url = match.group(2)
            
            images.append({
                'alt_text': alt_text,
                'url': url,
                'is_local': not url.startswith(('http://', 'https://')),
                'image_number': i
            })
        
        return images
    
    def _extract_markdown_links(self, content: str) -> List[Dict[str, Any]]:
        """Extract links from markdown content."""
        links = []
        link_pattern = r'\[([^\]]+)\]\(([^)]+)\)'
        
        for i, match in enumerate(re.finditer(link_pattern, content), 1):
            text = match.group(1)
            url = match.group(2)
            
            # Skip image links (already handled)
            if match.start() > 0 and content[match.start() - 1] == '!':
                continue
            
            parsed_url = urlparse(url)
            
            links.append({
                'text': text,
                'url': url,
                'domain': parsed_url.netloc if parsed_url.netloc else 'local',
                'is_external': bool(parsed_url.netloc),
                'link_number': i
            })
        
        return links
    
    def _extract_markdown_quotes(self, content: str) -> List[str]:
        """Extract blockquotes from markdown content."""
        quotes = []
        
        # Find blockquote sections
        lines = content.split('\n')
        current_quote = []
        
        for line in lines:
            if line.strip().startswith('>'):
                # Remove > and leading whitespace
                quote_line = line.strip()[1:].strip()
                current_quote.append(quote_line)
            else:
                if current_quote:
                    # End of quote block
                    quote_text = ' '.join(current_quote).strip()
                    if quote_text:
                        quotes.append(quote_text)
                    current_quote = []
        
        # Handle quote at end of content
        if current_quote:
            quote_text = ' '.join(current_quote).strip()
            if quote_text:
                quotes.append(quote_text)
        
        return quotes
    
    def _calculate_content_statistics(self, content: str) -> Dict[str, Any]:
        """Calculate various content statistics."""
        # Basic counts
        word_count = len(content.split())
        character_count = len(content)
        line_count = content.count('\n') + 1
        paragraph_count = len([p for p in content.split('\n\n') if p.strip()])
        
        # Reading time estimation (average 200 words per minute)
        reading_time_minutes = max(1, word_count // 200)
        
        # Complexity indicators
        avg_sentence_length = 0
        sentences = re.split(r'[.!?]+', content)
        if sentences:
            total_words = sum(len(sentence.split()) for sentence in sentences if sentence.strip())
            avg_sentence_length = total_words / len([s for s in sentences if s.strip()])
        
        return {
            'word_count': word_count,
            'character_count': character_count,
            'line_count': line_count,
            'paragraph_count': paragraph_count,
            'reading_time_minutes': reading_time_minutes,
            'average_sentence_length': round(avg_sentence_length, 1),
            'content_density': round(word_count / max(paragraph_count, 1), 1)
        }


class ContentEnhancer:
    """Enhances content with additional features and formatting."""
    
    def __init__(self, options: ProcessingOptions):
        """Initialize the content enhancer."""
        self.options = options
        self.logger = logging.getLogger(__name__)
    
    def enhance_content(self, processed_content: ProcessedContent) -> ProcessedContent:
        """Enhance processed content with additional features."""
        enhanced = processed_content
        
        # Add metadata headers
        if self.options.add_metadata_headers:
            enhanced.content = self._add_metadata_header(enhanced)
        
        # Generate table of contents
        if self.options.generate_table_of_contents and enhanced.table_of_contents:
            enhanced.content = self._add_table_of_contents(enhanced)
        
        # Highlight key terms
        if self.options.highlight_key_terms:
            enhanced.content = self._highlight_key_terms(enhanced.content)
        
        return enhanced
    
    def _add_metadata_header(self, content: ProcessedContent) -> str:
        """Add metadata header to content."""
        metadata_lines = []
        
        # Title
        if content.title:
            metadata_lines.append(f"# {content.title}")
            metadata_lines.append("")
        
        # Statistics
        if self.options.add_reading_time and 'reading_time_minutes' in content.statistics:
            reading_time = content.statistics['reading_time_minutes']
            metadata_lines.append(f"**Reading Time:** ~{reading_time} minute{'s' if reading_time != 1 else ''}")
        
        if self.options.add_word_count and 'word_count' in content.statistics:
            word_count = content.statistics['word_count']
            metadata_lines.append(f"**Word Count:** {word_count:,} words")
        
        # Processing info
        if content.metadata.get('original_url'):
            metadata_lines.append(f"**Source:** {content.metadata['original_url']}")
        
        if content.metadata.get('processed_date'):
            metadata_lines.append(f"**Processed:** {content.metadata['processed_date']}")
        
        if metadata_lines:
            metadata_lines.append("")
            metadata_lines.append("---")
            metadata_lines.append("")
        
        return '\n'.join(metadata_lines) + content.content
    
    def _add_table_of_contents(self, content: ProcessedContent) -> str:
        """Add table of contents to content."""
        if not content.table_of_contents:
            return content.content
        
        toc_lines = ["## Table of Contents", ""]
        
        for item in content.table_of_contents:
            indent = "  " * (item['level'] - 1)
            toc_lines.append(f"{indent}- [{item['title']}](#{item['anchor']})")
        
        toc_lines.extend(["", "---", ""])
        
        return '\n'.join(toc_lines) + content.content
    
    def _highlight_key_terms(self, content: str) -> str:
        """Highlight key programming and technical terms."""
        # Define key terms to highlight
        key_terms = [
            # Programming concepts
            'function', 'variable', 'class', 'method', 'object',
            'algorithm', 'data structure', 'array', 'list', 'dictionary',
            'loop', 'condition', 'exception', 'debugging', 'testing',
            
            # Technologies
            'API', 'REST', 'HTTP', 'JSON', 'XML', 'SQL', 'NoSQL',
            'Docker', 'Kubernetes', 'CI/CD', 'Git', 'GitHub',
            
            # Languages
            'Python', 'JavaScript', 'Java', 'C++', 'Go', 'Rust'
        ]
        
        enhanced_content = content
        
        for term in key_terms:
            # Highlight whole word matches, case insensitive
            pattern = r'\b' + re.escape(term) + r'\b'
            enhanced_content = re.sub(
                pattern, 
                f'**{term}**', 
                enhanced_content, 
                flags=re.IGNORECASE
            )
        
        return enhanced_content


class ContentProcessorService:
    """Main service for processing and formatting learning content."""
    
    def __init__(self, options: Optional[ProcessingOptions] = None):
        """Initialize the content processor service.
        
        Args:
            options: Processing configuration options
        """
        self.options = options or ProcessingOptions()
        self.logger = logging.getLogger(__name__)
        
        # Initialize components
        self.markdown_converter = MarkdownConverter(self.options)
        self.structure_analyzer = ContentStructureAnalyzer(self.options)
        self.content_enhancer = ContentEnhancer(self.options)
        
        # Processing statistics
        self._stats = {
            'items_processed': 0,
            'successful_conversions': 0,
            'failed_conversions': 0,
            'total_processing_time': 0.0
        }
    
    def process_crawled_content(self, crawled_content: CrawledContent) -> Dict[str, List[ProcessedContent]]:
        """Process all content from a crawled resource.
        
        Args:
            crawled_content: The crawled content to process
            
        Returns:
            Dictionary mapping content types to processed content lists
        """
        results = {
            'videos': [],
            'tutorials': [],
            'discussions': []
        }
        
        # Process videos
        for video in crawled_content.videos:
            processed = self.process_video_content(video)
            if processed:
                results['videos'].append(processed)
        
        # Process tutorials
        for tutorial in crawled_content.tutorials:
            processed = self.process_tutorial_content(tutorial)
            if processed:
                results['tutorials'].append(processed)
        
        # Process discussions
        for discussion in crawled_content.discussions:
            processed = self.process_discussion_content(discussion)
            if processed:
                results['discussions'].append(processed)
        
        self.logger.info(
            f"Processed crawled content: {len(results['videos'])} videos, "
            f"{len(results['tutorials'])} tutorials, {len(results['discussions'])} discussions"
        )
        
        return results
    
    def process_video_content(self, video: VideoContent) -> Optional[ProcessedContent]:
        """Process video content into structured format."""
        try:
            self._stats['items_processed'] += 1
            start_time = datetime.now()
            
            # Create basic processed content
            processed = ProcessedContent(
                title=video.title or "Video Content",
                content="",
                format="markdown"
            )
            
            # Build content
            content_parts = []
            
            # Video information
            content_parts.append(f"# {processed.title}")
            content_parts.append("")
            
            if video.description:
                content_parts.append("## Description")
                content_parts.append(video.description)
                content_parts.append("")
            
            # Video details
            content_parts.append("## Video Details")
            content_parts.append(f"- **URL:** {video.url}")
            
            if video.duration:
                minutes = video.duration // 60
                seconds = video.duration % 60
                content_parts.append(f"- **Duration:** {minutes}:{seconds:02d}")
            
            if video.file_size_mb:
                content_parts.append(f"- **File Size:** {video.file_size_mb:.1f} MB")
            
            if video.thumbnail_url:
                content_parts.append(f"- **Thumbnail:** ![Thumbnail]({video.thumbnail_url})")
            
            if video.download_path:
                content_parts.append(f"- **Downloaded:** {video.download_path}")
            
            content_parts.append("")
            
            # Combine content
            processed.content = '\n'.join(content_parts)
            
            # Set metadata
            processed.metadata = {
                'content_type': 'video',
                'original_url': video.url,
                'duration_seconds': video.duration,
                'file_size_mb': video.file_size_mb,
                'processed_date': datetime.now(timezone.utc).isoformat()
            }
            
            # Analyze structure
            structure = self.structure_analyzer.analyze_structure(processed.content)
            processed.table_of_contents = structure['table_of_contents']
            processed.images = structure['images']
            processed.links = structure['links']
            processed.statistics = structure['statistics']
            
            # Enhance content
            if self.options.add_metadata_headers or self.options.generate_table_of_contents:
                processed = self.content_enhancer.enhance_content(processed)
            
            # Update statistics
            processing_time = (datetime.now() - start_time).total_seconds()
            self._stats['total_processing_time'] += processing_time
            self._stats['successful_conversions'] += 1
            
            return processed
            
        except Exception as e:
            self.logger.error(f"Failed to process video content: {e}")
            self._stats['failed_conversions'] += 1
            return None
    
    def process_tutorial_content(self, tutorial: TutorialContent) -> Optional[ProcessedContent]:
        """Process tutorial content with enhanced formatting."""
        try:
            self._stats['items_processed'] += 1
            start_time = datetime.now()
            
            # Determine input format and convert to markdown
            if self.options.convert_to_markdown:
                # If content looks like HTML, convert it
                if '<' in tutorial.content and '>' in tutorial.content:
                    markdown_content = self.markdown_converter.convert_to_markdown(tutorial.content)
                else:
                    markdown_content = tutorial.content
            else:
                markdown_content = tutorial.content
            
            # Create processed content
            processed = ProcessedContent(
                title=tutorial.title,
                content=markdown_content,
                format="markdown"
            )
            
            # Set metadata
            processed.metadata = {
                'content_type': 'tutorial',
                'sections_count': len(tutorial.sections),
                'code_examples_count': len(tutorial.code_examples),
                'images_count': len(tutorial.images),
                'processed_date': datetime.now(timezone.utc).isoformat()
            }
            
            # Analyze structure
            structure = self.structure_analyzer.analyze_structure(processed.content)
            processed.table_of_contents = structure['table_of_contents']
            processed.code_blocks = structure['code_blocks']
            processed.images = structure['images']
            processed.links = structure['links']
            processed.quotes = structure['quotes']
            processed.statistics = structure['statistics']
            
            # Add processing notes
            if tutorial.code_examples:
                processed.processing_notes.append(f"Extracted {len(tutorial.code_examples)} code examples")
            if tutorial.images:
                processed.processing_notes.append(f"Found {len(tutorial.images)} images")
            
            # Enhance content
            processed = self.content_enhancer.enhance_content(processed)
            
            # Update statistics
            processing_time = (datetime.now() - start_time).total_seconds()
            self._stats['total_processing_time'] += processing_time
            self._stats['successful_conversions'] += 1
            
            return processed
            
        except Exception as e:
            self.logger.error(f"Failed to process tutorial content: {e}")
            self._stats['failed_conversions'] += 1
            return None
    
    def process_discussion_content(self, discussion: DiscussionContent) -> Optional[ProcessedContent]:
        """Process discussion content with structured formatting."""
        try:
            self._stats['items_processed'] += 1
            start_time = datetime.now()
            
            # Build formatted discussion content
            content_parts = []
            
            # Title
            content_parts.append(f"# {discussion.title}")
            content_parts.append("")
            
            # Posts
            if discussion.posts:
                content_parts.append("## Posts")
                content_parts.append("")
                
                for i, post in enumerate(discussion.posts, 1):
                    if isinstance(post, dict):
                        author = post.get('author', 'Unknown')
                        content = post.get('content', '')
                        timestamp = post.get('timestamp', 'Unknown')
                        
                        content_parts.append(f"### Post {i} - {author}")
                        if timestamp != 'Unknown':
                            content_parts.append(f"*Posted: {timestamp}*")
                        content_parts.append("")
                        content_parts.append(content)
                    else:
                        content_parts.append(f"### Post {i}")
                        content_parts.append(str(post))
                    
                    content_parts.append("")
            
            # Comments
            if discussion.comments:
                content_parts.append("## Comments")
                content_parts.append("")
                
                for i, comment in enumerate(discussion.comments, 1):
                    if isinstance(comment, dict):
                        author = comment.get('author', 'Unknown')
                        content = comment.get('content', '')
                        
                        content_parts.append(f"**Comment {i} - {author}:**")
                        content_parts.append(content)
                    else:
                        content_parts.append(f"**Comment {i}:**")
                        content_parts.append(str(comment))
                    
                    content_parts.append("")
            
            # Q&A Pairs
            if discussion.qa_pairs:
                content_parts.append("## Questions & Answers")
                content_parts.append("")
                
                for i, qa in enumerate(discussion.qa_pairs, 1):
                    if isinstance(qa, dict):
                        question = qa.get('question', '')
                        answer = qa.get('answer', '')
                        
                        content_parts.append(f"### Q&A {i}")
                        
                        if question:
                            content_parts.append("**Question:**")
                            content_parts.append(question)
                            content_parts.append("")
                        
                        if answer:
                            content_parts.append("**Answer:**")
                            content_parts.append(answer)
                        
                        content_parts.append("")
            
            # Create processed content
            processed = ProcessedContent(
                title=discussion.title,
                content='\n'.join(content_parts),
                format="markdown"
            )
            
            # Set metadata
            processed.metadata = {
                'content_type': 'discussion',
                'posts_count': len(discussion.posts),
                'comments_count': len(discussion.comments),
                'qa_pairs_count': len(discussion.qa_pairs),
                'processed_date': datetime.now(timezone.utc).isoformat()
            }
            
            # Analyze structure
            structure = self.structure_analyzer.analyze_structure(processed.content)
            processed.table_of_contents = structure['table_of_contents']
            processed.code_blocks = structure['code_blocks']
            processed.images = structure['images']
            processed.links = structure['links']
            processed.quotes = structure['quotes']
            processed.statistics = structure['statistics']
            
            # Add processing notes
            if discussion.posts:
                processed.processing_notes.append(f"Processed {len(discussion.posts)} posts")
            if discussion.comments:
                processed.processing_notes.append(f"Processed {len(discussion.comments)} comments")
            if discussion.qa_pairs:
                processed.processing_notes.append(f"Processed {len(discussion.qa_pairs)} Q&A pairs")
            
            # Enhance content
            processed = self.content_enhancer.enhance_content(processed)
            
            # Update statistics
            processing_time = (datetime.now() - start_time).total_seconds()
            self._stats['total_processing_time'] += processing_time
            self._stats['successful_conversions'] += 1
            
            return processed
            
        except Exception as e:
            self.logger.error(f"Failed to process discussion content: {e}")
            self._stats['failed_conversions'] += 1
            return None
    
    def export_processed_content(
        self, 
        processed_content: ProcessedContent, 
        output_path: Path,
        format_type: str = 'markdown'
    ) -> bool:
        """Export processed content to file.
        
        Args:
            processed_content: The processed content to export
            output_path: Path to save the file
            format_type: Export format (markdown, html, json)
            
        Returns:
            True if export successful, False otherwise
        """
        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            if format_type == 'markdown':
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(processed_content.content)
            
            elif format_type == 'json':
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(processed_content.to_dict(), f, indent=2, ensure_ascii=False)
            
            elif format_type == 'html':
                # Convert markdown to HTML (basic conversion)
                html_content = self._markdown_to_html(processed_content.content)
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(html_content)
            
            else:
                raise ValueError(f"Unsupported export format: {format_type}")
            
            self.logger.info(f"Exported processed content to: {output_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to export processed content: {e}")
            return False
    
    def _markdown_to_html(self, markdown_content: str) -> str:
        """Basic markdown to HTML conversion."""
        html = markdown_content
        
        # Headers
        html = re.sub(r'^# (.+)$', r'<h1>\1</h1>', html, flags=re.MULTILINE)
        html = re.sub(r'^## (.+)$', r'<h2>\1</h2>', html, flags=re.MULTILINE)
        html = re.sub(r'^### (.+)$', r'<h3>\1</h3>', html, flags=re.MULTILINE)
        
        # Bold and italic
        html = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', html)
        html = re.sub(r'\*(.+?)\*', r'<em>\1</em>', html)
        
        # Code blocks
        html = re.sub(r'```(\w+)?\n(.*?)\n```', r'<pre><code>\2</code></pre>', html, flags=re.DOTALL)
        html = re.sub(r'`(.+?)`', r'<code>\1</code>', html)
        
        # Links and images
        html = re.sub(r'!\[([^\]]*)\]\(([^)]+)\)', r'<img src="\2" alt="\1">', html)
        html = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2">\1</a>', html)
        
        # Paragraphs
        html = re.sub(r'\n\n', '</p>\n<p>', html)
        html = f'<p>{html}</p>'
        
        # Clean up empty paragraphs
        html = re.sub(r'<p>\s*</p>', '', html)
        
        return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Processed Content</title>
    <style>
        body {{ font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }}
        pre {{ background-color: #f4f4f4; padding: 10px; border-radius: 5px; }}
        code {{ background-color: #f4f4f4; padding: 2px 4px; border-radius: 3px; }}
    </style>
</head>
<body>
{html}
</body>
</html>"""
    
    def get_processing_statistics(self) -> Dict[str, Any]:
        """Get processing statistics."""
        stats = self._stats.copy()
        
        if stats['items_processed'] > 0:
            stats['success_rate'] = stats['successful_conversions'] / stats['items_processed']
            stats['average_processing_time'] = stats['total_processing_time'] / stats['items_processed']
        else:
            stats['success_rate'] = 0.0
            stats['average_processing_time'] = 0.0
        
        return stats
    
    def reset_statistics(self):
        """Reset processing statistics."""
        self._stats = {
            'items_processed': 0,
            'successful_conversions': 0,
            'failed_conversions': 0,
            'total_processing_time': 0.0
        }