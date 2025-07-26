"""Search service for discovering learning resources."""

import asyncio
import logging
import re
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from urllib.parse import urlparse

from ..clients.firecrawl_mcp_client import FirecrawlMCPClient, MCPError
from ..models.learning_resource import LearningResource
from ..config.firecrawl_config import FirecrawlConfig


@dataclass
class SearchOptions:
    """Options for configuring search behavior."""
    
    max_results: int = 10
    educational_domains_only: bool = True
    include_video_content: bool = True
    include_tutorial_content: bool = True
    include_documentation: bool = True
    language: str = 'en'
    freshness_days: Optional[int] = None  # Prefer content from last N days
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API calls."""
        options = {
            'limit': self.max_results,
            'language': self.language,
            'includeMetadata': True,
            'searchType': 'web'
        }
        
        # Configure content type filters
        content_types = []
        if self.include_tutorial_content:
            content_types.extend(['tutorial', 'guide', 'how-to'])
        if self.include_video_content:
            content_types.extend(['video', 'course'])
        if self.include_documentation:
            content_types.extend(['documentation', 'reference'])
        
        if content_types:
            options['filters'] = options.get('filters', {})
            options['filters']['contentType'] = content_types
        
        # Configure domain preferences
        if self.educational_domains_only:
            options['filters'] = options.get('filters', {})
            options['filters']['domains'] = ['edu', 'org', 'gov']
        
        # Configure freshness filter
        if self.freshness_days:
            options['filters'] = options.get('filters', {})
            options['filters']['publishedAfter'] = f'{self.freshness_days}d'
        
        return options


class SearchQueryOptimizer:
    """Optimizes search queries for educational content discovery."""
    
    def __init__(self):
        """Initialize the query optimizer."""
        self.logger = logging.getLogger(__name__)
        
        # Educational keywords to boost relevance
        self.educational_keywords = [
            'tutorial', 'guide', 'learn', 'course', 'lesson',
            'introduction', 'beginner', 'basics', 'fundamentals',
            'documentation', 'reference', 'manual', 'handbook'
        ]
        
        # Platform-specific search terms
        self.platform_terms = {
            'video': ['youtube', 'coursera', 'udemy', 'khan academy', 'edx'],
            'documentation': ['docs', 'api', 'reference', 'manual'],
            'tutorial': ['tutorial', 'guide', 'walkthrough', 'step-by-step'],
            'forum': ['stackoverflow', 'reddit', 'forum', 'community']
        }
    
    def optimize_query(self, topic: str, search_options: SearchOptions) -> List[str]:
        """Generate optimized search queries for the given topic.
        
        Args:
            topic: The learning topic to search for
            search_options: Search configuration options
            
        Returns:
            List of optimized search queries
        """
        queries = []
        base_topic = topic.strip()
        
        # Primary query with educational context
        primary_query = f"{base_topic} tutorial learn guide"
        queries.append(primary_query)
        
        # Query variations based on content types (prioritize documentation if enabled)
        if search_options.include_documentation:
            queries.append(f"{base_topic} documentation reference guide")
            queries.append(f"{base_topic} official documentation")
        
        if search_options.include_tutorial_content:
            queries.append(f"{base_topic} tutorial step by step guide")
            queries.append(f"learn {base_topic} beginner tutorial")
        
        if search_options.include_video_content:
            queries.append(f"{base_topic} video course tutorial")
            queries.append(f"{base_topic} youtube tutorial course")
        
        # Technology-specific optimizations
        if self._is_programming_topic(base_topic):
            queries.append(f"{base_topic} programming tutorial examples")
            queries.append(f"how to use {base_topic} programming")
        
        # Remove duplicates while preserving order
        seen = set()
        unique_queries = []
        for query in queries:
            if query not in seen:
                seen.add(query)
                unique_queries.append(query)
        
        self.logger.info(f"Generated {len(unique_queries)} optimized queries for topic: {base_topic}")
        return unique_queries[:5]  # Limit to top 5 queries
    
    def _is_programming_topic(self, topic: str) -> bool:
        """Check if the topic is related to programming/technology."""
        programming_keywords = [
            'python', 'javascript', 'java', 'react', 'angular', 'vue',
            'node', 'docker', 'kubernetes', 'git', 'sql', 'html', 'css',
            'programming', 'coding', 'development', 'api', 'framework',
            'library', 'database', 'algorithm', 'data structure'
        ]
        
        topic_lower = topic.lower()
        return any(keyword in topic_lower for keyword in programming_keywords)


class LearningResourceRanker:
    """Ranks and filters search results based on educational value."""
    
    def __init__(self):
        """Initialize the resource ranker."""
        self.logger = logging.getLogger(__name__)
        
        # Domain authority scores for educational content
        self.domain_scores = {
            # High authority educational sites
            'edu': 1.0, 'mit.edu': 1.0, 'stanford.edu': 1.0, 'harvard.edu': 1.0,
            'coursera.org': 0.95, 'edx.org': 0.95, 'khanacademy.org': 0.95,
            'udemy.com': 0.9, 'pluralsight.com': 0.9, 'lynda.com': 0.9,
            
            # Technical documentation sites
            'docs.python.org': 1.0, 'developer.mozilla.org': 0.95,
            'reactjs.org': 0.9, 'angular.io': 0.9, 'vuejs.org': 0.9,
            
            # Community and reference sites
            'stackoverflow.com': 0.85, 'github.com': 0.8, 'medium.com': 0.7,
            'dev.to': 0.75, 'freecodecamp.org': 0.9, 'w3schools.com': 0.8,
            'realpython.com': 0.85, 'tutorialspoint.com': 0.7, 'geeksforgeeks.org': 0.75,
            
            # Video platforms
            'youtube.com': 0.7,  # Variable quality, needs content analysis
            'vimeo.com': 0.6,
            
            # Default scores
            'org': 0.7, 'com': 0.5, 'net': 0.4, 'io': 0.6
        }
        
        # Content quality indicators
        self.quality_indicators = {
            'positive': [
                'tutorial', 'guide', 'introduction', 'beginner', 'complete',
                'comprehensive', 'step-by-step', 'hands-on', 'practical',
                'official', 'documentation', 'reference', 'learn', 'course'
            ],
            'negative': [
                'blog', 'opinion', 'review', 'news', 'advertisement',
                'sponsored', 'affiliate', 'click-bait'
            ]
        }
    
    def rank_resources(self, search_results: List[Dict[str, Any]], topic: str, limit: int = 3) -> List[LearningResource]:
        """Rank search results and return top learning resources.
        
        Args:
            search_results: Raw search results from web search
            topic: Original search topic for relevance scoring
            limit: Maximum number of resources to return
            
        Returns:
            List of ranked learning resources
        """
        if not search_results:
            return []
        
        self.logger.info(f"Ranking {len(search_results)} search results for topic: {topic}")
        
        # Score and convert each result
        scored_resources = []
        for result in search_results:
            resource = self._convert_to_learning_resource(result, topic)
            if resource:
                scored_resources.append(resource)
        
        # Sort by combined score (relevance + quality)
        scored_resources.sort(key=lambda x: x.relevance_score + x.estimated_quality, reverse=True)
        
        # Apply diversity filter to avoid too many results from same domain
        diverse_resources = self._apply_diversity_filter(scored_resources, limit * 2)
        
        # Return top results
        top_resources = diverse_resources[:limit]
        
        self.logger.info(f"Selected top {len(top_resources)} learning resources")
        return top_resources
    
    def _convert_to_learning_resource(self, result: Dict[str, Any], topic: str) -> Optional[LearningResource]:
        """Convert search result to LearningResource with scoring.
        
        Args:
            result: Raw search result dictionary
            topic: Original search topic
            
        Returns:
            LearningResource instance or None if invalid
        """
        try:
            url = result.get('url', '')
            title = result.get('title', '')
            description = result.get('description', '') or result.get('snippet', '')
            
            if not url or not title:
                return None
            
            # Calculate relevance score
            relevance_score = self._calculate_relevance_score(title, description, topic)
            
            # Calculate quality score
            quality_score = self._calculate_quality_score(url, title, description)
            
            # Determine content type
            content_type = self._determine_content_type(url, title, description)
            
            return LearningResource(
                url=url,
                title=title,
                description=description,
                relevance_score=relevance_score,
                content_type=content_type,
                estimated_quality=quality_score
            )
            
        except Exception as e:
            self.logger.warning(f"Failed to convert search result to learning resource: {e}")
            return None
    
    def _calculate_relevance_score(self, title: str, description: str, topic: str) -> float:
        """Calculate relevance score based on topic matching.
        
        Args:
            title: Resource title
            description: Resource description
            topic: Search topic
            
        Returns:
            Relevance score between 0.0 and 1.0
        """
        topic_words = set(topic.lower().split())
        combined_text = f"{title} {description}".lower()
        
        # Direct topic word matches
        word_matches = sum(1 for word in topic_words if word in combined_text)
        word_score = min(word_matches / len(topic_words), 1.0) if topic_words else 0.0
        
        # Boost for exact topic phrase match
        phrase_boost = 0.3 if topic.lower() in combined_text else 0.0
        
        # Boost for title matches (more important than description)
        title_boost = 0.2 if any(word in title.lower() for word in topic_words) else 0.0
        
        # Educational context boost
        edu_keywords = ['learn', 'tutorial', 'guide', 'course', 'introduction']
        edu_boost = 0.1 if any(keyword in combined_text for keyword in edu_keywords) else 0.0
        
        return min(word_score + phrase_boost + title_boost + edu_boost, 1.0)
    
    def _calculate_quality_score(self, url: str, title: str, description: str) -> float:
        """Calculate quality score based on various indicators.
        
        Args:
            url: Resource URL
            title: Resource title
            description: Resource description
            
        Returns:
            Quality score between 0.0 and 1.0
        """
        # Domain authority score
        domain_score = self._get_domain_score(url)
        
        # Content quality indicators
        combined_text = f"{title} {description}".lower()
        
        positive_score = sum(0.1 for indicator in self.quality_indicators['positive'] 
                           if indicator in combined_text)
        negative_score = sum(0.15 for indicator in self.quality_indicators['negative'] 
                           if indicator in combined_text)
        
        content_score = max(0.0, positive_score - negative_score)
        
        # Length penalty for very short descriptions
        length_score = min(len(description) / 100, 1.0) if description else 0.5
        
        # URL structure quality (prefer clean, structured URLs)
        url_score = self._score_url_structure(url)
        
        # Combine scores with weights (boost domain score for official documentation)
        quality_score = (
            domain_score * 0.5 +
            content_score * 0.25 +
            length_score * 0.15 +
            url_score * 0.1
        )
        
        return min(quality_score, 1.0)
    
    def _get_domain_score(self, url: str) -> float:
        """Get domain authority score for URL.
        
        Args:
            url: Resource URL
            
        Returns:
            Domain score between 0.0 and 1.0
        """
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            
            # Check for exact domain matches
            if domain in self.domain_scores:
                return self.domain_scores[domain]
            
            # Check for TLD-based scoring
            for tld, score in self.domain_scores.items():
                if domain.endswith(f'.{tld}'):
                    return score
            
            # Default score for unknown domains
            return 0.5
            
        except Exception:
            return 0.3
    
    def _score_url_structure(self, url: str) -> float:
        """Score URL structure for educational content indicators.
        
        Args:
            url: Resource URL
            
        Returns:
            URL structure score between 0.0 and 1.0
        """
        try:
            parsed = urlparse(url)
            path = parsed.path.lower()
            
            # Positive path indicators
            positive_paths = [
                'tutorial', 'guide', 'learn', 'course', 'lesson',
                'documentation', 'docs', 'reference', 'manual'
            ]
            
            # Negative path indicators
            negative_paths = [
                'blog', 'news', 'ad', 'advertisement', 'popup',
                'affiliate', 'sponsored'
            ]
            
            positive_score = 0.2 * sum(1 for indicator in positive_paths if indicator in path)
            negative_score = 0.3 * sum(1 for indicator in negative_paths if indicator in path)
            
            # Clean URL structure bonus
            structure_bonus = 0.1 if path.count('/') <= 4 else 0.0
            
            return max(0.0, min(0.5 + positive_score - negative_score + structure_bonus, 1.0))
            
        except Exception:
            return 0.5
    
    def _determine_content_type(self, url: str, title: str, description: str) -> str:
        """Determine the type of learning content.
        
        Args:
            url: Resource URL
            title: Resource title
            description: Resource description
            
        Returns:
            Content type string
        """
        combined_text = f"{url} {title} {description}".lower()
        
        # Video content indicators
        video_indicators = ['youtube', 'vimeo', 'video', 'watch', 'course', 'lecture']
        if any(indicator in combined_text for indicator in video_indicators):
            return 'video'
        
        # Documentation indicators
        doc_indicators = ['docs', 'documentation', 'reference', 'api', 'manual']
        if any(indicator in combined_text for indicator in doc_indicators):
            return 'documentation'
        
        # Tutorial indicators
        tutorial_indicators = ['tutorial', 'guide', 'walkthrough', 'how-to', 'step-by-step']
        if any(indicator in combined_text for indicator in tutorial_indicators):
            return 'tutorial'
        
        # Forum/discussion indicators
        forum_indicators = ['forum', 'discussion', 'stackoverflow', 'reddit', 'community']
        if any(indicator in combined_text for indicator in forum_indicators):
            return 'discussion'
        
        return 'article'  # Default type
    
    def _apply_diversity_filter(self, resources: List[LearningResource], max_per_domain: int = 2) -> List[LearningResource]:
        """Apply diversity filter to avoid too many results from same domain.
        
        Args:
            resources: List of learning resources
            max_per_domain: Maximum resources per domain
            
        Returns:
            Filtered list with domain diversity
        """
        domain_counts = {}
        filtered_resources = []
        
        for resource in resources:
            try:
                domain = urlparse(resource.url).netloc.lower()
                current_count = domain_counts.get(domain, 0)
                
                if current_count < max_per_domain:
                    filtered_resources.append(resource)
                    domain_counts[domain] = current_count + 1
                    
            except Exception:
                # Include resources with unparseable URLs
                filtered_resources.append(resource)
        
        return filtered_resources


class SearchService:
    """Main service for discovering learning resources through web search."""
    
    def __init__(self, firecrawl_client: FirecrawlMCPClient):
        """Initialize the search service.
        
        Args:
            firecrawl_client: Configured Firecrawl MCP client
        """
        self.firecrawl_client = firecrawl_client
        self.logger = logging.getLogger(__name__)
        self.query_optimizer = SearchQueryOptimizer()
        self.resource_ranker = LearningResourceRanker()
    
    async def search_learning_resources(
        self, 
        topic: str, 
        options: Optional[SearchOptions] = None
    ) -> Tuple[List[LearningResource], Dict[str, Any]]:
        """Search for learning resources on a given topic.
        
        Args:
            topic: The learning topic to search for
            options: Search configuration options
            
        Returns:
            Tuple of (learning resources list, search metadata)
            
        Raises:
            MCPError: If search operation fails
        """
        if not topic or not topic.strip():
            raise MCPError("Search topic cannot be empty")
        
        options = options or SearchOptions()
        self.logger.info(f"Searching for learning resources on topic: {topic}")
        
        try:
            # Generate optimized search queries
            search_queries = self.query_optimizer.optimize_query(topic, options)
            
            # Execute searches for each query
            all_results = []
            failed_queries = 0
            search_metadata = {
                'topic': topic,
                'queries_executed': len(search_queries),
                'total_raw_results': 0,
                'search_options': options.to_dict(),
                'execution_time': 0.0
            }
            
            start_time = asyncio.get_event_loop().time()
            
            for query in search_queries:
                try:
                    self.logger.debug(f"Executing search query: {query}")
                    
                    # Search with MCP client
                    results = await self.firecrawl_client.search_web(
                        query=query,
                        options=options.to_dict()
                    )
                    
                    all_results.extend(results)
                    search_metadata['total_raw_results'] += len(results)
                    
                    # Brief delay between queries to be respectful
                    await asyncio.sleep(0.5)
                    
                except MCPError as e:
                    self.logger.warning(f"Search query failed: {query} - {e}")
                    failed_queries += 1
                    continue
            
            end_time = asyncio.get_event_loop().time()
            search_metadata['execution_time'] = end_time - start_time
            
            # If all queries failed with MCP errors, raise an error
            if failed_queries == len(search_queries) and failed_queries > 0:
                raise MCPError(f"All search queries failed for topic: {topic}")
            
            if not all_results:
                self.logger.warning(f"No search results found for topic: {topic}")
                search_metadata.update({
                    'final_resource_count': 0,
                    'deduplication_ratio': 0
                })
                return [], search_metadata
            
            # Rank and filter results
            learning_resources = self.resource_ranker.rank_resources(
                search_results=all_results,
                topic=topic,
                limit=3  # Return exactly 3 most useful resources
            )
            
            search_metadata.update({
                'final_resource_count': len(learning_resources),
                'deduplication_ratio': len(learning_resources) / len(all_results) if all_results else 0
            })
            
            self.logger.info(
                f"Search completed for topic '{topic}': "
                f"{len(learning_resources)} resources from {len(all_results)} raw results"
            )
            
            return learning_resources, search_metadata
            
        except Exception as e:
            self.logger.error(f"Search failed for topic '{topic}': {e}")
            raise MCPError(f"Search operation failed: {e}")
    
    async def search_specific_content_type(
        self, 
        topic: str, 
        content_type: str,
        options: Optional[SearchOptions] = None
    ) -> List[LearningResource]:
        """Search for specific type of learning content.
        
        Args:
            topic: The learning topic to search for
            content_type: Specific content type ('video', 'tutorial', 'documentation')
            options: Search configuration options
            
        Returns:
            List of learning resources of specified type
            
        Raises:
            MCPError: If search operation fails
        """
        if not topic or not topic.strip():
            raise MCPError("Search topic cannot be empty")
        
        # Configure options for specific content type
        options = options or SearchOptions()
        
        if content_type == 'video':
            options.include_video_content = True
            options.include_tutorial_content = False
            options.include_documentation = False
        elif content_type == 'tutorial':
            options.include_video_content = False
            options.include_tutorial_content = True
            options.include_documentation = False
        elif content_type == 'documentation':
            options.include_video_content = False
            options.include_tutorial_content = False
            options.include_documentation = True
        
        self.logger.info(f"Searching for {content_type} content on topic: {topic}")
        
        resources, _ = await self.search_learning_resources(topic, options)
        
        # Additional filtering by content type
        filtered_resources = [
            resource for resource in resources 
            if resource.content_type == content_type or 
               content_type in resource.title.lower() or 
               content_type in resource.description.lower()
        ]
        
        return filtered_resources
    
    def get_search_suggestions(self, partial_topic: str) -> List[str]:
        """Get search suggestions for partial topic input.
        
        Args:
            partial_topic: Partial or incomplete topic string
            
        Returns:
            List of suggested complete topics
        """
        if not partial_topic or len(partial_topic) < 2:
            return []
        
        # Common learning topics and expansions
        topic_suggestions = {
            'python': ['python programming', 'python web development', 'python data science'],
            'javascript': ['javascript fundamentals', 'javascript frameworks', 'javascript backend'],
            'react': ['react hooks', 'react components', 'react state management'],
            'machine': ['machine learning', 'machine learning algorithms', 'machine learning python'],
            'data': ['data science', 'data analysis', 'data structures'],
            'web': ['web development', 'web design', 'web frameworks'],
            'api': ['api development', 'api design', 'rest api'],
            'database': ['database design', 'database management', 'sql database'],
            'docker': ['docker containers', 'docker deployment', 'docker compose'],
            'git': ['git version control', 'git workflow', 'git commands']
        }
        
        partial_lower = partial_topic.lower()
        suggestions = []
        
        # Find matching topics
        for key, values in topic_suggestions.items():
            if key.startswith(partial_lower) or partial_lower in key:
                suggestions.extend(values)
        
        # If no specific matches, provide general suggestions
        if not suggestions:
            general_suggestions = [
                f"{partial_topic} tutorial",
                f"{partial_topic} guide",
                f"learn {partial_topic}",
                f"{partial_topic} for beginners"
            ]
            suggestions.extend(general_suggestions)
        
        return suggestions[:5]  # Return top 5 suggestions