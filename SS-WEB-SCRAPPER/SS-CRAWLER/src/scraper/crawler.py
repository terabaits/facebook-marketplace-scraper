"""HTTP crawler with error classification and retry logic."""
import random
import time
from dataclasses import dataclass
from enum import Enum
from typing import Optional, List
from pathlib import Path
from datetime import datetime

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry as urllibRetry

from src.utils.config import ScraperConfig
from src.utils.logger import get_logger

logger = get_logger("crawler")


class ErrorType(Enum):
    """Classification of request errors."""
    SUCCESS = "success"
    RETRYABLE = "retryable"      # 5xx, timeout, connection reset
    NOT_FOUND = "not_found"      # 404 - listing deleted
    BLOCKED = "blocked"          # 403 - IP blocked, stop immediately
    RATE_LIMIT = "rate_limit"    # 429 - back off
    PARSE_ERROR = "parse_error"  # HTML structure changed
    NETWORK_ERROR = "network"    # DNS, connection refused


@dataclass
class FetchResult:
    """Result of a fetch operation."""
    url: str
    status_code: int
    html: Optional[str]
    error_type: ErrorType
    error_msg: Optional[str]
    attempts: int
    duration_ms: float


class Crawler:
    """
    HTTP crawler with intelligent retry and rate limiting.
    """
    
    BASE_URL = "https://www.ss.com"
    
    def __init__(self, config: ScraperConfig):
        self.config = config
        self.session = requests.Session()
        
        # Configure retry for network-level issues
        retry_strategy = urllibRetry(
            total=config.retry_attempts,
            backoff_factor=1,
            status_forcelist=tuple(config.retryable_status),
            allowed_methods=["GET"]
        )
        
        adapter = HTTPAdapter(
            max_retries=retry_strategy,
            pool_connections=10,
            pool_maxsize=10
        )
        
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        # Ensure HTML samples directory exists
        if config.save_html_samples:
            Path(config.html_samples_dir).mkdir(parents=True, exist_ok=True)
    
    def _get_headers(self) -> dict:
        """Generate random headers."""
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        ]
        
        return {
            "User-Agent": random.choice(user_agents),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "lv,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1"
        }
    
    def _throttle(self):
        """Random delay between requests."""
        delay = random.uniform(self.config.throttle_min, self.config.throttle_max)
        time.sleep(delay)
    
    def _classify_error(self, status_code: int, exception: Optional[Exception]) -> ErrorType:
        """Classify error based on status code and exception."""
        if status_code == 200:
            return ErrorType.SUCCESS
        
        if status_code == 404:
            return ErrorType.NOT_FOUND
        elif status_code == 403:
            return ErrorType.BLOCKED
        elif status_code == 429:
            return ErrorType.RATE_LIMIT
        elif status_code >= 500:
            return ErrorType.RETRYABLE
        elif exception:
            if isinstance(exception, requests.exceptions.Timeout):
                return ErrorType.RETRYABLE
            elif isinstance(exception, requests.exceptions.ConnectionError):
                return ErrorType.NETWORK_ERROR
        
        return ErrorType.RETRYABLE
    
    def fetch(self, url: str, context: str = "") -> FetchResult:
        """
        Fetch URL with retry logic and error classification.
        
        Args:
            url: URL to fetch
            context: Description of what we're fetching (for logging)
        
        Returns:
            FetchResult with HTML or error info
        """
        start_time = time.time()
        full_url = url if url.startswith("http") else f"{self.BASE_URL}{url}"
        
        logger.info(f"Fetching {context}: {full_url}")
        
        for attempt in range(1, self.config.retry_attempts + 1):
            try:
                response = self.session.get(
                    full_url,
                    headers=self._get_headers(),
                    timeout=self.config.request_timeout
                )
                
                error_type = self._classify_error(response.status_code, None)
                duration = (time.time() - start_time) * 1000
                
                if error_type == ErrorType.SUCCESS:
                    logger.debug(f"✓ Success in {duration:.0f}ms (attempt {attempt})")
                    self._throttle()
                    return FetchResult(
                        url=full_url,
                        status_code=response.status_code,
                        html=response.text,
                        error_type=error_type,
                        error_msg=None,
                        attempts=attempt,
                        duration_ms=duration
                    )
                
                elif error_type == ErrorType.BLOCKED:
                    logger.critical(f"🚫 BLOCKED after {attempt} attempts! Stopping scraper.")
                    return FetchResult(
                        url=full_url,
                        status_code=response.status_code,
                        html=None,
                        error_type=error_type,
                        error_msg=f"Access blocked (403)",
                        attempts=attempt,
                        duration_ms=duration
                    )
                
                elif error_type == ErrorType.NOT_FOUND:
                    logger.warning(f"✗ 404 Not Found: {full_url}")
                    return FetchResult(
                        url=full_url,
                        status_code=response.status_code,
                        html=None,
                        error_type=error_type,
                        error_msg="Listing not found (deleted)",
                        attempts=attempt,
                        duration_ms=duration
                    )
                
                elif error_type == ErrorType.RETRYABLE:
                    if attempt < self.config.retry_attempts:
                        delay = self.config.retry_delays[min(attempt-1, len(self.config.retry_delays)-1)]
                        logger.warning(f"⚠ Retryable error {response.status_code}, waiting {delay}s...")
                        time.sleep(delay)
                        continue
                    else:
                        logger.error(f"✗ Max retries exceeded for {full_url}")
                        return FetchResult(
                            url=full_url,
                            status_code=response.status_code,
                            html=None,
                            error_type=error_type,
                            error_msg=f"Max retries exceeded, last status: {response.status_code}",
                            attempts=attempt,
                            duration_ms=duration
                        )
                
            except requests.exceptions.RequestException as e:
                error_type = self._classify_error(0, e)
                duration = (time.time() - start_time) * 1000
                
                if attempt < self.config.retry_attempts:
                    delay = self.config.retry_delays[min(attempt-1, len(self.config.retry_delays)-1)]
                    logger.warning(f"⚠ Network error (attempt {attempt}): {type(e).__name__}, retrying in {delay}s...")
                    time.sleep(delay)
                    continue
                else:
                    logger.error(f"✗ Network failed after {attempt} attempts: {e}")
                    return FetchResult(
                        url=full_url,
                        status_code=0,
                        html=None,
                        error_type=error_type,
                        error_msg=str(e),
                        attempts=attempt,
                        duration_ms=duration
                    )
        
        # Should never reach here
        return FetchResult(
            url=full_url,
            status_code=0,
            html=None,
            error_type=ErrorType.RETRYABLE,
            error_msg="Unexpected exit from retry loop",
            attempts=self.config.retry_attempts,
            duration_ms=(time.time() - start_time) * 1000
        )
    
    def save_html_sample(self, html: str, prefix: str = "debug") -> str:
        """Save HTML sample for debugging. Returns file path."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{prefix}_{timestamp}.html"
        filepath = Path(self.config.html_samples_dir) / filename
        
        filepath.write_text(html, encoding='utf-8')
        logger.info(f"HTML sample saved: {filepath}")
        return str(filepath)
