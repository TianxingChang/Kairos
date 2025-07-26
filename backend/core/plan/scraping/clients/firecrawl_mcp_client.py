"""Firecrawl MCP client for web scraping operations."""

import asyncio
import json
import logging
import time
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass
from enum import Enum
import aiohttp
from urllib.parse import urljoin, urlparse

from ..config.firecrawl_config import FirecrawlConfig
from ..models.learning_resource import LearningResource, CrawledContent


class MCPConnectionState(Enum):
    """Enumeration of MCP connection states."""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"
    RECONNECTING = "reconnecting"


class MCPError(Exception):
    """Base exception for MCP-related errors."""
    pass


class MCPConnectionError(MCPError):
    """Exception raised when MCP connection fails."""
    pass


class MCPRateLimitError(MCPError):
    """Exception raised when rate limit is exceeded."""
    pass


class MCPTimeoutError(MCPError):
    """Exception raised when MCP operation times out."""
    pass


@dataclass
class MCPHealthStatus:
    """Represents the health status of MCP connection."""
    
    is_healthy: bool
    connection_state: MCPConnectionState
    last_check_time: float
    error_message: Optional[str] = None
    response_time_ms: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'is_healthy': self.is_healthy,
            'connection_state': self.connection_state.value,
            'last_check_time': self.last_check_time,
            'error_message': self.error_message,
            'response_time_ms': self.response_time_ms
        }


@dataclass
class RateLimitInfo:
    """Information about rate limiting status."""
    
    requests_made: int
    requests_remaining: int
    reset_time: float
    window_start: float
    
    def is_rate_limited(self) -> bool:
        """Check if currently rate limited."""
        return self.requests_remaining <= 0 and time.time() < self.reset_time
    
    def time_until_reset(self) -> float:
        """Get seconds until rate limit resets."""
        return max(0, self.reset_time - time.time())


class MCPConnectionManager:
    """Manages MCP connection lifecycle and reconnection logic."""
    
    def __init__(self, config: FirecrawlConfig):
        """Initialize connection manager with configuration.
        
        Args:
            config: Firecrawl configuration instance.
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        self._connection_state = MCPConnectionState.DISCONNECTED
        self._session: Optional[aiohttp.ClientSession] = None
        self._last_health_check = 0.0
        self._health_check_interval = 30.0  # seconds
        self._reconnect_attempts = 0
        self._max_reconnect_attempts = 5
        self._reconnect_delay = 1.0
        self._rate_limit_info: Optional[RateLimitInfo] = None
        
    @property
    def connection_state(self) -> MCPConnectionState:
        """Get current connection state."""
        return self._connection_state
    
    @property
    def is_connected(self) -> bool:
        """Check if currently connected."""
        return self._connection_state == MCPConnectionState.CONNECTED
    
    async def connect(self) -> bool:
        """Establish connection to MCP server.
        
        Returns:
            True if connection successful, False otherwise.
        
        Raises:
            MCPConnectionError: If connection fails after retries.
        """
        if self.is_connected:
            return True
            
        self._connection_state = MCPConnectionState.CONNECTING
        self.logger.info(f"Connecting to MCP server at {self.config.mcp_server_url}")
        
        try:
            # Create aiohttp session with timeout
            timeout = aiohttp.ClientTimeout(total=self.config.timeout_seconds)
            self._session = aiohttp.ClientSession(timeout=timeout)
            
            # Test connection with health check
            health_status = await self._perform_health_check()
            
            if health_status.is_healthy:
                self._connection_state = MCPConnectionState.CONNECTED
                self._reconnect_attempts = 0
                self.logger.info("Successfully connected to MCP server")
                return True
            else:
                self._connection_state = MCPConnectionState.ERROR
                raise MCPConnectionError(f"Health check failed: {health_status.error_message}")
                
        except Exception as e:
            self._connection_state = MCPConnectionState.ERROR
            self.logger.error(f"Failed to connect to MCP server: {e}")
            await self._cleanup_session()
            raise MCPConnectionError(f"Connection failed: {e}")
    
    async def disconnect(self) -> None:
        """Disconnect from MCP server."""
        self.logger.info("Disconnecting from MCP server")
        self._connection_state = MCPConnectionState.DISCONNECTED
        await self._cleanup_session()
    
    async def _cleanup_session(self) -> None:
        """Clean up aiohttp session."""
        if self._session:
            await self._session.close()
            self._session = None
    
    async def reconnect(self) -> bool:
        """Attempt to reconnect to MCP server with exponential backoff.
        
        Returns:
            True if reconnection successful, False otherwise.
        """
        if self._reconnect_attempts >= self._max_reconnect_attempts:
            self.logger.error("Max reconnection attempts reached")
            return False
        
        self._connection_state = MCPConnectionState.RECONNECTING
        self._reconnect_attempts += 1
        
        # Calculate delay with exponential backoff
        delay = self._reconnect_delay * (self.config.backoff_factor ** (self._reconnect_attempts - 1))
        self.logger.info(f"Reconnection attempt {self._reconnect_attempts} in {delay:.1f}s")
        
        await asyncio.sleep(delay)
        
        try:
            return await self.connect()
        except MCPConnectionError:
            return False
    
    async def health_check(self) -> MCPHealthStatus:
        """Perform health check on MCP connection.
        
        Returns:
            Health status information.
        """
        current_time = time.time()
        
        # Use cached result if recent
        if (current_time - self._last_health_check) < self._health_check_interval:
            return MCPHealthStatus(
                is_healthy=self.is_connected,
                connection_state=self._connection_state,
                last_check_time=self._last_health_check
            )
        
        return await self._perform_health_check()
    
    async def _perform_health_check(self) -> MCPHealthStatus:
        """Perform actual health check against MCP server."""
        start_time = time.time()
        
        try:
            if not self._session:
                raise MCPConnectionError("No active session")
            
            # Simple health check endpoint
            health_url = urljoin(self.config.mcp_server_url, "/health")
            
            async with self._session.get(health_url) as response:
                response_time = (time.time() - start_time) * 1000  # ms
                
                if response.status == 200:
                    self._last_health_check = time.time()
                    return MCPHealthStatus(
                        is_healthy=True,
                        connection_state=MCPConnectionState.CONNECTED,
                        last_check_time=self._last_health_check,
                        response_time_ms=response_time
                    )
                else:
                    error_msg = f"Health check failed with status {response.status}"
                    return MCPHealthStatus(
                        is_healthy=False,
                        connection_state=MCPConnectionState.ERROR,
                        last_check_time=time.time(),
                        error_message=error_msg,
                        response_time_ms=response_time
                    )
                    
        except Exception as e:
            return MCPHealthStatus(
                is_healthy=False,
                connection_state=MCPConnectionState.ERROR,
                last_check_time=time.time(),
                error_message=str(e)
            )
    
    async def ensure_connected(self) -> None:
        """Ensure connection is active, reconnect if necessary.
        
        Raises:
            MCPConnectionError: If unable to establish connection.
        """
        if not self.is_connected:
            success = await self.reconnect()
            if not success:
                raise MCPConnectionError("Unable to establish MCP connection")
    
    def update_rate_limit_info(self, headers: Dict[str, str]) -> None:
        """Update rate limit information from response headers.
        
        Args:
            headers: HTTP response headers containing rate limit info.
        """
        try:
            requests_made = int(headers.get('X-RateLimit-Used', 0))
            requests_remaining = int(headers.get('X-RateLimit-Remaining', self.config.rate_limit_per_minute))
            reset_time = float(headers.get('X-RateLimit-Reset', time.time() + 60))
            
            self._rate_limit_info = RateLimitInfo(
                requests_made=requests_made,
                requests_remaining=requests_remaining,
                reset_time=reset_time,
                window_start=time.time()
            )
        except (ValueError, TypeError) as e:
            self.logger.warning(f"Failed to parse rate limit headers: {e}")
    
    def get_rate_limit_info(self) -> Optional[RateLimitInfo]:
        """Get current rate limit information."""
        return self._rate_limit_info
    
    async def wait_for_rate_limit_reset(self) -> None:
        """Wait for rate limit to reset if currently limited."""
        if self._rate_limit_info and self._rate_limit_info.is_rate_limited():
            wait_time = self._rate_limit_info.time_until_reset()
            if wait_time > 0:
                self.logger.info(f"Rate limited, waiting {wait_time:.1f}s for reset")
                await asyncio.sleep(wait_time)


class FirecrawlMCPClient:
    """Client for interacting with Firecrawl MCP server."""
    
    def __init__(self, config: FirecrawlConfig):
        """Initialize Firecrawl MCP client.
        
        Args:
            config: Firecrawl configuration instance.
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.connection_manager = MCPConnectionManager(config)
        self._request_count = 0
        self._last_request_time = 0.0
        
    async def connect(self) -> bool:
        """Connect to Firecrawl MCP server.
        
        Returns:
            True if connection successful, False otherwise.
        """
        try:
            return await self.connection_manager.connect()
        except MCPConnectionError as e:
            self.logger.error(f"Failed to connect to MCP server: {e}")
            return False
    
    async def disconnect(self) -> None:
        """Disconnect from MCP server."""
        await self.connection_manager.disconnect()
    
    async def health_check(self) -> MCPHealthStatus:
        """Check health of MCP connection.
        
        Returns:
            Health status information.
        """
        return await self.connection_manager.health_check()
    
    async def _make_request(self, method: str, endpoint: str, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Make HTTP request to MCP server with error handling and retries.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path
            data: Request payload data
            
        Returns:
            Response data as dictionary
            
        Raises:
            MCPConnectionError: If connection fails
            MCPRateLimitError: If rate limited
            MCPTimeoutError: If request times out
            MCPError: For other MCP-related errors
        """
        await self.connection_manager.ensure_connected()
        
        # Check rate limiting
        await self.connection_manager.wait_for_rate_limit_reset()
        
        url = urljoin(self.config.mcp_server_url, endpoint)
        headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'FirecrawlLearningScraperMCP/1.0'
        }
        
        if self.config.api_key:
            headers['Authorization'] = f'Bearer {self.config.api_key}'
        
        for attempt in range(self.config.max_retries + 1):
            try:
                session = self.connection_manager._session
                if not session:
                    raise MCPConnectionError("No active session")
                
                # Make request
                if method.upper() == 'GET':
                    async with session.get(url, headers=headers, params=data) as response:
                        return await self._process_response(response)
                elif method.upper() == 'POST':
                    async with session.post(url, headers=headers, json=data) as response:
                        return await self._process_response(response)
                else:
                    raise MCPError(f"Unsupported HTTP method: {method}")
                    
            except asyncio.TimeoutError:
                if attempt == self.config.max_retries:
                    raise MCPTimeoutError(f"Request timed out after {self.config.timeout_seconds}s")
                await self._wait_before_retry(attempt)
                
            except aiohttp.ClientError as e:
                if attempt == self.config.max_retries:
                    raise MCPConnectionError(f"Request failed: {e}")
                await self._wait_before_retry(attempt)
                
            except MCPRateLimitError:
                # Rate limit errors should not be retried immediately
                raise
                
        raise MCPError("Max retries exceeded")
    
    async def _process_response(self, response: aiohttp.ClientResponse) -> Dict[str, Any]:
        """Process HTTP response and handle errors.
        
        Args:
            response: aiohttp response object
            
        Returns:
            Response data as dictionary
            
        Raises:
            MCPRateLimitError: If rate limited
            MCPError: For other errors
        """
        # Update rate limit info from headers
        self.connection_manager.update_rate_limit_info(dict(response.headers))
        
        if response.status == 429:
            raise MCPRateLimitError("Rate limit exceeded")
        elif response.status >= 400:
            error_text = await response.text()
            raise MCPError(f"HTTP {response.status}: {error_text}")
        
        try:
            return await response.json()
        except json.JSONDecodeError as e:
            raise MCPError(f"Invalid JSON response: {e}")
    
    async def _wait_before_retry(self, attempt: int) -> None:
        """Wait before retrying with exponential backoff.
        
        Args:
            attempt: Current attempt number (0-based)
        """
        delay = self.config.retry_delay * (self.config.backoff_factor ** attempt)
        self.logger.info(f"Retrying in {delay:.1f}s (attempt {attempt + 1})")
        await asyncio.sleep(delay)
    
    async def scrape_url(self, url: str, options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Scrape content from a specific URL using MCP tools.
        
        Args:
            url: URL to scrape
            options: Additional scraping options
            
        Returns:
            Scraped content data
            
        Raises:
            MCPError: If scraping fails
        """
        if not url or not url.strip():
            raise MCPError("URL cannot be empty")
        
        # Validate URL format
        parsed_url = urlparse(url)
        if not parsed_url.scheme or not parsed_url.netloc:
            raise MCPError(f"Invalid URL format: {url}")
        
        self.logger.info(f"Scraping URL: {url}")
        
        # Prepare request data
        request_data = {
            'url': url.strip(),
            'options': options or {}
        }
        
        # Add default options
        default_options = {
            'formats': ['markdown', 'html'],
            'includeTags': ['title', 'meta', 'h1', 'h2', 'h3', 'p', 'a', 'img', 'video'],
            'excludeTags': ['script', 'style', 'nav', 'footer'],
            'waitFor': 2000,  # Wait 2 seconds for dynamic content
            'timeout': self.config.timeout_seconds * 1000
        }
        
        request_data['options'].update(default_options)
        
        try:
            response = await self._make_request('POST', '/api/scrape', request_data)
            
            # Validate response structure
            if 'success' not in response:
                raise MCPError("Invalid response format from MCP server")
            
            if not response['success']:
                error_msg = response.get('error', 'Unknown error')
                raise MCPError(f"Scraping failed: {error_msg}")
            
            self.logger.info(f"Successfully scraped URL: {url}")
            return response.get('data', {})
            
        except MCPError:
            raise
        except Exception as e:
            raise MCPError(f"Unexpected error during scraping: {e}")
    
    async def search_web(self, query: str, options: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Search the web for learning resources using MCP tools.
        
        Args:
            query: Search query string
            options: Additional search options
            
        Returns:
            List of search results
            
        Raises:
            MCPError: If search fails
        """
        if not query or not query.strip():
            raise MCPError("Search query cannot be empty")
        
        self.logger.info(f"Searching web for: {query}")
        
        # Prepare request data
        request_data = {
            'query': query.strip(),
            'options': options or {}
        }
        
        # Add default search options optimized for learning content
        default_options = {
            'limit': 10,  # Get more results for ranking
            'searchType': 'web',
            'includeMetadata': True,
            'filters': {
                'contentType': ['educational', 'tutorial', 'documentation'],
                'domains': ['edu', 'org'],  # Prefer educational domains
                'language': 'en'
            }
        }
        
        request_data['options'].update(default_options)
        
        try:
            response = await self._make_request('POST', '/api/search', request_data)
            
            # Validate response structure
            if 'success' not in response:
                raise MCPError("Invalid response format from MCP server")
            
            if not response['success']:
                error_msg = response.get('error', 'Unknown error')
                raise MCPError(f"Search failed: {error_msg}")
            
            results = response.get('data', {}).get('results', [])
            self.logger.info(f"Found {len(results)} search results for query: {query}")
            
            return results
            
        except MCPError:
            raise
        except Exception as e:
            raise MCPError(f"Unexpected error during search: {e}")
    
    async def crawl_site(self, url: str, options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Crawl an entire site or section using MCP tools.
        
        Args:
            url: Base URL to crawl
            options: Additional crawling options
            
        Returns:
            Crawled site data
            
        Raises:
            MCPError: If crawling fails
        """
        if not url or not url.strip():
            raise MCPError("URL cannot be empty")
        
        # Validate URL format
        parsed_url = urlparse(url)
        if not parsed_url.scheme or not parsed_url.netloc:
            raise MCPError(f"Invalid URL format: {url}")
        
        self.logger.info(f"Crawling site: {url}")
        
        # Prepare request data
        request_data = {
            'url': url.strip(),
            'options': options or {}
        }
        
        # Add default crawling options
        default_options = {
            'limit': 50,  # Limit pages to avoid overwhelming
            'maxDepth': 3,
            'allowedDomains': [parsed_url.netloc],
            'excludePatterns': [
                '*/admin/*', '*/login/*', '*/register/*',
                '*.pdf', '*.doc', '*.zip'
            ],
            'includePatterns': [
                '*/tutorial/*', '*/guide/*', '*/learn/*',
                '*/course/*', '*/lesson/*', '*/documentation/*'
            ],
            'respectRobotsTxt': True,
            'delay': 1000,  # 1 second delay between requests
            'timeout': self.config.timeout_seconds * 1000
        }
        
        request_data['options'].update(default_options)
        
        try:
            response = await self._make_request('POST', '/api/crawl', request_data)
            
            # Validate response structure
            if 'success' not in response:
                raise MCPError("Invalid response format from MCP server")
            
            if not response['success']:
                error_msg = response.get('error', 'Unknown error')
                raise MCPError(f"Crawling failed: {error_msg}")
            
            self.logger.info(f"Successfully crawled site: {url}")
            return response.get('data', {})
            
        except MCPError:
            raise
        except Exception as e:
            raise MCPError(f"Unexpected error during crawling: {e}")
    
    async def get_crawl_status(self, job_id: str) -> Dict[str, Any]:
        """Get status of a crawling job.
        
        Args:
            job_id: ID of the crawling job
            
        Returns:
            Job status information
            
        Raises:
            MCPError: If status check fails
        """
        if not job_id or not job_id.strip():
            raise MCPError("Job ID cannot be empty")
        
        try:
            response = await self._make_request('GET', f'/api/crawl/{job_id}')
            
            if 'success' not in response:
                raise MCPError("Invalid response format from MCP server")
            
            if not response['success']:
                error_msg = response.get('error', 'Unknown error')
                raise MCPError(f"Status check failed: {error_msg}")
            
            return response.get('data', {})
            
        except MCPError:
            raise
        except Exception as e:
            raise MCPError(f"Unexpected error checking crawl status: {e}")
    
    async def handle_rate_limits(self) -> None:
        """Handle rate limiting by waiting for reset if necessary."""
        await self.connection_manager.wait_for_rate_limit_reset()
    
    def get_connection_info(self) -> Dict[str, Any]:
        """Get information about the current connection.
        
        Returns:
            Connection information dictionary
        """
        rate_limit_info = self.connection_manager.get_rate_limit_info()
        
        return {
            'server_url': self.config.mcp_server_url,
            'connection_state': self.connection_manager.connection_state.value,
            'is_connected': self.connection_manager.is_connected,
            'rate_limit_info': rate_limit_info.to_dict() if rate_limit_info else None,
            'config': {
                'timeout_seconds': self.config.timeout_seconds,
                'max_retries': self.config.max_retries,
                'rate_limit_per_minute': self.config.rate_limit_per_minute
            }
        }
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.disconnect()