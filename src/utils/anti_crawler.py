#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Anti-crawler utility module for the web interaction element crawler.

This module provides functions and classes to help avoid detection by anti-bot systems.
"""

import random
import time
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Callable, Any
import math

from src.utils.logger import get_logger

logger = get_logger()

# Common user agents for different browsers and devices
DEFAULT_USER_AGENTS = [
    # Chrome on Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/93.0.4577.63 Safari/537.36",
    
    # Chrome on macOS
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/93.0.4577.63 Safari/537.36",
    
    # Firefox on Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:90.0) Gecko/20100101 Firefox/90.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:91.0) Gecko/20100101 Firefox/91.0",
    
    # Firefox on macOS
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:89.0) Gecko/20100101 Firefox/89.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:90.0) Gecko/20100101 Firefox/90.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:91.0) Gecko/20100101 Firefox/91.0",
    
    # Safari on macOS
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Safari/605.1.15",
    
    # Edge on Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36 Edg/91.0.864.59",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36 Edg/92.0.902.55",
    
    # Mobile browsers
    "Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (iPad; CPU OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Linux; Android 11; SM-G991B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.120 Mobile Safari/537.36",
]

# Common referrers
DEFAULT_REFERRERS = [
    "https://www.google.com/",
    "https://www.google.com/search?q=interaction+elements",
    "https://www.bing.com/",
    "https://www.bing.com/search?q=web+interaction+elements",
    "https://duckduckgo.com/",
    "https://www.yahoo.com/",
    "https://www.baidu.com/",
    "https://www.reddit.com/",
    "https://www.facebook.com/",
    "https://twitter.com/",
    "https://www.linkedin.com/",
    "https://www.instagram.com/",
    "https://www.youtube.com/",
]

class RateLimiter:
    """Rate limiter to control request frequency."""
    
    def __init__(self, requests_per_minute: int = 20):
        """
        Initialize the rate limiter.
        
        Args:
            requests_per_minute: Maximum number of requests per minute
        """
        self.requests_per_minute = requests_per_minute
        self.interval = 60.0 / requests_per_minute  # Time between requests in seconds
        self.last_request_time = datetime.now() - timedelta(seconds=self.interval)
        
    def wait(self) -> None:
        """Wait until it's safe to make the next request."""
        now = datetime.now()
        elapsed = (now - self.last_request_time).total_seconds()
        
        if elapsed < self.interval:
            wait_time = self.interval - elapsed
            logger.debug(f"Rate limiting: waiting {wait_time:.2f} seconds")
            time.sleep(wait_time)
            
        self.last_request_time = datetime.now()

class RetryHandler:
    """Handler for retrying failed requests with exponential backoff."""
    
    def __init__(self, max_retries: int = 3, backoff_factor: float = 2.0):
        """
        Initialize the retry handler.
        
        Args:
            max_retries: Maximum number of retry attempts
            backoff_factor: Exponential backoff factor
        """
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        
    def execute_with_retry(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute a function with retry logic.
        
        Args:
            func: Function to execute
            *args: Positional arguments for the function
            **kwargs: Keyword arguments for the function
            
        Returns:
            Result of the function
            
        Raises:
            Exception: If all retry attempts fail
        """
        last_exception = None
        
        for attempt in range(self.max_retries + 1):
            try:
                if attempt > 0:
                    logger.info(f"Retry attempt {attempt}/{self.max_retries}")
                    
                return func(*args, **kwargs)
                
            except Exception as e:
                last_exception = e
                
                if attempt < self.max_retries:
                    # Calculate backoff time
                    backoff_time = self.backoff_factor ** attempt
                    logger.warning(f"Request failed: {str(e)}. Retrying in {backoff_time:.2f} seconds...")
                    time.sleep(backoff_time)
                else:
                    logger.error(f"All retry attempts failed: {str(e)}")
        
        # If we get here, all retries failed
        raise last_exception

class AntiCrawlerUtils:
    """Utility class for anti-crawler mechanisms."""
    
    @staticmethod
    def get_random_user_agent(custom_agents: List[str] = None) -> str:
        """
        Get a random user agent.
        
        Args:
            custom_agents: List of custom user agents
            
        Returns:
            Random user agent string
        """
        agents = custom_agents if custom_agents else DEFAULT_USER_AGENTS
        return random.choice(agents)
    
    @staticmethod
    def get_random_referrer(custom_referrers: List[str] = None) -> str:
        """
        Get a random referrer.
        
        Args:
            custom_referrers: List of custom referrers
            
        Returns:
            Random referrer URL
        """
        referrers = custom_referrers if custom_referrers else DEFAULT_REFERRERS
        return random.choice(referrers)
    
    @staticmethod
    def get_random_delay(min_delay: float = 1.0, max_delay: float = 5.0) -> float:
        """
        Get a random delay time.
        
        Args:
            min_delay: Minimum delay in seconds
            max_delay: Maximum delay in seconds
            
        Returns:
            Random delay time in seconds
        """
        return random.uniform(min_delay, max_delay)
    
    @staticmethod
    def apply_random_delay(min_delay: float = 1.0, max_delay: float = 5.0) -> None:
        """
        Apply a random delay.
        
        Args:
            min_delay: Minimum delay in seconds
            max_delay: Maximum delay in seconds
        """
        delay = AntiCrawlerUtils.get_random_delay(min_delay, max_delay)
        logger.debug(f"Applying random delay: {delay:.2f} seconds")
        time.sleep(delay)
    
    @staticmethod
    def get_browser_headers(user_agent: str = None, referrer: str = None) -> Dict[str, str]:
        """
        Get browser-like headers.
        
        Args:
            user_agent: User agent string
            referrer: Referrer URL
            
        Returns:
            Dictionary of HTTP headers
        """
        headers = {
            "User-Agent": user_agent or AntiCrawlerUtils.get_random_user_agent(),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Cache-Control": "max-age=0",
        }
        
        if referrer:
            headers["Referer"] = referrer
            
        return headers
    
    @staticmethod
    def simulate_human_behavior(page, config) -> None:
        """
        Simulate human-like behavior on a page.
        
        Args:
            page: Playwright page object
            config: Configuration object
        """
        # Random scrolling
        if config.random_scroll:
            AntiCrawlerUtils.random_scrolling(page)
            
        # Mouse movements
        if config.mouse_movement:
            AntiCrawlerUtils.random_mouse_movement(page)
            
        # Random pauses
        if config.random_delay:
            AntiCrawlerUtils.apply_random_delay(config.min_delay, config.max_delay)
    
    @staticmethod
    def random_scrolling(page) -> None:
        """
        Perform random scrolling on a page.
        
        Args:
            page: Playwright page object
        """
        # Get page height
        page_height = page.evaluate("document.body.scrollHeight")
        viewport_height = page.viewport_size["height"]
        
        # Number of scroll actions (random)
        scroll_count = random.randint(2, 5)
        
        for _ in range(scroll_count):
            # Random scroll position
            scroll_position = random.randint(0, max(1, int(page_height - viewport_height)))
            
            # Scroll to position
            page.evaluate(f"window.scrollTo(0, {scroll_position})")
            
            # Random pause between scrolls
            time.sleep(random.uniform(0.5, 2.0))
    
    @staticmethod
    def random_mouse_movement(page) -> None:
        """
        Perform random mouse movements on a page.
        
        Args:
            page: Playwright page object
        """
        # Get viewport dimensions
        viewport_width = page.viewport_size["width"]
        viewport_height = page.viewport_size["height"]
        
        # Number of mouse movements (random)
        movement_count = random.randint(3, 8)
        
        for _ in range(movement_count):
            # Random coordinates
            x = random.randint(0, viewport_width)
            y = random.randint(0, viewport_height)
            
            # Move mouse
            page.mouse.move(x, y)
            
            # Random pause between movements
            time.sleep(random.uniform(0.1, 0.5))
