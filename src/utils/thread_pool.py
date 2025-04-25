#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Thread pool manager for the web interaction element crawler.

This module provides a thread pool implementation for parallel crawling.
"""

import concurrent.futures
import threading
import queue
import time
from typing import List, Dict, Any, Callable, Optional, Tuple, Set
from dataclasses import dataclass, field

from src.utils.logger import get_logger

logger = get_logger()

@dataclass
class CrawlTask:
    """Class representing a crawl task."""
    url: str
    domain: str = ""
    priority: int = 0
    retry_count: int = 0
    result: Any = None
    error: Optional[Exception] = None

    def __post_init__(self):
        """Extract domain from URL if not provided."""
        if not self.domain:
            from urllib.parse import urlparse
            parsed_url = urlparse(self.url)
            self.domain = parsed_url.netloc

    def __lt__(self, other):
        """
        Less than comparison for priority queue ordering.
        Lower priority number means higher priority.

        Args:
            other: Another CrawlTask to compare with

        Returns:
            True if this task has higher priority than the other
        """
        if not isinstance(other, CrawlTask):
            return NotImplemented
        return self.priority < other.priority

    def __eq__(self, other):
        """
        Equality comparison.

        Args:
            other: Another CrawlTask to compare with

        Returns:
            True if the tasks are equal
        """
        if not isinstance(other, CrawlTask):
            return NotImplemented
        return (self.url == other.url and
                self.domain == other.domain and
                self.priority == other.priority)

class DomainThrottler:
    """Class to throttle requests to the same domain."""

    def __init__(self, requests_per_minute: int = 20):
        """
        Initialize the domain throttler.

        Args:
            requests_per_minute: Maximum number of requests per minute per domain
        """
        self.requests_per_minute = requests_per_minute
        self.interval = 60.0 / max(1, requests_per_minute)  # Time between requests in seconds
        self.domain_last_request = {}  # Domain -> timestamp of last request
        self.lock = threading.Lock()

    def wait_if_needed(self, domain: str) -> float:
        """
        Wait if needed to respect the rate limit for the domain.

        Args:
            domain: Domain to check

        Returns:
            Time waited in seconds
        """
        with self.lock:
            now = time.time()
            last_request = self.domain_last_request.get(domain, 0)
            elapsed = now - last_request

            if elapsed < self.interval:
                wait_time = self.interval - elapsed
                return wait_time

            # Update last request time
            self.domain_last_request[domain] = now
            return 0

    def wait_for_domain(self, domain: str) -> None:
        """
        Wait if needed to respect the rate limit for the domain.

        Args:
            domain: Domain to wait for
        """
        wait_time = self.wait_if_needed(domain)
        if wait_time > 0:
            logger.debug(f"Throttling domain {domain}: waiting {wait_time:.2f} seconds")
            time.sleep(wait_time)

    def update_domain_timestamp(self, domain: str) -> None:
        """
        Update the timestamp for a domain.

        Args:
            domain: Domain to update
        """
        with self.lock:
            self.domain_last_request[domain] = time.time()

class ThreadPoolManager:
    """Thread pool manager for parallel crawling."""

    def __init__(self,
                 max_workers: int = 4,
                 max_domains_per_worker: int = 2,
                 requests_per_minute_per_domain: int = 20):
        """
        Initialize the thread pool manager.

        Args:
            max_workers: Maximum number of worker threads
            max_domains_per_worker: Maximum number of domains per worker
            requests_per_minute_per_domain: Maximum requests per minute per domain
        """
        self.max_workers = max_workers
        self.max_domains_per_worker = max_domains_per_worker
        self.requests_per_minute = requests_per_minute_per_domain

        # Create thread pool
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=max_workers)

        # Create domain throttler
        self.domain_throttler = DomainThrottler(requests_per_minute_per_domain)

        # Task queue and results
        self.task_queue = queue.PriorityQueue()
        self.results = []
        self.active_domains = set()
        self.domain_lock = threading.Lock()

        # Status tracking
        self.running = False
        self.completed_tasks = 0
        self.total_tasks = 0
        self.status_lock = threading.Lock()

    def add_task(self, url: str, domain: str = "") -> None:
        """
        Add a task to the queue.

        Args:
            url: URL to crawl
            domain: Domain of the URL (extracted automatically if not provided)
        """
        task = CrawlTask(url=url, domain=domain)
        with self.status_lock:
            self.total_tasks += 1
        self.task_queue.put(task)
        logger.debug(f"Added task for URL: {url}, domain: {task.domain}")

    def add_tasks(self, urls: List[str]) -> None:
        """
        Add multiple tasks to the queue.

        Args:
            urls: List of URLs to crawl
        """
        for url in urls:
            self.add_task(url)

    def is_domain_available(self, domain: str) -> bool:
        """
        Check if a domain is available for crawling.

        Args:
            domain: Domain to check

        Returns:
            True if the domain is available, False otherwise
        """
        with self.domain_lock:
            # Check if we're already processing too many domains
            if len(self.active_domains) >= self.max_workers * self.max_domains_per_worker:
                # If the domain is already active, it's available
                return domain in self.active_domains

            # Otherwise, we can add a new domain
            return True

    def acquire_domain(self, domain: str) -> bool:
        """
        Acquire a domain for crawling.

        Args:
            domain: Domain to acquire

        Returns:
            True if the domain was acquired, False otherwise
        """
        with self.domain_lock:
            if self.is_domain_available(domain):
                self.active_domains.add(domain)
                return True
            return False

    def release_domain(self, domain: str) -> None:
        """
        Release a domain after crawling.

        Args:
            domain: Domain to release
        """
        with self.domain_lock:
            if domain in self.active_domains:
                self.active_domains.remove(domain)

    def worker(self, process_func: Callable[[str], Any]) -> None:
        """
        Worker function for processing tasks.

        Args:
            process_func: Function to process a URL
        """
        while self.running:
            try:
                # Try to get a task with a short timeout
                try:
                    task = self.task_queue.get(timeout=0.5)
                except queue.Empty:
                    # No tasks available, check if we should continue running
                    continue

                # Check if we can process this domain
                if not self.acquire_domain(task.domain):
                    # Put the task back in the queue with a higher priority
                    task.priority -= 1  # Lower number = higher priority
                    self.task_queue.put(task)
                    continue

                try:
                    # Wait for domain throttling
                    self.domain_throttler.wait_for_domain(task.domain)

                    # Process the task
                    logger.info(f"Processing URL: {task.url}")
                    result = process_func(task.url)

                    # Update domain timestamp
                    self.domain_throttler.update_domain_timestamp(task.domain)

                    # Store the result
                    task.result = result
                    with self.status_lock:
                        self.results.append(task)
                        self.completed_tasks += 1

                except Exception as e:
                    logger.error(f"Error processing URL {task.url}: {str(e)}")
                    task.error = e

                    # Retry if needed
                    if task.retry_count < 3:  # Maximum 3 retries
                        task.retry_count += 1
                        logger.info(f"Retrying URL {task.url} (attempt {task.retry_count})")
                        self.task_queue.put(task)
                    else:
                        # Store the failed task
                        with self.status_lock:
                            self.results.append(task)
                            self.completed_tasks += 1

                finally:
                    # Release the domain
                    self.release_domain(task.domain)

                    # Mark the task as done
                    self.task_queue.task_done()

            except Exception as e:
                logger.error(f"Error in worker thread: {str(e)}")

    def start(self, process_func: Callable[[str], Any]) -> None:
        """
        Start the thread pool.

        Args:
            process_func: Function to process a URL
        """
        if self.running:
            return

        self.running = True

        # Submit worker tasks to the thread pool
        self.futures = []
        for _ in range(self.max_workers):
            future = self.executor.submit(self.worker, process_func)
            self.futures.append(future)

        logger.info(f"Started thread pool with {self.max_workers} workers")

    def stop(self) -> None:
        """Stop the thread pool."""
        if not self.running:
            return

        self.running = False

        # Wait for all tasks to complete
        for future in self.futures:
            future.result()

        logger.info("Stopped thread pool")

    def wait_completion(self) -> None:
        """Wait for all tasks to complete."""
        self.task_queue.join()

    def get_results(self) -> List[CrawlTask]:
        """
        Get the results of all completed tasks.

        Returns:
            List of completed tasks
        """
        return self.results

    def get_progress(self) -> Tuple[int, int]:
        """
        Get the current progress.

        Returns:
            Tuple of (completed_tasks, total_tasks)
        """
        with self.status_lock:
            return (self.completed_tasks, self.total_tasks)

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.stop()
        self.executor.shutdown()
