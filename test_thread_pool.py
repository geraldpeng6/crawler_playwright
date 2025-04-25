#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script for the ThreadPoolManager class.
"""

import time
from src.utils.thread_pool import ThreadPoolManager, CrawlTask

def test_crawl_task_comparison():
    """Test CrawlTask comparison methods."""
    task1 = CrawlTask(url="https://example.com/1", priority=1)
    task2 = CrawlTask(url="https://example.com/2", priority=2)
    task3 = CrawlTask(url="https://example.com/1", priority=1)
    
    # Test __lt__
    print(f"task1 < task2: {task1 < task2}")  # Should be True (lower priority number = higher priority)
    print(f"task2 < task1: {task2 < task1}")  # Should be False
    
    # Test __eq__
    print(f"task1 == task3: {task1 == task3}")  # Should be True
    print(f"task1 == task2: {task1 == task2}")  # Should be False

def test_thread_pool():
    """Test ThreadPoolManager."""
    # Create thread pool
    pool = ThreadPoolManager(max_workers=2, max_domains_per_worker=1)
    
    # Define a simple process function
    def process_url(url):
        print(f"Processing URL: {url}")
        time.sleep(1)  # Simulate work
        return {"url": url, "status": "success"}
    
    # Add tasks
    urls = [
        "https://example.com/1",
        "https://example.com/2",
        "https://example2.com/1",
        "https://example2.com/2"
    ]
    
    for url in urls:
        pool.add_task(url)
    
    # Start the thread pool
    pool.start(process_url)
    
    # Wait for completion
    pool.wait_completion()
    
    # Get results
    results = pool.get_results()
    print(f"Completed {len(results)} tasks")
    
    # Stop the thread pool
    pool.stop()

if __name__ == "__main__":
    print("Testing CrawlTask comparison methods:")
    test_crawl_task_comparison()
    
    print("\nTesting ThreadPoolManager:")
    test_thread_pool()
