"""Data models for learning resources and scraped content."""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum
import json
import re
from urllib.parse import urlparse


class ContentType(Enum):
    """Enumeration of supported content types."""
    VIDEO = "video"
    TUTORIAL = "tutorial"
    DISCUSSION = "discussion"


class CommandIntent(Enum):
    """Enumeration of command intents for natural language processing."""
    TOPIC_SEARCH = "topic_search"
    URL_CRAWL = "url_crawl"
    UNKNOWN = "unknown"


class ConfidenceLevel(Enum):
    """Enumeration of confidence levels for intent classification."""
    HIGH = "high"      # > 0.8
    MEDIUM = "medium"  # 0.5 - 0.8
    LOW = "low"        # < 0.5


class ValidationError(Exception):
    """Custom exception for validation errors."""
    pass


@dataclass
class CommandPattern:
    """Represents a pattern for matching natural language commands."""
    
    pattern: str
    intent: CommandIntent
    confidence_boost: float = 0.0
    parameter_extractors: Dict[str, str] = field(default_factory=dict)
    
    def matches(self, text: str) -> bool:
        """Check if the pattern matches the given text."""
        return bool(re.search(self.pattern, text, re.IGNORECASE))
    
    def extract_parameters(self, text: str) -> Dict[str, Any]:
        """Extract parameters from text using the defined extractors."""
        parameters = {}
        for param_name, extractor_pattern in self.parameter_extractors.items():
            match = re.search(extractor_pattern, text, re.IGNORECASE)
            if match:
                # Try to get the last group if multiple groups exist
                try:
                    if match.lastindex and match.lastindex > 0:
                        parameters[param_name] = match.group(match.lastindex).strip()
                    else:
                        parameters[param_name] = match.group(1).strip()
                except IndexError:
                    # Fallback to group 0 (entire match) minus the command part
                    full_match = match.group(0).strip()
                    # Try to extract just the topic part
                    topic_match = re.search(r'(?:about|on|for|learn|find|search|show|give|help|teach|what|how|courses?|tutorials?|guides?)\s+(?:me\s+)?(?:some\s+)?(?:about\s+|on\s+|for\s+|with\s+)?(.+)', full_match, re.IGNORECASE)
                    if topic_match:
                        parameters[param_name] = topic_match.group(1).strip()
                    else:
                        parameters[param_name] = full_match
        return parameters


@dataclass
class IntentClassificationResult:
    """Result of intent classification with confidence and reasoning."""
    
    intent: CommandIntent
    confidence: float
    matched_patterns: List[str] = field(default_factory=list)
    extracted_entities: Dict[str, Any] = field(default_factory=dict)
    reasoning: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'intent': self.intent.value,
            'confidence': self.confidence,
            'matched_patterns': self.matched_patterns,
            'extracted_entities': self.extracted_entities,
            'reasoning': self.reasoning
        }


@dataclass
class LearningResource:
    """Represents a discovered learning resource from search results."""
    
    url: str
    title: str
    description: str
    relevance_score: float
    content_type: str
    estimated_quality: float
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'url': self.url,
            'title': self.title,
            'description': self.description,
            'relevance_score': self.relevance_score,
            'content_type': self.content_type,
            'estimated_quality': self.estimated_quality
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'LearningResource':
        """Create instance from dictionary."""
        return cls(
            url=data['url'],
            title=data['title'],
            description=data['description'],
            relevance_score=data['relevance_score'],
            content_type=data['content_type'],
            estimated_quality=data['estimated_quality']
        )


@dataclass
class VideoContent:
    """Represents extracted video content with metadata."""
    
    title: str
    url: str
    duration: Optional[int] = None
    description: str = ""
    download_path: Optional[str] = None
    thumbnail_url: Optional[str] = None
    file_size_mb: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'title': self.title,
            'url': self.url,
            'duration': self.duration,
            'description': self.description,
            'download_path': self.download_path,
            'thumbnail_url': self.thumbnail_url,
            'file_size_mb': self.file_size_mb
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'VideoContent':
        """Create instance from dictionary."""
        return cls(
            title=data['title'],
            url=data['url'],
            duration=data.get('duration'),
            description=data.get('description', ''),
            download_path=data.get('download_path'),
            thumbnail_url=data.get('thumbnail_url'),
            file_size_mb=data.get('file_size_mb')
        )


@dataclass
class TutorialContent:
    """Represents extracted tutorial content with structure."""
    
    title: str
    content: str
    sections: List[str] = field(default_factory=list)
    code_examples: List[str] = field(default_factory=list)
    images: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'title': self.title,
            'content': self.content,
            'sections': self.sections,
            'code_examples': self.code_examples,
            'images': self.images
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TutorialContent':
        """Create instance from dictionary."""
        return cls(
            title=data['title'],
            content=data['content'],
            sections=data.get('sections', []),
            code_examples=data.get('code_examples', []),
            images=data.get('images', [])
        )


@dataclass
class DiscussionContent:
    """Represents extracted discussion content from forums/comments."""
    
    title: str
    posts: List[Dict[str, Any]] = field(default_factory=list)
    comments: List[Dict[str, Any]] = field(default_factory=list)
    qa_pairs: List[Dict[str, Any]] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'title': self.title,
            'posts': self.posts,
            'comments': self.comments,
            'qa_pairs': self.qa_pairs
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DiscussionContent':
        """Create instance from dictionary."""
        return cls(
            title=data['title'],
            posts=data.get('posts', []),
            comments=data.get('comments', []),
            qa_pairs=data.get('qa_pairs', [])
        )


@dataclass
class CrawledContent:
    """Represents all content extracted from a single URL."""
    
    url: str
    title: str
    videos: List[VideoContent] = field(default_factory=list)
    tutorials: List[TutorialContent] = field(default_factory=list)
    discussions: List[DiscussionContent] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'url': self.url,
            'title': self.title,
            'videos': [v.to_dict() for v in self.videos],
            'tutorials': [t.to_dict() for t in self.tutorials],
            'discussions': [d.to_dict() for d in self.discussions],
            'metadata': self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CrawledContent':
        """Create instance from dictionary."""
        return cls(
            url=data['url'],
            title=data['title'],
            videos=[VideoContent.from_dict(v) for v in data.get('videos', [])],
            tutorials=[TutorialContent.from_dict(t) for t in data.get('tutorials', [])],
            discussions=[DiscussionContent.from_dict(d) for d in data.get('discussions', [])],
            metadata=data.get('metadata', {})
        )
    
    def get_content_summary(self) -> Dict[str, int]:
        """Get summary of extracted content counts."""
        return {
            'videos': len(self.videos),
            'tutorials': len(self.tutorials),
            'discussions': len(self.discussions)
        }


@dataclass
class ParsedCommand:
    """Represents a parsed natural language command with validation."""
    
    intent: CommandIntent
    topic: Optional[str] = None
    url: Optional[str] = None
    parameters: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.0
    original_text: str = ""
    ambiguous_parts: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        """Validate the parsed command after initialization."""
        self.validate()
    
    def validate(self) -> None:
        """Validate the parsed command parameters and intent classification."""
        # Validate confidence score
        if not 0.0 <= self.confidence <= 1.0:
            raise ValidationError(f"Confidence must be between 0.0 and 1.0, got {self.confidence}")
        
        # Validate intent-specific requirements
        if self.intent == CommandIntent.TOPIC_SEARCH:
            self._validate_topic_search()
        elif self.intent == CommandIntent.URL_CRAWL:
            self._validate_url_crawl()
        elif self.intent == CommandIntent.UNKNOWN:
            self._validate_unknown_intent()
    
    def _validate_topic_search(self) -> None:
        """Validate topic search command requirements."""
        if not self.topic or not self.topic.strip():
            raise ValidationError("Topic search requires a non-empty topic")
        
        cleaned_topic = self.topic.strip()
        if len(cleaned_topic) < 2:
            raise ValidationError("Topic must be at least 2 characters long")
        
        # Check for meaningless topics
        meaningless_patterns = [
            r'^(?:resources?\s*about\s*)+$',
            r'^(?:materials?\s*about\s*)+$',
            r'^(?:tutorials?\s*about\s*)+$',
            r'^(?:about\s*)+$'
        ]
        
        for pattern in meaningless_patterns:
            if re.match(pattern, cleaned_topic, re.IGNORECASE):
                raise ValidationError(f"Topic '{cleaned_topic}' is too vague")
        
        # URL should not be present for topic search
        if self.url:
            raise ValidationError("Topic search should not include a URL")
    
    def _validate_url_crawl(self) -> None:
        """Validate URL crawl command requirements."""
        if not self.url or not self.url.strip():
            raise ValidationError("URL crawl requires a non-empty URL")
        
        if not self.is_valid_url(self.url):
            raise ValidationError(f"Invalid URL format: {self.url}")
        
        # Topic should not be present for URL crawl
        if self.topic:
            raise ValidationError("URL crawl should not include a topic")
    
    def _validate_unknown_intent(self) -> None:
        """Validate unknown intent command."""
        if self.confidence > 0.5:
            raise ValidationError("Unknown intent should have low confidence")
    
    @staticmethod
    def is_valid_url(url: str) -> bool:
        """Check if the provided URL is valid."""
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except Exception:
            return False
    
    def get_confidence_level(self) -> ConfidenceLevel:
        """Get the confidence level category."""
        if self.confidence > 0.8:
            return ConfidenceLevel.HIGH
        elif self.confidence >= 0.5:
            return ConfidenceLevel.MEDIUM
        else:
            return ConfidenceLevel.LOW
    
    def is_ambiguous(self) -> bool:
        """Check if the command has ambiguous parts that need clarification."""
        return len(self.ambiguous_parts) > 0 or self.get_confidence_level() == ConfidenceLevel.LOW
    
    def needs_clarification(self) -> bool:
        """Check if the command needs clarification from the user."""
        return (
            self.intent == CommandIntent.UNKNOWN or
            self.is_ambiguous() or
            self.get_confidence_level() == ConfidenceLevel.LOW
        )
    
    def get_clarification_questions(self) -> List[str]:
        """Generate clarification questions for ambiguous commands."""
        questions = []
        
        if self.intent == CommandIntent.UNKNOWN:
            questions.append("Are you looking to search for learning resources on a topic, or crawl a specific URL?")
        
        if self.is_ambiguous():
            for ambiguous_part in self.ambiguous_parts:
                questions.append(f"Could you clarify what you mean by '{ambiguous_part}'?")
        
        if self.intent == CommandIntent.TOPIC_SEARCH and not self.topic:
            questions.append("What topic would you like to search for learning resources about?")
        
        if self.intent == CommandIntent.URL_CRAWL and not self.url:
            questions.append("What URL would you like to crawl for learning content?")
        
        return questions
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'intent': self.intent.value,
            'topic': self.topic,
            'url': self.url,
            'parameters': self.parameters,
            'confidence': self.confidence,
            'original_text': self.original_text,
            'ambiguous_parts': self.ambiguous_parts,
            'confidence_level': self.get_confidence_level().value,
            'needs_clarification': self.needs_clarification()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ParsedCommand':
        """Create instance from dictionary."""
        return cls(
            intent=CommandIntent(data['intent']),
            topic=data.get('topic'),
            url=data.get('url'),
            parameters=data.get('parameters', {}),
            confidence=data.get('confidence', 0.0),
            original_text=data.get('original_text', ''),
            ambiguous_parts=data.get('ambiguous_parts', [])
        )
    
    @classmethod
    def create_topic_search(cls, topic: str, confidence: float = 1.0, original_text: str = "") -> 'ParsedCommand':
        """Create a validated topic search command."""
        return cls(
            intent=CommandIntent.TOPIC_SEARCH,
            topic=topic.strip(),
            confidence=confidence,
            original_text=original_text
        )
    
    @classmethod
    def create_url_crawl(cls, url: str, confidence: float = 1.0, original_text: str = "") -> 'ParsedCommand':
        """Create a validated URL crawl command."""
        return cls(
            intent=CommandIntent.URL_CRAWL,
            url=url.strip(),
            confidence=confidence,
            original_text=original_text
        )
    
    @classmethod
    def create_unknown(cls, original_text: str = "", ambiguous_parts: List[str] = None) -> 'ParsedCommand':
        """Create an unknown intent command that needs clarification."""
        return cls(
            intent=CommandIntent.UNKNOWN,
            confidence=0.0,
            original_text=original_text,
            ambiguous_parts=ambiguous_parts or []
        )