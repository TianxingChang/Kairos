"""Summary report generation and duplicate content detection service."""

import json
import hashlib
import logging
from typing import Dict, List, Any, Optional, Set, Tuple
from dataclasses import dataclass, field
from pathlib import Path
from datetime import datetime, timezone
from collections import Counter, defaultdict
from urllib.parse import urlparse
import difflib

from ..models.learning_resource import CrawledContent, LearningResource
from .content_processor import ProcessedContent
from .file_storage_service import StoredItem


@dataclass
class DuplicateMatch:
    """Represents a duplicate content match."""
    
    item1_id: str
    item2_id: str
    similarity_score: float
    match_type: str  # exact, near_exact, similar
    content_hash1: Optional[str] = None
    content_hash2: Optional[str] = None
    title_similarity: float = 0.0
    url_similarity: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'item1_id': self.item1_id,
            'item2_id': self.item2_id,
            'similarity_score': self.similarity_score,
            'match_type': self.match_type,
            'content_hash1': self.content_hash1,
            'content_hash2': self.content_hash2,
            'title_similarity': self.title_similarity,
            'url_similarity': self.url_similarity
        }


@dataclass
class TopicSummary:
    """Summary of content for a specific topic."""
    
    topic: str
    total_items: int = 0
    videos_count: int = 0
    tutorials_count: int = 0
    discussions_count: int = 0
    total_size_mb: float = 0.0
    sources: Dict[str, int] = field(default_factory=dict)
    tags: Dict[str, int] = field(default_factory=dict)
    date_range: Tuple[Optional[datetime], Optional[datetime]] = (None, None)
    duplicate_groups: List[List[str]] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'topic': self.topic,
            'total_items': self.total_items,
            'videos_count': self.videos_count,
            'tutorials_count': self.tutorials_count,
            'discussions_count': self.discussions_count,
            'total_size_mb': self.total_size_mb,
            'sources': self.sources,
            'tags': self.tags,
            'date_range': [
                self.date_range[0].isoformat() if self.date_range[0] else None,
                self.date_range[1].isoformat() if self.date_range[1] else None
            ],
            'duplicate_groups': self.duplicate_groups
        }


@dataclass
class ComprehensiveReport:
    """Comprehensive report of all processed content."""
    
    generation_date: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    total_items: int = 0
    total_size_mb: float = 0.0
    content_type_breakdown: Dict[str, int] = field(default_factory=dict)
    topic_summaries: List[TopicSummary] = field(default_factory=list)
    source_analysis: Dict[str, Any] = field(default_factory=dict)
    duplicate_analysis: Dict[str, Any] = field(default_factory=dict)
    quality_metrics: Dict[str, Any] = field(default_factory=dict)
    processing_statistics: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'generation_date': self.generation_date.isoformat(),
            'total_items': self.total_items,
            'total_size_mb': self.total_size_mb,
            'content_type_breakdown': self.content_type_breakdown,
            'topic_summaries': [ts.to_dict() for ts in self.topic_summaries],
            'source_analysis': self.source_analysis,
            'duplicate_analysis': self.duplicate_analysis,
            'quality_metrics': self.quality_metrics,
            'processing_statistics': self.processing_statistics
        }


class DuplicateDetector:
    """Detects duplicate and similar content."""
    
    def __init__(self):
        """Initialize the duplicate detector."""
        self.logger = logging.getLogger(__name__)
        
        # Similarity thresholds
        self.exact_match_threshold = 1.0
        self.near_exact_threshold = 0.95
        self.similar_threshold = 0.8
        self.title_similarity_weight = 0.3
        self.content_similarity_weight = 0.7
    
    def detect_duplicates(self, items: List[StoredItem]) -> List[DuplicateMatch]:
        """Detect duplicate content among stored items.
        
        Args:
            items: List of stored items to analyze
            
        Returns:
            List of duplicate matches found
        """
        duplicates = []
        
        # Group items by content type for more efficient comparison
        content_groups = defaultdict(list)
        for item in items:
            content_groups[item.content_type].append(item)
        
        # Check for duplicates within each content type
        for content_type, type_items in content_groups.items():
            type_duplicates = self._find_duplicates_in_group(type_items)
            duplicates.extend(type_duplicates)
        
        self.logger.info(f"Found {len(duplicates)} duplicate matches across {len(items)} items")
        
        return duplicates
    
    def _find_duplicates_in_group(self, items: List[StoredItem]) -> List[DuplicateMatch]:
        """Find duplicates within a group of items of the same type."""
        duplicates = []
        
        # Create content hashes for quick exact match detection
        hash_to_items = defaultdict(list)
        for item in items:
            content_hash = self._calculate_content_hash(item)
            hash_to_items[content_hash].append((item, content_hash))
        
        # Check for exact hash matches
        for content_hash, item_pairs in hash_to_items.items():
            if len(item_pairs) > 1:
                # Multiple items with same hash = exact duplicates
                for i in range(len(item_pairs)):
                    for j in range(i + 1, len(item_pairs)):
                        item1, hash1 = item_pairs[i]
                        item2, hash2 = item_pairs[j]
                        
                        duplicates.append(DuplicateMatch(
                            item1_id=item1.item_id,
                            item2_id=item2.item_id,
                            similarity_score=1.0,
                            match_type="exact",
                            content_hash1=hash1,
                            content_hash2=hash2,
                            title_similarity=self._calculate_title_similarity(item1.title, item2.title),
                            url_similarity=self._calculate_url_similarity(item1.original_url, item2.original_url)
                        ))
        
        # Check for near-exact and similar matches
        unique_items = [item_pairs[0][0] for item_pairs in hash_to_items.values()]
        
        for i in range(len(unique_items)):
            for j in range(i + 1, len(unique_items)):
                item1 = unique_items[i]
                item2 = unique_items[j]
                
                # Skip if already found as exact match
                if any(d.item1_id == item1.item_id and d.item2_id == item2.item_id for d in duplicates):
                    continue
                
                similarity = self._calculate_similarity(item1, item2)
                
                if similarity >= self.similar_threshold:
                    match_type = "similar"
                    if similarity >= self.near_exact_threshold:
                        match_type = "near_exact"
                    
                    duplicates.append(DuplicateMatch(
                        item1_id=item1.item_id,
                        item2_id=item2.item_id,
                        similarity_score=similarity,
                        match_type=match_type,
                        title_similarity=self._calculate_title_similarity(item1.title, item2.title),
                        url_similarity=self._calculate_url_similarity(item1.original_url, item2.original_url)
                    ))
        
        return duplicates
    
    def _calculate_content_hash(self, item: StoredItem) -> str:
        """Calculate hash of item content for exact duplicate detection."""
        # Combine key identifying features
        content_string = f"{item.title.lower().strip()}{item.original_url}{item.content_type}"
        
        # Add file size if available (helps distinguish different downloads of same content)
        if item.file_size_bytes > 0:
            content_string += str(item.file_size_bytes)
        
        return hashlib.md5(content_string.encode('utf-8')).hexdigest()
    
    def _calculate_similarity(self, item1: StoredItem, item2: StoredItem) -> float:
        """Calculate overall similarity between two items."""
        # Title similarity
        title_sim = self._calculate_title_similarity(item1.title, item2.title)
        
        # URL similarity
        url_sim = self._calculate_url_similarity(item1.original_url, item2.original_url)
        
        # Source domain similarity
        domain_sim = 1.0 if item1.source_domain == item2.source_domain else 0.0
        
        # Tag similarity
        tag_sim = self._calculate_tag_similarity(item1.tags, item2.tags)
        
        # Weighted combination
        overall_similarity = (
            title_sim * 0.4 +
            url_sim * 0.3 +
            domain_sim * 0.2 +
            tag_sim * 0.1
        )
        
        return overall_similarity
    
    def _calculate_title_similarity(self, title1: str, title2: str) -> float:
        """Calculate similarity between two titles."""
        if not title1 or not title2:
            return 0.0
        
        # Normalize titles
        norm_title1 = title1.lower().strip()
        norm_title2 = title2.lower().strip()
        
        # Exact match
        if norm_title1 == norm_title2:
            return 1.0
        
        # Use sequence matcher for similarity
        matcher = difflib.SequenceMatcher(None, norm_title1, norm_title2)
        return matcher.ratio()
    
    def _calculate_url_similarity(self, url1: str, url2: str) -> float:
        """Calculate similarity between two URLs."""
        if not url1 or not url2:
            return 0.0
        
        # Exact match
        if url1 == url2:
            return 1.0
        
        # Parse URLs
        parsed1 = urlparse(url1)
        parsed2 = urlparse(url2)
        
        # Same domain
        if parsed1.netloc == parsed2.netloc:
            # Compare paths
            if parsed1.path == parsed2.path:
                return 0.9  # Same path, might be different query params
            else:
                # Calculate path similarity
                path_sim = difflib.SequenceMatcher(None, parsed1.path, parsed2.path).ratio()
                return 0.6 + (path_sim * 0.3)  # Base similarity for same domain
        
        return 0.0
    
    def _calculate_tag_similarity(self, tags1: List[str], tags2: List[str]) -> float:
        """Calculate similarity between two tag lists."""
        if not tags1 or not tags2:
            return 0.0
        
        set1 = set(tag.lower() for tag in tags1)
        set2 = set(tag.lower() for tag in tags2)
        
        if not set1 or not set2:
            return 0.0
        
        intersection = len(set1.intersection(set2))
        union = len(set1.union(set2))
        
        return intersection / union if union > 0 else 0.0
    
    def group_duplicates(self, duplicates: List[DuplicateMatch]) -> List[List[str]]:
        """Group duplicate matches into clusters of related items."""
        # Build graph of duplicate relationships
        connections = defaultdict(set)
        
        for duplicate in duplicates:
            connections[duplicate.item1_id].add(duplicate.item2_id)
            connections[duplicate.item2_id].add(duplicate.item1_id)
        
        # Find connected components (duplicate groups)
        visited = set()
        groups = []
        
        for item_id in connections:
            if item_id not in visited:
                group = []
                self._dfs_group(item_id, connections, visited, group)
                if len(group) > 1:  # Only include groups with multiple items
                    groups.append(sorted(group))
        
        return groups
    
    def _dfs_group(self, item_id: str, connections: Dict[str, Set[str]], visited: Set[str], group: List[str]):
        """Depth-first search to find connected duplicate items."""
        visited.add(item_id)
        group.append(item_id)
        
        for connected_id in connections[item_id]:
            if connected_id not in visited:
                self._dfs_group(connected_id, connections, visited, group)


class SummaryGenerator:
    """Generates comprehensive summaries and reports."""
    
    def __init__(self):
        """Initialize the summary generator."""
        self.logger = logging.getLogger(__name__)
        self.duplicate_detector = DuplicateDetector()
    
    def generate_topic_summary(self, topic: str, items: List[StoredItem]) -> TopicSummary:
        """Generate summary for a specific topic.
        
        Args:
            topic: Topic name
            items: List of stored items for this topic
            
        Returns:
            Topic summary
        """
        summary = TopicSummary(topic=topic)
        
        if not items:
            return summary
        
        # Basic counts
        summary.total_items = len(items)
        summary.videos_count = sum(1 for item in items if item.content_type == 'video')
        summary.tutorials_count = sum(1 for item in items if item.content_type == 'tutorial')
        summary.discussions_count = sum(1 for item in items if item.content_type == 'discussion')
        
        # Size calculation
        summary.total_size_mb = sum(item.file_size_bytes for item in items) / (1024 * 1024)
        
        # Source analysis
        source_counter = Counter(item.source_domain for item in items)
        summary.sources = dict(source_counter.most_common())
        
        # Tag analysis
        all_tags = []
        for item in items:
            all_tags.extend(item.tags)
        tag_counter = Counter(all_tags)
        summary.tags = dict(tag_counter.most_common(10))  # Top 10 tags
        
        # Date range
        dates = [item.storage_date for item in items if item.storage_date]
        if dates:
            summary.date_range = (min(dates), max(dates))
        
        # Duplicate detection
        duplicates = self.duplicate_detector.detect_duplicates(items)
        summary.duplicate_groups = self.duplicate_detector.group_duplicates(duplicates)
        
        return summary
    
    def generate_comprehensive_report(
        self, 
        stored_items: List[StoredItem],
        processing_stats: Optional[Dict[str, Any]] = None
    ) -> ComprehensiveReport:
        """Generate comprehensive report of all content.
        
        Args:
            stored_items: All stored items
            processing_stats: Optional processing statistics
            
        Returns:
            Comprehensive report
        """
        report = ComprehensiveReport()
        
        if not stored_items:
            return report
        
        # Basic statistics
        report.total_items = len(stored_items)
        report.total_size_mb = sum(item.file_size_bytes for item in stored_items) / (1024 * 1024)
        
        # Content type breakdown
        content_types = Counter(item.content_type for item in stored_items)
        report.content_type_breakdown = dict(content_types)
        
        # Topic summaries
        topics = defaultdict(list)
        for item in stored_items:
            topics[item.topic].append(item)
        
        for topic, topic_items in topics.items():
            topic_summary = self.generate_topic_summary(topic, topic_items)
            report.topic_summaries.append(topic_summary)
        
        # Source analysis
        report.source_analysis = self._analyze_sources(stored_items)
        
        # Duplicate analysis
        all_duplicates = self.duplicate_detector.detect_duplicates(stored_items)
        duplicate_groups = self.duplicate_detector.group_duplicates(all_duplicates)
        
        report.duplicate_analysis = {
            'total_duplicates_found': len(all_duplicates),
            'duplicate_groups_count': len(duplicate_groups),
            'items_with_duplicates': len(set(
                item_id for group in duplicate_groups for item_id in group
            )),
            'potential_space_savings_mb': self._calculate_space_savings(duplicate_groups, stored_items)
        }
        
        # Quality metrics
        report.quality_metrics = self._calculate_quality_metrics(stored_items)
        
        # Processing statistics
        if processing_stats:
            report.processing_statistics = processing_stats
        
        return report
    
    def _analyze_sources(self, items: List[StoredItem]) -> Dict[str, Any]:
        """Analyze source domains and their characteristics."""
        source_stats = defaultdict(lambda: {
            'count': 0,
            'total_size_mb': 0.0,
            'content_types': defaultdict(int),
            'quality_score': 0.0
        })
        
        # Collect source statistics
        for item in items:
            stats = source_stats[item.source_domain]
            stats['count'] += 1
            stats['total_size_mb'] += item.file_size_bytes / (1024 * 1024)
            stats['content_types'][item.content_type] += 1
        
        # Calculate quality scores (based on content diversity and quantity)
        for domain, stats in source_stats.items():
            diversity_score = len(stats['content_types']) / 3.0  # Max 3 content types
            quantity_score = min(stats['count'] / 10.0, 1.0)  # Normalize to max 10 items
            stats['quality_score'] = (diversity_score + quantity_score) / 2.0
        
        # Convert to regular dict and sort by count
        return {
            'total_sources': len(source_stats),
            'top_sources': dict(sorted(
                source_stats.items(),
                key=lambda x: x[1]['count'],
                reverse=True
            )[:10]),  # Top 10 sources
            'source_diversity': len(source_stats) / max(len(items), 1)
        }
    
    def _calculate_space_savings(self, duplicate_groups: List[List[str]], items: List[StoredItem]) -> float:
        """Calculate potential space savings from removing duplicates."""
        item_lookup = {item.item_id: item for item in items}
        total_savings = 0.0
        
        for group in duplicate_groups:
            # Find largest file in group (keep this one)
            group_items = [item_lookup[item_id] for item_id in group if item_id in item_lookup]
            if len(group_items) <= 1:
                continue
            
            group_items.sort(key=lambda x: x.file_size_bytes, reverse=True)
            
            # Sum size of all but the largest
            for item in group_items[1:]:
                total_savings += item.file_size_bytes
        
        return total_savings / (1024 * 1024)  # Convert to MB
    
    def _calculate_quality_metrics(self, items: List[StoredItem]) -> Dict[str, Any]:
        """Calculate quality metrics for the content collection."""
        if not items:
            return {}
        
        # Content diversity
        topics = set(item.topic for item in items)
        sources = set(item.source_domain for item in items)
        content_types = set(item.content_type for item in items)
        
        # Tag analysis
        all_tags = []
        for item in items:
            all_tags.extend(item.tags)
        unique_tags = set(all_tags)
        
        # Size distribution
        sizes_mb = [item.file_size_bytes / (1024 * 1024) for item in items if item.file_size_bytes > 0]
        avg_size = sum(sizes_mb) / len(sizes_mb) if sizes_mb else 0
        
        # Recency score (how recent is the content)
        now = datetime.now(timezone.utc)
        ages_days = [(now - item.storage_date).days for item in items if item.storage_date]
        avg_age_days = sum(ages_days) / len(ages_days) if ages_days else 0
        recency_score = max(0, 1 - (avg_age_days / 365))  # Normalize to 1 year
        
        return {
            'content_diversity_score': len(topics) / max(len(items), 1),
            'source_diversity_score': len(sources) / max(len(items), 1),
            'content_type_coverage': len(content_types) / 3.0,  # Max 3 types
            'tag_richness': len(unique_tags) / max(len(items), 1),
            'average_content_size_mb': round(avg_size, 2),
            'recency_score': round(recency_score, 2),
            'collection_completeness': min(len(items) / 100, 1.0)  # Arbitrary target of 100 items
        }
    
    def export_report(self, report: ComprehensiveReport, output_path: Path, format_type: str = 'json') -> bool:
        """Export report to file.
        
        Args:
            report: Report to export
            output_path: Path to save the report
            format_type: Export format (json, markdown, html)
            
        Returns:
            True if export successful, False otherwise
        """
        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            if format_type == 'json':
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(report.to_dict(), f, indent=2, ensure_ascii=False)
            
            elif format_type == 'markdown':
                markdown_content = self._generate_markdown_report(report)
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(markdown_content)
            
            elif format_type == 'html':
                html_content = self._generate_html_report(report)
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(html_content)
            
            else:
                raise ValueError(f"Unsupported export format: {format_type}")
            
            self.logger.info(f"Report exported to: {output_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to export report: {e}")
            return False
    
    def _generate_markdown_report(self, report: ComprehensiveReport) -> str:
        """Generate markdown format report."""
        lines = []
        
        # Header
        lines.extend([
            "# Learning Content Collection Report",
            "",
            f"**Generated:** {report.generation_date.strftime('%Y-%m-%d %H:%M:%S UTC')}",
            "",
            "## Overview",
            "",
            f"- **Total Items:** {report.total_items:,}",
            f"- **Total Size:** {report.total_size_mb:.1f} MB",
            ""
        ])
        
        # Content type breakdown
        if report.content_type_breakdown:
            lines.extend([
                "## Content Type Breakdown",
                ""
            ])
            
            for content_type, count in report.content_type_breakdown.items():
                percentage = (count / report.total_items) * 100 if report.total_items > 0 else 0
                lines.append(f"- **{content_type.title()}:** {count:,} items ({percentage:.1f}%)")
            
            lines.append("")
        
        # Topic summaries
        if report.topic_summaries:
            lines.extend([
                "## Topic Analysis",
                ""
            ])
            
            # Sort topics by item count
            sorted_topics = sorted(report.topic_summaries, key=lambda x: x.total_items, reverse=True)
            
            for topic_summary in sorted_topics[:10]:  # Top 10 topics
                lines.extend([
                    f"### {topic_summary.topic.title()}",
                    "",
                    f"- **Items:** {topic_summary.total_items}",
                    f"- **Size:** {topic_summary.total_size_mb:.1f} MB",
                    f"- **Videos:** {topic_summary.videos_count}",
                    f"- **Tutorials:** {topic_summary.tutorials_count}",
                    f"- **Discussions:** {topic_summary.discussions_count}",
                    ""
                ])
                
                if topic_summary.sources:
                    lines.append("**Top Sources:**")
                    for source, count in list(topic_summary.sources.items())[:3]:
                        lines.append(f"- {source}: {count} items")
                    lines.append("")
        
        # Source analysis
        if report.source_analysis.get('top_sources'):
            lines.extend([
                "## Source Analysis",
                "",
                f"**Total Sources:** {report.source_analysis['total_sources']}",
                "",
                "### Top Sources",
                ""
            ])
            
            for source, stats in list(report.source_analysis['top_sources'].items())[:10]:
                lines.extend([
                    f"#### {source}",
                    "",
                    f"- **Items:** {stats['count']}",
                    f"- **Size:** {stats['total_size_mb']:.1f} MB",
                    f"- **Quality Score:** {stats['quality_score']:.2f}",
                    ""
                ])
        
        # Duplicate analysis
        if report.duplicate_analysis:
            lines.extend([
                "## Duplicate Analysis",
                "",
                f"- **Duplicates Found:** {report.duplicate_analysis['total_duplicates_found']}",
                f"- **Duplicate Groups:** {report.duplicate_analysis['duplicate_groups_count']}",
                f"- **Items with Duplicates:** {report.duplicate_analysis['items_with_duplicates']}",
                f"- **Potential Space Savings:** {report.duplicate_analysis['potential_space_savings_mb']:.1f} MB",
                ""
            ])
        
        # Quality metrics
        if report.quality_metrics:
            lines.extend([
                "## Quality Metrics",
                ""
            ])
            
            for metric, value in report.quality_metrics.items():
                metric_name = metric.replace('_', ' ').title()
                if isinstance(value, float):
                    lines.append(f"- **{metric_name}:** {value:.2f}")
                else:
                    lines.append(f"- **{metric_name}:** {value}")
            
            lines.append("")
        
        return '\n'.join(lines)
    
    def _generate_html_report(self, report: ComprehensiveReport) -> str:
        """Generate HTML format report."""
        # Convert markdown to HTML
        markdown_content = self._generate_markdown_report(report)
        
        # Basic markdown to HTML conversion
        html_content = markdown_content
        
        # Headers
        html_content = re.sub(r'^# (.+)$', r'<h1>\1</h1>', html_content, flags=re.MULTILINE)
        html_content = re.sub(r'^## (.+)$', r'<h2>\1</h2>', html_content, flags=re.MULTILINE)
        html_content = re.sub(r'^### (.+)$', r'<h3>\1</h3>', html_content, flags=re.MULTILINE)
        html_content = re.sub(r'^#### (.+)$', r'<h4>\1</h4>', html_content, flags=re.MULTILINE)
        
        # Bold text
        html_content = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', html_content)
        
        # Lists
        html_content = re.sub(r'^- (.+)$', r'<li>\1</li>', html_content, flags=re.MULTILINE)
        
        # Wrap in HTML structure
        return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Learning Content Collection Report</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            line-height: 1.6;
        }}
        h1, h2, h3, h4 {{
            color: #333;
            margin-top: 30px;
        }}
        h1 {{
            border-bottom: 2px solid #eee;
            padding-bottom: 10px;
        }}
        h2 {{
            border-bottom: 1px solid #eee;
            padding-bottom: 5px;
        }}
        li {{
            margin: 5px 0;
        }}
        strong {{
            color: #2c5aa0;
        }}
        .overview {{
            background-color: #f8f9fa;
            padding: 20px;
            border-radius: 8px;
            margin: 20px 0;
        }}
    </style>
</head>
<body>
    <div class="overview">
        {html_content}
    </div>
</body>
</html>"""


class SummaryReportService:
    """Main service for generating summaries and reports."""
    
    def __init__(self):
        """Initialize the summary report service."""
        self.logger = logging.getLogger(__name__)
        self.summary_generator = SummaryGenerator()
        self.duplicate_detector = DuplicateDetector()
    
    def generate_session_summary(
        self,
        session_data: Dict[str, Any],
        stored_items: List[StoredItem]
    ) -> Dict[str, Any]:
        """Generate summary of a scraping session.
        
        Args:
            session_data: Data about the scraping session
            stored_items: Items that were stored during the session
            
        Returns:
            Session summary dictionary
        """
        summary = {
            'session_id': session_data.get('session_id', 'unknown'),
            'start_time': session_data.get('start_time'),
            'end_time': session_data.get('end_time'),
            'duration_seconds': session_data.get('duration_seconds', 0),
            'items_processed': len(stored_items),
            'total_size_mb': sum(item.file_size_bytes for item in stored_items) / (1024 * 1024),
            'content_breakdown': {},
            'topics_covered': [],
            'sources_used': [],
            'success_metrics': {},
            'issues_encountered': session_data.get('errors', [])
        }
        
        if stored_items:
            # Content breakdown
            content_types = Counter(item.content_type for item in stored_items)
            summary['content_breakdown'] = dict(content_types)
            
            # Topics and sources
            summary['topics_covered'] = list(set(item.topic for item in stored_items))
            summary['sources_used'] = list(set(item.source_domain for item in stored_items))
            
            # Success metrics
            summary['success_metrics'] = {
                'average_item_size_mb': summary['total_size_mb'] / len(stored_items),
                'items_per_minute': len(stored_items) / max(summary['duration_seconds'] / 60, 1),
                'unique_sources': len(summary['sources_used']),
                'unique_topics': len(summary['topics_covered'])
            }
        
        return summary
    
    def detect_and_report_duplicates(self, items: List[StoredItem]) -> Dict[str, Any]:
        """Detect duplicates and generate detailed report.
        
        Args:
            items: List of stored items to analyze
            
        Returns:
            Duplicate detection report
        """
        duplicates = self.duplicate_detector.detect_duplicates(items)
        duplicate_groups = self.duplicate_detector.group_duplicates(duplicates)
        
        # Analyze duplicate types
        duplicate_types = Counter(d.match_type for d in duplicates)
        
        # Calculate statistics
        items_with_duplicates = set()
        for duplicate in duplicates:
            items_with_duplicates.add(duplicate.item1_id)
            items_with_duplicates.add(duplicate.item2_id)
        
        # Group analysis
        group_sizes = [len(group) for group in duplicate_groups]
        largest_group_size = max(group_sizes) if group_sizes else 0
        
        return {
            'total_items_analyzed': len(items),
            'duplicate_matches_found': len(duplicates),
            'items_with_duplicates': len(items_with_duplicates),
            'duplicate_groups': len(duplicate_groups),
            'largest_group_size': largest_group_size,
            'duplicate_types': dict(duplicate_types),
            'duplicate_rate': len(items_with_duplicates) / len(items) if items else 0,
            'groups_detail': [
                {
                    'group_id': i,
                    'item_count': len(group),
                    'item_ids': group
                }
                for i, group in enumerate(duplicate_groups)
            ],
            'recommendations': self._generate_duplicate_recommendations(duplicates, duplicate_groups)
        }
    
    def _generate_duplicate_recommendations(
        self,
        duplicates: List[DuplicateMatch],
        duplicate_groups: List[List[str]]
    ) -> List[str]:
        """Generate recommendations for handling duplicates."""
        recommendations = []
        
        exact_matches = [d for d in duplicates if d.match_type == "exact"]
        if exact_matches:
            recommendations.append(
                f"Found {len(exact_matches)} exact duplicates that can be safely removed"
            )
        
        near_exact_matches = [d for d in duplicates if d.match_type == "near_exact"]
        if near_exact_matches:
            recommendations.append(
                f"Found {len(near_exact_matches)} near-exact matches that likely should be reviewed for removal"
            )
        
        large_groups = [group for group in duplicate_groups if len(group) > 3]
        if large_groups:
            recommendations.append(
                f"Found {len(large_groups)} groups with more than 3 duplicates - prioritize these for cleanup"
            )
        
        if not duplicates:
            recommendations.append("No duplicates detected - collection appears to be well-curated")
        
        return recommendations
    
    def export_comprehensive_report(
        self,
        stored_items: List[StoredItem],
        output_dir: Path,
        include_duplicates: bool = True,
        processing_stats: Optional[Dict[str, Any]] = None
    ) -> Dict[str, str]:
        """Export comprehensive report in multiple formats.
        
        Args:
            stored_items: All stored items to analyze
            output_dir: Directory to save reports
            include_duplicates: Whether to include duplicate analysis
            processing_stats: Optional processing statistics
            
        Returns:
            Dictionary mapping format to output file path
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate comprehensive report
        report = self.summary_generator.generate_comprehensive_report(
            stored_items, processing_stats
        )
        
        # Export in multiple formats
        exported_files = {}
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        formats = [
            ('json', f'comprehensive_report_{timestamp}.json'),
            ('markdown', f'comprehensive_report_{timestamp}.md'),
            ('html', f'comprehensive_report_{timestamp}.html')
        ]
        
        for format_type, filename in formats:
            output_path = output_dir / filename
            
            try:
                success = self.summary_generator.export_report(report, output_path, format_type)
                if success:
                    exported_files[format_type] = str(output_path)
            except Exception as e:
                self.logger.error(f"Failed to export {format_type} report: {e}")
        
        # Export duplicate analysis separately if requested
        if include_duplicates and stored_items:
            duplicate_report = self.detect_and_report_duplicates(stored_items)
            duplicate_path = output_dir / f'duplicate_analysis_{timestamp}.json'
            
            try:
                with open(duplicate_path, 'w', encoding='utf-8') as f:
                    json.dump(duplicate_report, f, indent=2, ensure_ascii=False)
                exported_files['duplicates'] = str(duplicate_path)
            except Exception as e:
                self.logger.error(f"Failed to export duplicate analysis: {e}")
        
        self.logger.info(f"Exported {len(exported_files)} report files to {output_dir}")
        
        return exported_files