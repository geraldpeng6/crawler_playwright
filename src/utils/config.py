#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Configuration module for the web interaction element crawler.

This module contains the Config class that stores all configuration settings
for the crawler.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Union, Any


@dataclass
class Config:
    """Configuration class for the crawler."""

    # Browser settings
    headless: bool = False
    profile_name: Optional[str] = None

    # Output settings
    output_dir: str = "output"

    # Crawler settings
    similarity_threshold: int = 70  # 0-100
    scroll_count: int = 3
    delay: float = 2.0  # seconds

    # Keywords
    custom_keywords: List[str] = field(default_factory=list)

    # Anti-crawler settings
    random_delay: bool = True  # Add random delay between requests
    min_delay: float = 1.0  # Minimum delay in seconds
    max_delay: float = 5.0  # Maximum delay in seconds

    rotate_user_agent: bool = True  # Rotate user agents
    custom_user_agents: List[str] = field(default_factory=list)  # Custom user agents

    use_referrers: bool = True  # Use HTTP referrers
    custom_referrers: List[str] = field(default_factory=list)  # Custom referrers

    rate_limit: bool = True  # Enable rate limiting
    requests_per_minute: int = 20  # Maximum requests per minute

    use_proxies: bool = False  # Use proxy servers
    proxies: List[str] = field(default_factory=list)  # List of proxy servers

    retry_count: int = 3  # Number of retries on failure
    retry_backoff: float = 2.0  # Exponential backoff factor

    # Browser emulation settings
    emulate_human_behavior: bool = True  # Emulate human-like behavior
    random_scroll: bool = True  # Random scrolling behavior
    mouse_movement: bool = True  # Simulate mouse movements

    # Request headers
    custom_headers: Dict[str, str] = field(default_factory=dict)  # Custom HTTP headers

    # Multi-threading settings
    use_multithreading: bool = False  # Enable multi-threading
    max_threads: int = 4  # Maximum number of threads
    max_domains_per_thread: int = 2  # Maximum number of domains per thread
    domain_specific_settings: Dict[str, Dict[str, Any]] = field(default_factory=dict)  # Domain-specific settings

    # URL processing status settings
    track_processed_urls: bool = True  # Track which URLs have been processed
    process_only_unprocessed: bool = False  # Only process URLs that haven't been processed yet
    processed_status_column: str = "processed"  # Column name for processed status

    def to_dict(self):
        """Convert config to dictionary."""
        return {
            # Browser settings
            "headless": self.headless,
            "profile_name": self.profile_name,

            # Output settings
            "output_dir": self.output_dir,

            # Crawler settings
            "similarity_threshold": self.similarity_threshold,
            "scroll_count": self.scroll_count,
            "delay": self.delay,
            "custom_keywords": self.custom_keywords,

            # Anti-crawler settings
            "random_delay": self.random_delay,
            "min_delay": self.min_delay,
            "max_delay": self.max_delay,
            "rotate_user_agent": self.rotate_user_agent,
            "custom_user_agents": self.custom_user_agents,
            "use_referrers": self.use_referrers,
            "custom_referrers": self.custom_referrers,
            "rate_limit": self.rate_limit,
            "requests_per_minute": self.requests_per_minute,
            "use_proxies": self.use_proxies,
            "proxies": self.proxies,
            "retry_count": self.retry_count,
            "retry_backoff": self.retry_backoff,
            "emulate_human_behavior": self.emulate_human_behavior,
            "random_scroll": self.random_scroll,
            "mouse_movement": self.mouse_movement,
            "custom_headers": self.custom_headers,

            # Multi-threading settings
            "use_multithreading": self.use_multithreading,
            "max_threads": self.max_threads,
            "max_domains_per_thread": self.max_domains_per_thread,
            "domain_specific_settings": self.domain_specific_settings,

            # URL processing status settings
            "track_processed_urls": self.track_processed_urls,
            "process_only_unprocessed": self.process_only_unprocessed,
            "processed_status_column": self.processed_status_column
        }

    @classmethod
    def from_dict(cls, data):
        """Create config from dictionary."""
        return cls(
            # Browser settings
            headless=data.get("headless", False),
            profile_name=data.get("profile_name"),

            # Output settings
            output_dir=data.get("output_dir", "output"),

            # Crawler settings
            similarity_threshold=data.get("similarity_threshold", 70),
            scroll_count=data.get("scroll_count", 3),
            delay=data.get("delay", 2.0),
            custom_keywords=data.get("custom_keywords", []),

            # Anti-crawler settings
            random_delay=data.get("random_delay", True),
            min_delay=data.get("min_delay", 1.0),
            max_delay=data.get("max_delay", 5.0),
            rotate_user_agent=data.get("rotate_user_agent", True),
            custom_user_agents=data.get("custom_user_agents", []),
            use_referrers=data.get("use_referrers", True),
            custom_referrers=data.get("custom_referrers", []),
            rate_limit=data.get("rate_limit", True),
            requests_per_minute=data.get("requests_per_minute", 20),
            use_proxies=data.get("use_proxies", False),
            proxies=data.get("proxies", []),
            retry_count=data.get("retry_count", 3),
            retry_backoff=data.get("retry_backoff", 2.0),
            emulate_human_behavior=data.get("emulate_human_behavior", True),
            random_scroll=data.get("random_scroll", True),
            mouse_movement=data.get("mouse_movement", True),
            custom_headers=data.get("custom_headers", {}),

            # Multi-threading settings
            use_multithreading=data.get("use_multithreading", False),
            max_threads=data.get("max_threads", 4),
            max_domains_per_thread=data.get("max_domains_per_thread", 2),
            domain_specific_settings=data.get("domain_specific_settings", {}),

            # URL processing status settings
            track_processed_urls=data.get("track_processed_urls", True),
            process_only_unprocessed=data.get("process_only_unprocessed", False),
            processed_status_column=data.get("processed_status_column", "processed")
        )
