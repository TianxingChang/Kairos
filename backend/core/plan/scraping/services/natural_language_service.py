"""Natural language processing service for command parsing and intent classification."""

import re
from typing import List, Dict, Any, Optional, Tuple
from urllib.parse import urlparse

from ..models.learning_resource import (
    ParsedCommand, CommandIntent, CommandPattern, IntentClassificationResult,
    ConfidenceLevel, ValidationError
)


class IntentClassifier:
    """Classifies user intents from natural language commands."""
    
    def __init__(self):
        """Initialize the intent classifier with predefined patterns."""
        self.patterns = self._initialize_patterns()
        self.url_indicators = [
            r'https?://[^\s]+',
            r'www\.[a-zA-Z0-9-]+\.[a-zA-Z]{2,}[^\s]*',
            r'\b[a-zA-Z0-9-]+\.[a-zA-Z]{2,}(?:/[^\s]*)?(?:\?[^\s]*)?(?:#[^\s]*)?(?:\s|$)'
        ]
        self.topic_indicators = [
            r'learn(?:ing)?\s+(?:about\s+)?(.+)',
            r'find\s+(?:me\s+)?(?:some\s+)?(?:resources?\s+(?:about|on|for)\s+)?(.+)',
            r'search\s+(?:for\s+)?(.+)',
            r'(?:what|how)\s+(?:about|to)\s+(.+)',
            r'resources?\s+(?:about|on|for)\s+(.+)',
            r'materials?\s+(?:about|on|for)\s+(.+)',
            r'tutorials?\s+(?:about|on|for)\s+(.+)',
            r'courses?\s+(?:about|on|for)\s+(.+)',
            r'(?:show|give)\s+me\s+(.+)',
            r'(?:help|teach)\s+me\s+(?:with\s+)?(.+)',
            r'(?:i\s+need\s+help\s+with)\s+(.+)'
        ]
    
    def _initialize_patterns(self) -> List[CommandPattern]:
        """Initialize command patterns for intent classification."""
        patterns = []
        
        # URL crawling patterns
        url_patterns = [
            CommandPattern(
                pattern=r'(?:crawl|scrape|extract|download)\s+(?:from\s+)?(?:this\s+)?(?:url\s+)?(?:https?://[^\s]+|www\.[^\s]+)',
                intent=CommandIntent.URL_CRAWL,
                confidence_boost=0.3,
                parameter_extractors={'url': r'(https?://[^\s]+|www\.[^\s]+)'}
            ),
            CommandPattern(
                pattern=r'(?:get|fetch|pull)\s+(?:content|data|materials?)\s+from\s+(?:https?://[^\s]+|www\.[^\s]+)',
                intent=CommandIntent.URL_CRAWL,
                confidence_boost=0.25,
                parameter_extractors={'url': r'from\s+(https?://[^\s]+|www\.[^\s]+)'}
            ),
            CommandPattern(
                pattern=r'(?:analyze|process|parse)\s+(?:this\s+)?(?:url|website|page)\s*:?\s*(?:https?://[^\s]+|www\.[^\s]+)',
                intent=CommandIntent.URL_CRAWL,
                confidence_boost=0.2,
                parameter_extractors={'url': r'(?:url|website|page)\s*:?\s*(https?://[^\s]+|www\.[^\s]+)'}
            ),
            CommandPattern(
                pattern=r'https?://[^\s]+',
                intent=CommandIntent.URL_CRAWL,
                confidence_boost=0.1,
                parameter_extractors={'url': r'(https?://[^\s]+)'}
            ),
            CommandPattern(
                pattern=r'\bwww\.[a-zA-Z0-9-]+\.[a-zA-Z]{2,}[^\s]*',
                intent=CommandIntent.URL_CRAWL,
                confidence_boost=0.1,
                parameter_extractors={'url': r'(www\.[a-zA-Z0-9-]+\.[a-zA-Z]{2,}[^\s]*)'}
            )
        ]
        
        # Topic search patterns
        topic_patterns = [
            CommandPattern(
                pattern=r'(?:find|search|look\s+for)\s+(?:learning\s+)?(?:resources?|materials?|content)\s+(?:about|on|for)\s+(.+)',
                intent=CommandIntent.TOPIC_SEARCH,
                confidence_boost=0.3,
                parameter_extractors={'topic': r'(?:about|on|for)\s+(.+)'}
            ),
            CommandPattern(
                pattern=r'(?:find|search|look\s+for)\s+(?:me\s+)?(?:some\s+)?(.+?)(?:\s+(?:resources?|materials?|tutorials?|courses?))?$',
                intent=CommandIntent.TOPIC_SEARCH,
                confidence_boost=0.25,
                parameter_extractors={'topic': r'(?:find|search|look\s+for)\s+(?:me\s+)?(?:some\s+)?(.+?)(?:\s+(?:resources?|materials?|tutorials?|courses?))?$'}
            ),
            CommandPattern(
                pattern=r'(?:i\s+want\s+to\s+)?learn\s+(?:about\s+)?(.+)',
                intent=CommandIntent.TOPIC_SEARCH,
                confidence_boost=0.25,
                parameter_extractors={'topic': r'learn\s+(?:about\s+)?(.+)'}
            ),
            CommandPattern(
                pattern=r'(?:show|give)\s+me\s+(?:some\s+)?(?:resources?|materials?|tutorials?|content)?\s*(?:about|on|for)?\s*(.+)',
                intent=CommandIntent.TOPIC_SEARCH,
                confidence_boost=0.25,
                parameter_extractors={'topic': r'(?:show|give)\s+me\s+(?:some\s+)?(?:(?:resources?|materials?|tutorials?|content)\s+)?(?:about\s+|on\s+|for\s+)?(.+)'}
            ),
            CommandPattern(
                pattern=r'(?:give)\s+me\s+(.+?)\s+(?:resources?|materials?|tutorials?|content)',
                intent=CommandIntent.TOPIC_SEARCH,
                confidence_boost=0.3,
                parameter_extractors={'topic': r'(?:give)\s+me\s+(.+?)\s+(?:resources?|materials?|tutorials?|content)'}
            ),
            CommandPattern(
                pattern=r'(?:what|how)\s+(?:about|to)\s+(.+)',
                intent=CommandIntent.TOPIC_SEARCH,
                confidence_boost=0.3,
                parameter_extractors={'topic': r'(?:what|how)\s+(?:about|to)\s+(.+)'}
            ),
            CommandPattern(
                pattern=r'(?:help\s+me\s+(?:with|understand)|teach\s+me)\s+(.+)',
                intent=CommandIntent.TOPIC_SEARCH,
                confidence_boost=0.2,
                parameter_extractors={'topic': r'(?:help\s+me\s+(?:with|understand)|teach\s+me)\s+(.+)'}
            ),
            CommandPattern(
                pattern=r'(?:i\s+need\s+help\s+with|help\s+me\s+understand)\s+(.+)',
                intent=CommandIntent.TOPIC_SEARCH,
                confidence_boost=0.2,
                parameter_extractors={'topic': r'(?:i\s+need\s+help\s+with|help\s+me\s+understand)\s+(.+)'}
            ),
            CommandPattern(
                pattern=r'(?:courses?|tutorials?|guides?)\s+(?:about|on|for)\s+(.+)',
                intent=CommandIntent.TOPIC_SEARCH,
                confidence_boost=0.3,
                parameter_extractors={'topic': r'(?:courses?|tutorials?|guides?)\s+(?:about|on|for)\s+(.+)'}
            ),
            CommandPattern(
                pattern=r'(?:courses?|tutorials?|guides?)\s+(.+)',
                intent=CommandIntent.TOPIC_SEARCH,
                confidence_boost=0.1,
                parameter_extractors={'topic': r'(?:courses?|tutorials?|guides?)\s+(.+)'}
            ),
            CommandPattern(
                pattern=r'^(.+?)\s+(?:courses?|tutorials?|guides?)$',
                intent=CommandIntent.TOPIC_SEARCH,
                confidence_boost=0.4,
                parameter_extractors={'topic': r'^(.+?)\s+(?:courses?|tutorials?|guides?)$'}
            ),
            CommandPattern(
                pattern=r'(?:look\s+for)\s+(.+?)(?:\s+(?:resources?|materials?|tutorials?|courses?))?',
                intent=CommandIntent.TOPIC_SEARCH,
                confidence_boost=0.25,
                parameter_extractors={'topic': r'(?:look\s+for)\s+(.+?)(?:\s+(?:resources?|materials?|tutorials?|courses?))?'}
            ),
            CommandPattern(
                pattern=r'^learn\s+(.+)',
                intent=CommandIntent.TOPIC_SEARCH,
                confidence_boost=0.3,
                parameter_extractors={'topic': r'^learn\s+(.+)'}
            ),
            CommandPattern(
                pattern=r'(?:i\s+)?(?:need\s+to\s+understand|want\s+to\s+study|interested\s+in\s+learning\s+about)\s+(.+)',
                intent=CommandIntent.TOPIC_SEARCH,
                confidence_boost=0.3,
                parameter_extractors={'topic': r'(?:need\s+to\s+understand|want\s+to\s+study|interested\s+in\s+learning\s+about)\s+(.+)'}
            ),
            CommandPattern(
                pattern=r'(?:can\s+you\s+find\s+me|could\s+you\s+show\s+me|please\s+find\s+me)\s+(?:some\s+)?(.+?)(?:\s+(?:tutorials?|resources?|materials?|courses?))?$',
                intent=CommandIntent.TOPIC_SEARCH,
                confidence_boost=0.4,
                parameter_extractors={'topic': r'(?:can\s+you\s+find\s+me|could\s+you\s+show\s+me|please\s+find\s+me)\s+(?:some\s+)?(.+?)(?:\s+(?:tutorials?|resources?|materials?|courses?))?$'}
            ),
            CommandPattern(
                pattern=r'(?:looking\s+for|need\s+help\s+learning|any\s+good\s+resources\s+for\s+learning|best\s+materials\s+for\s+studying|where\s+can\s+i\s+learn\s+about)\s+(.+)',
                intent=CommandIntent.TOPIC_SEARCH,
                confidence_boost=0.3,
                parameter_extractors={'topic': r'(?:looking\s+for|need\s+help\s+learning|any\s+good\s+resources\s+for\s+learning|best\s+materials\s+for\s+studying|where\s+can\s+i\s+learn\s+about)\s+(.+)'}
            ),
            CommandPattern(
                pattern=r'(?:i\s+want\s+to\s+master|need\s+comprehensive|i\'d\s+like\s+to\s+learn)\s+(.+)',
                intent=CommandIntent.TOPIC_SEARCH,
                confidence_boost=0.4,
                parameter_extractors={'topic': r'(?:i\s+want\s+to\s+master|need\s+comprehensive|i\'d\s+like\s+to\s+learn)\s+(.+)'}
            ),
            CommandPattern(
                pattern=r'(?:i\s+need\s+to\s+understand|need\s+help\s+learning|want\s+to\s+study|interested\s+in\s+learning\s+about)\s+(.+)',
                intent=CommandIntent.TOPIC_SEARCH,
                confidence_boost=0.3,
                parameter_extractors={'topic': r'(?:i\s+need\s+to\s+understand|need\s+help\s+learning|want\s+to\s+study|interested\s+in\s+learning\s+about)\s+(.+)'}
            ),
            CommandPattern(
                pattern=r'(?:i\s+need\s+materials?\s+about|need\s+help\s+with|help\s+me\s+find)\s+(.+)',
                intent=CommandIntent.TOPIC_SEARCH,
                confidence_boost=0.3,
                parameter_extractors={'topic': r'(?:i\s+need\s+materials?\s+about|need\s+help\s+with|help\s+me\s+find)\s+(.+)'}
            ),
            CommandPattern(
                pattern=r'^(?:looking\s+for|need\s+help\s+learning|want\s+to\s+study|need\s+comprehensive)\s+(.+)',
                intent=CommandIntent.TOPIC_SEARCH,
                confidence_boost=0.3,
                parameter_extractors={'topic': r'^(?:looking\s+for|need\s+help\s+learning|want\s+to\s+study|need\s+comprehensive)\s+(.+)'}
            ),
            CommandPattern(
                pattern=r'(?:best\s+materials?\s+for\s+studying|any\s+good\s+resources?\s+for\s+learning|where\s+can\s+i\s+learn\s+about)\s+(.+)',
                intent=CommandIntent.TOPIC_SEARCH,
                confidence_boost=0.3,
                parameter_extractors={'topic': r'(?:best\s+materials?\s+for\s+studying|any\s+good\s+resources?\s+for\s+learning|where\s+can\s+i\s+learn\s+about)\s+(.+)'}
            )
        ]
        
        patterns.extend(url_patterns)
        patterns.extend(topic_patterns)
        
        return patterns
    
    def classify_intent(self, text: str) -> IntentClassificationResult:
        """Classify the intent of a natural language command."""
        text = text.strip()
        if not text:
            return IntentClassificationResult(
                intent=CommandIntent.UNKNOWN,
                confidence=0.0,
                reasoning="Empty input text"
            )
        
        # Check for URL patterns first (higher priority)
        url_result = self._check_url_intent(text)
        if url_result.confidence > 0.5:
            return url_result
        
        # Check for topic search patterns
        topic_result = self._check_topic_intent(text)
        if topic_result.confidence > 0.5:
            return topic_result
        
        # Return the result with higher confidence
        if url_result.confidence >= topic_result.confidence:
            return url_result
        else:
            return topic_result
    
    def _check_url_intent(self, text: str) -> IntentClassificationResult:
        """Check if the text indicates URL crawling intent."""
        base_confidence = 0.0
        matched_patterns = []
        extracted_entities = {}
        
        # Check for URL presence and extract it
        url_found = False
        found_url = None
        
        # Check for obvious URLs first
        if re.search(r'https?://[^\s]+', text, re.IGNORECASE):
            match = re.search(r'(https?://[^\s]+)', text, re.IGNORECASE)
            if match:
                url_found = True
                found_url = match.group(1)
                base_confidence += 0.4
        elif re.search(r'www\.[a-zA-Z0-9-]+\.[a-zA-Z]{2,}', text, re.IGNORECASE):
            match = re.search(r'(www\.[a-zA-Z0-9-]+\.[a-zA-Z]{2,}[^\s]*)', text, re.IGNORECASE)
            if match:
                url_found = True
                found_url = match.group(1)
                base_confidence += 0.4
        else:
            # Check for domain patterns but be more careful
            domain_pattern = r'\b([a-zA-Z0-9-]+\.[a-zA-Z]{2,}(?:/[^\s]*)?)'
            matches = re.findall(domain_pattern, text, re.IGNORECASE)
            
            for match in matches:
                # Skip known tech terms
                tech_exceptions = [
                    'node.js', 'vue.js', 'angular.js', 'react.js', 'express.js',
                    'next.js', 'nuxt.js', 'd3.js', 'three.js', 'chart.js',
                    '.net', 'asp.net', 'vb.net'
                ]
                
                if any(exception.lower() in match.lower() for exception in tech_exceptions):
                    continue
                    
                # If it has a path or common TLD, consider it a URL
                if ('/' in match or 
                    any(tld in match.lower() for tld in ['.com', '.org', '.net', '.edu', '.gov', '.io', '.co'])):
                    url_found = True
                    found_url = match
                    base_confidence += 0.3
                    break
        
        # Check command patterns
        for pattern in self.patterns:
            if pattern.intent == CommandIntent.URL_CRAWL and pattern.matches(text):
                matched_patterns.append(pattern.pattern)
                base_confidence += pattern.confidence_boost
                
                # Extract parameters
                params = pattern.extract_parameters(text)
                extracted_entities.update(params)
        
        # If URL found but not extracted by patterns, add it
        if url_found and 'url' not in extracted_entities and found_url:
            extracted_entities['url'] = found_url
        
        # Boost confidence if URL is found
        if url_found:
            base_confidence += 0.2
        
        # Cap confidence at 1.0
        confidence = min(base_confidence, 1.0)
        
        reasoning = f"Found URL indicators: {url_found}, Matched patterns: {len(matched_patterns)}"
        
        return IntentClassificationResult(
            intent=CommandIntent.URL_CRAWL,
            confidence=confidence,
            matched_patterns=matched_patterns,
            extracted_entities=extracted_entities,
            reasoning=reasoning
        )
    
    def _check_topic_intent(self, text: str) -> IntentClassificationResult:
        """Check if the text indicates topic search intent."""
        base_confidence = 0.0
        matched_patterns = []
        extracted_entities = {}
        
        # Check command patterns
        for pattern in self.patterns:
            if pattern.intent == CommandIntent.TOPIC_SEARCH and pattern.matches(text):
                matched_patterns.append(pattern.pattern)
                base_confidence += pattern.confidence_boost
                
                # Extract parameters
                params = pattern.extract_parameters(text)
                extracted_entities.update(params)
        
        # Check for topic indicators
        for topic_pattern in self.topic_indicators:
            match = re.search(topic_pattern, text, re.IGNORECASE)
            if match:
                base_confidence += 0.2  # Increased from 0.1
                if 'topic' not in extracted_entities:
                    extracted_entities['topic'] = match.group(1).strip()
        
        # Add base confidence for common topic search words
        topic_keywords = ['learn', 'find', 'search', 'show', 'help', 'teach', 'course', 'tutorial', 'guide', 'resource', 'material', 'master', 'study', 'understand']
        keyword_found = False
        for keyword in topic_keywords:
            if re.search(r'\b' + keyword + r's?\b', text, re.IGNORECASE):  # Added 's?' for plurals
                base_confidence += 0.2  # Increased from 0.15
                keyword_found = True
                break
        
        # Reduce confidence for very short or vague inputs
        if len(text.strip().split()) <= 1 and keyword_found:
            base_confidence -= 0.1  # Reduce confidence for single word inputs like "help"
        
        # Handle short topic inputs (single words that look like topics)
        if len(text.strip().split()) <= 2 and not self._contains_url(text):
            # Check if it looks like a technology/topic name
            tech_patterns = [
                r'\b(?:python|javascript|java|react|angular|vue|node|docker|kubernetes|git|sql|html|css|php|ruby|go|rust|swift|kotlin|scala|typescript|c\+\+|c#|\.net)\b',
                r'\b(?:machine\s*learning|data\s*science|artificial\s*intelligence|web\s*development|software\s*engineering|programming|coding)\b',
                r'\b(?:algorithms|databases|networking|security|devops|cloud|aws|azure|gcp)\b'
            ]
            
            for pattern in tech_patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    base_confidence += 0.4
                    if 'topic' not in extracted_entities:
                        extracted_entities['topic'] = text.strip()
                    break
            
            # If it's a short input without URL indicators, likely a topic
            if not any(re.search(url_pattern, text, re.IGNORECASE) for url_pattern in self.url_indicators):
                base_confidence += 0.3
                if 'topic' not in extracted_entities and len(text.strip()) >= 2:
                    extracted_entities['topic'] = text.strip()
        
        # Penalize if URL is present
        for url_pattern in self.url_indicators:
            if re.search(url_pattern, text, re.IGNORECASE):
                base_confidence -= 0.4  # Increased penalty
                break
        
        # Cap confidence at 1.0 and ensure non-negative
        confidence = max(0.0, min(base_confidence, 1.0))
        
        reasoning = f"Matched topic patterns: {len(matched_patterns)}, Topic indicators found"
        
        return IntentClassificationResult(
            intent=CommandIntent.TOPIC_SEARCH,
            confidence=confidence,
            matched_patterns=matched_patterns,
            extracted_entities=extracted_entities,
            reasoning=reasoning
        )
    
    def _contains_url(self, text: str) -> bool:
        """Check if text contains a URL."""
        # First check for obvious URLs
        if re.search(r'https?://[^\s]+', text, re.IGNORECASE):
            return True
        if re.search(r'www\.[a-zA-Z0-9-]+\.[a-zA-Z]{2,}', text, re.IGNORECASE):
            return True
        
        # Check for domain-like patterns, but exclude common tech terms
        tech_exceptions = [
            'node.js', 'vue.js', 'angular.js', 'react.js', 'express.js',
            'next.js', 'nuxt.js', 'd3.js', 'three.js', 'chart.js',
            '.net', 'asp.net', 'vb.net', 'c#.net'
        ]
        
        # Look for domain patterns
        domain_pattern = r'\b[a-zA-Z0-9-]+\.[a-zA-Z]{2,}(?:/[^\s]*)?(?:\?[^\s]*)?(?:#[^\s]*)?'
        matches = re.findall(domain_pattern, text, re.IGNORECASE)
        
        for match in matches:
            # Skip if it's a known tech term
            if any(exception.lower() in match.lower() for exception in tech_exceptions):
                continue
            # If it looks like a real domain (has path or common TLD), consider it a URL
            if ('/' in match or 
                any(tld in match.lower() for tld in ['.com', '.org', '.net', '.edu', '.gov', '.io', '.co'])):
                return True
        
        return False


class CommandParser:
    """Parses natural language commands and extracts parameters."""
    
    def __init__(self):
        """Initialize the command parser."""
        self.intent_classifier = IntentClassifier()
    
    def extract_topic(self, text: str) -> Optional[str]:
        """Extract topic from natural language text."""
        # First check if URL is present - if so, don't extract topic
        if self._contains_url(text):
            return None
        
        # Remove common stop words and phrases
        cleaned_text = self._clean_text_for_topic(text)
        
        # Try specific topic extraction patterns
        topic_patterns = [
            r'(?:learn|learning)\s+(?:about\s+)?(.+)',
            r'(?:find|search|look\s+for)\s+(?:resources?\s+)?(?:about|on|for)\s+(.+)',
            r'(?:show|give)\s+me\s+(?:some\s+)?(?:resources?\s+)?(?:about|on|for)\s+(.+)',
            r'(?:help\s+me\s+with|teach\s+me)\s+(.+)',
            r'(?:what|how)\s+(?:about|to)\s+(.+)',
            r'(?:courses?|tutorials?|guides?)\s+(?:about|on|for)\s+(.+)',
            r'(?:materials?\s+)?(?:about|on|for)\s+(.+)'
        ]
        
        for pattern in topic_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                topic = match.group(1).strip()
                # Clean up the extracted topic
                topic = self._clean_extracted_topic(topic)
                if topic and len(topic) >= 2 and not self._contains_url(topic):
                    return topic
        
        # Fallback: use the cleaned text if it looks like a topic
        if cleaned_text and len(cleaned_text) >= 2 and not self._contains_url(cleaned_text):
            return cleaned_text
        
        return None
    
    def extract_url(self, text: str) -> Optional[str]:
        """Extract URL from natural language text."""
        # URL patterns in order of preference
        url_patterns = [
            r'(https?://[^\s]+)',
            r'(www\.[^\s]+)',
            r'([a-zA-Z0-9-]+\.[a-zA-Z]{2,}[^\s]*)'
        ]
        
        for pattern in url_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                url = match.group(1).strip()
                # Clean up the URL
                url = self._clean_extracted_url(url)
                if self._is_valid_url(url):
                    return url
        
        return None
    
    def _clean_text_for_topic(self, text: str) -> str:
        """Clean text for topic extraction."""
        # Remove URLs first
        text = re.sub(r'https?://[^\s]+', '', text)
        text = re.sub(r'www\.[^\s]+', '', text)
        text = re.sub(r'[a-zA-Z0-9-]+\.[a-zA-Z]{2,}[^\s]*', '', text)
        
        # Remove common command words
        command_words = [
            r'\b(?:find|search|look\s+for|show|give\s+me|help\s+me\s+with|teach\s+me)\b',
            r'\b(?:resources?|materials?|content|tutorials?|courses?|guides?)\b',
            r'\b(?:about|on|for|some|any)\b',
            r'\b(?:i\s+want\s+to|please|can\s+you)\b'
        ]
        
        for pattern in command_words:
            text = re.sub(pattern, ' ', text, flags=re.IGNORECASE)
        
        # Clean up whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text
    
    def _clean_extracted_topic(self, topic: str) -> str:
        """Clean up extracted topic text."""
        # Remove trailing punctuation
        topic = re.sub(r'[.!?]+$', '', topic)
        
        # Remove common trailing words
        topic = re.sub(r'\s+(?:please|thanks?|thank\s+you)$', '', topic, flags=re.IGNORECASE)
        
        # Remove common stop words that might be extracted
        topic = re.sub(r'^(?:resources?\s+about\s+|materials?\s+about\s+|tutorials?\s+about\s+)', '', topic, flags=re.IGNORECASE)
        
        # Clean up whitespace
        topic = re.sub(r'\s+', ' ', topic).strip()
        
        return topic
    
    def _clean_extracted_url(self, url: str) -> str:
        """Clean up extracted URL."""
        # Remove trailing punctuation
        url = re.sub(r'[.!?]+$', '', url)
        
        # Add protocol if missing
        if not url.startswith(('http://', 'https://')):
            if url.startswith('www.'):
                url = 'https://' + url
            elif '.' in url:
                url = 'https://' + url
        
        return url
    
    def _contains_url(self, text: str) -> bool:
        """Check if text contains a URL."""
        url_patterns = [
            r'https?://[^\s]+',
            r'www\.[^\s]+',
            r'[a-zA-Z0-9-]+\.[a-zA-Z]{2,}'
        ]
        
        for pattern in url_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        
        return False
    
    def _is_valid_url(self, url: str) -> bool:
        """Check if the URL is valid."""
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except Exception:
            return False


class NaturalLanguageService:
    """Main service for natural language processing and command parsing."""
    
    def __init__(self):
        """Initialize the natural language service."""
        self.intent_classifier = IntentClassifier()
        self.command_parser = CommandParser()
    
    async def parse_command(self, user_input: str) -> ParsedCommand:
        """Parse a natural language command and return structured result."""
        if not user_input or not user_input.strip():
            return ParsedCommand.create_unknown(
                original_text=user_input,
                ambiguous_parts=["empty input"]
            )
        
        # Classify intent
        classification_result = self.intent_classifier.classify_intent(user_input)
        
        # Extract parameters based on intent
        topic = None
        url = None
        ambiguous_parts = []
        
        if classification_result.intent == CommandIntent.TOPIC_SEARCH:
            topic = self._extract_topic_from_classification(user_input, classification_result)
            if not topic:
                ambiguous_parts.append("topic not clearly specified")
        
        elif classification_result.intent == CommandIntent.URL_CRAWL:
            url = self._extract_url_from_classification(user_input, classification_result)
            if not url:
                ambiguous_parts.append("URL not found or invalid")
        
        # Handle low confidence or unknown intent
        if (classification_result.confidence < 0.5 or 
            classification_result.intent == CommandIntent.UNKNOWN):
            return ParsedCommand.create_unknown(
                original_text=user_input,
                ambiguous_parts=ambiguous_parts or ["intent unclear"]
            )
        
        # Create parsed command
        try:
            if classification_result.intent == CommandIntent.TOPIC_SEARCH:
                return ParsedCommand.create_topic_search(
                    topic=topic or "",
                    confidence=classification_result.confidence,
                    original_text=user_input
                )
            elif classification_result.intent == CommandIntent.URL_CRAWL:
                return ParsedCommand.create_url_crawl(
                    url=url or "",
                    confidence=classification_result.confidence,
                    original_text=user_input
                )
        except ValidationError:
            # If validation fails, return unknown with ambiguous parts
            return ParsedCommand.create_unknown(
                original_text=user_input,
                ambiguous_parts=ambiguous_parts or ["validation failed"]
            )
        
        # Fallback to unknown
        return ParsedCommand.create_unknown(
            original_text=user_input,
            ambiguous_parts=["unable to parse command"]
        )
    
    async def classify_intent(self, command: str) -> CommandIntent:
        """Classify the intent of a command."""
        result = self.intent_classifier.classify_intent(command)
        return result.intent
    
    async def extract_parameters(self, command: str, intent: CommandIntent) -> Dict[str, Any]:
        """Extract parameters from command based on intent."""
        parameters = {}
        
        if intent == CommandIntent.TOPIC_SEARCH:
            topic = self.command_parser.extract_topic(command)
            if topic:
                parameters['topic'] = topic
        
        elif intent == CommandIntent.URL_CRAWL:
            url = self.command_parser.extract_url(command)
            if url:
                parameters['url'] = url
        
        return parameters
    
    def _extract_topic_from_classification(self, text: str, classification: IntentClassificationResult) -> Optional[str]:
        """Extract topic using classification results."""
        # First try extracted entities from classification
        if 'topic' in classification.extracted_entities:
            topic = classification.extracted_entities['topic']
            if topic and len(topic.strip()) >= 2:
                return topic.strip()
        
        # Fallback to command parser
        return self.command_parser.extract_topic(text)
    
    def _extract_url_from_classification(self, text: str, classification: IntentClassificationResult) -> Optional[str]:
        """Extract URL using classification results."""
        # First try extracted entities from classification
        if 'url' in classification.extracted_entities:
            url = classification.extracted_entities['url']
            if url and self.command_parser._is_valid_url(url):
                return url
        
        # Fallback to command parser
        return self.command_parser.extract_url(text)
    
    def get_supported_phrasings(self) -> Dict[str, List[str]]:
        """Get examples of supported command phrasings."""
        return {
            'topic_search': [
                "Find learning resources about Python programming",
                "I want to learn machine learning",
                "Search for tutorials on web development",
                "Show me materials about data science",
                "Help me with JavaScript",
                "What about React framework?",
                "Courses for artificial intelligence"
            ],
            'url_crawl': [
                "Crawl https://example.com/tutorial",
                "Extract content from www.example.com",
                "Scrape this URL: https://example.com",
                "Get materials from https://example.com/course",
                "Download from https://example.com/videos",
                "Analyze this website: https://example.com"
            ]
        }