#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Core crawler module for detecting and interacting with web elements.

This module contains the main crawler class that handles browser automation,
element detection, and interaction.
"""

import json
import os
import time
import random
import threading
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

import pandas as pd
from playwright.sync_api import sync_playwright, Page, Browser, BrowserContext

from src.utils.config import Config
from src.utils.logger import get_logger
from src.utils.anti_crawler import AntiCrawlerUtils, RateLimiter, RetryHandler
from src.utils.thread_pool import ThreadPoolManager

logger = get_logger()

class InteractionCrawler:
    """Main crawler class for detecting and interacting with web elements."""

    # Default keywords for interaction elements
    DEFAULT_KEYWORDS = [
        "like", "vote", "upvote", "downvote", "favorite", "follow",
        "subscribe", "share", "comment", "reply", "react", "agree",
        "disagree", "thumbs up", "thumbs down", "heart", "star",
        "点赞", "投票", "关注", "分享", "评论", "回复", "订阅"
    ]

    def __init__(self, config: Config):
        """
        Initialize the crawler with configuration.

        Args:
            config: Configuration object containing crawler settings
        """
        self.config = config
        self.playwright = None
        self.browser = None
        self.context = None
        self.custom_keywords = []
        self.results = []

        # Initialize anti-crawler utilities
        self.rate_limiter = RateLimiter(config.requests_per_minute) if config.rate_limit else None
        self.retry_handler = RetryHandler(config.retry_count, config.retry_backoff)

        # Ensure output directory exists
        os.makedirs(self.config.output_dir, exist_ok=True)

        # Ensure profiles directory exists
        os.makedirs("profiles", exist_ok=True)

    def __enter__(self):
        """Context manager entry point."""
        self.start_browser()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit point."""
        self.close_browser()

    def start_browser(self) -> None:
        """Initialize and start the browser."""
        logger.info("Starting browser")
        self.playwright = sync_playwright().start()

        # Get user agent if rotation is enabled
        user_agent = None
        if self.config.rotate_user_agent:
            user_agent = AntiCrawlerUtils.get_random_user_agent(self.config.custom_user_agents)
            logger.debug(f"Using user agent: {user_agent}")

        # Prepare browser arguments
        browser_args = {
            "headless": self.config.headless
        }

        # Prepare context options
        context_options = {
            "viewport": {"width": 1280, "height": 800}
        }

        # Add user agent if specified
        if user_agent:
            context_options["user_agent"] = user_agent

        # Add custom headers if specified
        if self.config.custom_headers:
            context_options["extra_http_headers"] = self.config.custom_headers

        # Add proxy if enabled and available
        if self.config.use_proxies and self.config.proxies:
            # Use the first proxy in the list
            proxy_url = self.config.proxies[0]
            logger.info(f"Using proxy: {proxy_url}")
            context_options["proxy"] = {
                "server": proxy_url
            }

        # Use browser profile if specified
        if self.config.profile_name:
            profile_path = os.path.join("profiles", self.config.profile_name)
            if os.path.exists(profile_path):
                logger.info(f"Using browser profile: {self.config.profile_name}")

                # Merge options for persistent context
                persistent_options = {
                    "user_data_dir": profile_path,
                    "headless": self.config.headless,
                    **context_options
                }

                # Create a persistent context directly
                self.context = self.playwright.chromium.launch_persistent_context(**persistent_options)

                # In this approach, we don't need a separate browser object
                self.browser = None
            else:
                logger.warning(f"Profile {self.config.profile_name} not found, using default")
                # Launch browser without profile
                self.browser = self.playwright.chromium.launch(**browser_args)
                # Create a new browser context
                self.context = self.browser.new_context(**context_options)
        else:
            # Launch browser without profile
            self.browser = self.playwright.chromium.launch(**browser_args)
            # Create a new browser context
            self.context = self.browser.new_context(**context_options)

    def close_browser(self) -> None:
        """Close the browser and playwright."""
        # Close context first (this is important for persistent contexts)
        if self.context:
            self.context.close()

        # Close browser if it exists (may be None when using persistent context)
        if self.browser:
            self.browser.close()

        # Stop playwright
        if self.playwright:
            self.playwright.stop()

        # Reset all objects
        self.context = None
        self.browser = None
        self.playwright = None
        logger.info("Browser closed")

    def set_custom_keywords(self, keywords: List[str]) -> None:
        """
        Set custom keywords for element detection.

        Args:
            keywords: List of custom keywords
        """
        self.custom_keywords = keywords
        logger.info(f"Set {len(keywords)} custom keywords")

    def get_all_keywords(self) -> List[str]:
        """
        Get all keywords (default + custom).

        Returns:
            Combined list of default and custom keywords
        """
        return self.DEFAULT_KEYWORDS + self.custom_keywords

    def crawl_from_csv(self, csv_path: str) -> List[Dict[str, Any]]:
        """
        Crawl URLs from a CSV file.

        Args:
            csv_path: Path to CSV file containing URLs

        Returns:
            List of results for each URL
        """
        try:
            # Read CSV file
            df = pd.read_csv(csv_path)

            # Find URL column
            url_column = None
            for col in df.columns:
                if col.lower() == 'url':
                    url_column = col
                    break

            if not url_column:
                # Try to find a column that contains URLs
                for col in df.columns:
                    if df[col].dtype == 'object' and df[col].str.contains('http').any():
                        url_column = col
                        break

            if not url_column:
                logger.error("No URL column found in CSV file")
                return []

            # Extract URLs
            urls = df[url_column].tolist()
            logger.info(f"Found {len(urls)} URLs in CSV file")

            # Check if we should use multi-threading
            if self.config.use_multithreading and len(urls) > 1:
                return self.crawl_urls_multithreaded(urls)
            else:
                return self.crawl_urls_sequential(urls)

        except Exception as e:
            logger.error(f"Error processing CSV file: {e}")
            return []

    def crawl_urls_sequential(self, urls: List[str]) -> List[Dict[str, Any]]:
        """
        Crawl URLs sequentially (single-threaded).

        Args:
            urls: List of URLs to crawl

        Returns:
            List of results for each URL
        """
        try:
            # Start browser if not already started
            if not self.context:
                self.start_browser()

            # Process each URL
            self.results = []
            for i, url in enumerate(urls):
                logger.info(f"Processing URL {i+1}/{len(urls)}: {url}")

                # Apply rate limiting if enabled
                if self.rate_limiter:
                    self.rate_limiter.wait()

                try:
                    # Use retry handler for crawling
                    if self.config.retry_count > 0:
                        result = self.retry_handler.execute_with_retry(self.crawl_url, url)
                    else:
                        result = self.crawl_url(url)

                    self.results.append(result)
                except Exception as e:
                    logger.error(f"Error processing URL {url}: {e}")

                # Add delay between URLs
                if i < len(urls) - 1:
                    if self.config.random_delay:
                        # Use random delay
                        AntiCrawlerUtils.apply_random_delay(
                            self.config.min_delay,
                            self.config.max_delay
                        )
                    else:
                        # Use fixed delay
                        time.sleep(self.config.delay)

            return self.results

        except Exception as e:
            logger.error(f"Error processing URLs sequentially: {e}")
            return []
        finally:
            self.close_browser()

    def crawl_urls_multithreaded(self, urls: List[str]) -> List[Dict[str, Any]]:
        """
        Crawl URLs in parallel using multiple threads.

        Args:
            urls: List of URLs to crawl

        Returns:
            List of results for each URL
        """
        logger.info(f"Starting multi-threaded crawling with {self.config.max_threads} threads")

        # Store results
        results = []

        # Create a lock for thread safety when appending to results
        results_lock = threading.Lock()

        # Create a simple thread-safe counter for progress tracking
        completed_count = 0
        total_count = len(urls)
        counter_lock = threading.Lock()

        # Define the worker function that will be executed in each thread
        def worker_func(url):
            # Create a new config object for this thread
            thread_config = Config()
            thread_config.__dict__.update(self.config.__dict__)

            # Create a result dictionary
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            result = {
                "url": url,
                "timestamp": timestamp,
                "elements": [],
                "elements_count": 0
            }

            try:
                logger.info(f"Thread starting browser for URL: {url}")

                # Use a context manager to ensure proper cleanup
                with sync_playwright() as playwright:
                    # Get user agent if rotation is enabled
                    user_agent = None
                    if thread_config.rotate_user_agent:
                        user_agent = AntiCrawlerUtils.get_random_user_agent(thread_config.custom_user_agents)
                        logger.debug(f"Thread using user agent: {user_agent}")

                    # Prepare browser arguments
                    browser_args = {
                        "headless": thread_config.headless
                    }

                    # Prepare context options
                    context_options = {
                        "viewport": {"width": 1280, "height": 800}
                    }

                    # Add user agent if specified
                    if user_agent:
                        context_options["user_agent"] = user_agent

                    # Add proxy if enabled and available
                    if thread_config.use_proxies and thread_config.proxies:
                        # Use the first proxy in the list
                        proxy_url = thread_config.proxies[0]
                        logger.info(f"Thread using proxy: {proxy_url}")
                        context_options["proxy"] = {
                            "server": proxy_url
                        }

                    # Launch browser
                    browser = playwright.chromium.launch(**browser_args)

                    # Create context
                    context = browser.new_context(**context_options)

                    # Create a page
                    page = context.new_page()

                    # Set referrer if enabled
                    if thread_config.use_referrers:
                        referrer = AntiCrawlerUtils.get_random_referrer(thread_config.custom_referrers)
                        logger.debug(f"Thread using referrer: {referrer}")
                        page.set_extra_http_headers({"Referer": referrer})

                    # Navigate to URL
                    logger.info(f"Thread navigating to {url}")

                    # Use a more robust navigation approach
                    try:
                        response = page.goto(
                            url,
                            wait_until="networkidle",
                            timeout=60000
                        )

                        # Check for anti-crawler response
                        if response and response.status >= 400:
                            status = response.status
                            status_text = response.status_text
                            logger.warning(f"Received error response: {status} {status_text}")

                            # Check for common anti-crawler status codes
                            if status in [403, 429, 503]:
                                logger.warning("Possible anti-crawler protection detected")
                    except Exception as e:
                        logger.error(f"Navigation error: {e}")
                        raise

                    # Simulate human behavior if enabled
                    if thread_config.emulate_human_behavior:
                        AntiCrawlerUtils.simulate_human_behavior(page, thread_config)

                    # Scroll page to load lazy elements
                    if thread_config.random_scroll:
                        AntiCrawlerUtils.random_scrolling(page)
                    else:
                        # Simple scroll implementation for thread
                        page_height = page.evaluate("document.body.scrollHeight")
                        viewport_height = page.viewport_size["height"]

                        for i in range(thread_config.scroll_count):
                            current_position = i * viewport_height
                            if current_position >= page_height:
                                break

                            page.evaluate(f"window.scrollTo(0, {current_position})")
                            time.sleep(1)  # Wait for content to load

                        # Scroll back to top
                        page.evaluate("window.scrollTo(0, 0)")

                    # Find interaction elements (simplified for thread)
                    elements = []
                    keywords = self.get_all_keywords()

                    # Find elements by text content
                    for keyword in keywords:
                        try:
                            # Use XPath to find elements containing the keyword
                            elements_locator = page.locator(f"//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{keyword.lower()}')]")
                            count = elements_locator.count()

                            for i in range(count):
                                try:
                                    element = elements_locator.nth(i)
                                    tag_name = element.evaluate("el => el.tagName.toLowerCase()")
                                    text = element.inner_text().strip()

                                    # Skip if text is too long (likely not a button or interaction element)
                                    if len(text) > 50:
                                        continue

                                    # Get element attributes
                                    class_name = element.evaluate("el => el.className") or ""
                                    id_value = element.evaluate("el => el.id") or ""

                                    # Add element to results
                                    element_info = {
                                        "element_text": text,
                                        "element_tag": tag_name,
                                        "element_class": class_name,
                                        "element_id": id_value,
                                        "match_type": "keyword_match",
                                        "match_keyword": keyword
                                    }

                                    elements.append(element_info)
                                except Exception as e:
                                    logger.warning(f"Error processing element: {e}")
                        except Exception as e:
                            logger.warning(f"Error finding elements for keyword {keyword}: {e}")

                    # Take screenshot
                    screenshot_path = os.path.join(
                        thread_config.output_dir,
                        f"{self._sanitize_filename(url)}_{timestamp}.png"
                    )
                    page.screenshot(path=screenshot_path, full_page=True)
                    logger.info(f"Thread screenshot saved to {screenshot_path}")

                    # Update result
                    result["elements"] = elements
                    result["elements_count"] = len(elements)

                    # Save JSON result
                    json_path = os.path.join(
                        thread_config.output_dir,
                        f"{self._sanitize_filename(url)}_{timestamp}.json"
                    )
                    with open(json_path, 'w', encoding='utf-8') as f:
                        json.dump(result, f, ensure_ascii=False, indent=2)
                    logger.info(f"Thread results saved to {json_path}")

                    # Close page, context, and browser
                    page.close()
                    context.close()
                    browser.close()

                    # Add result to results list
                    with results_lock:
                        results.append(result)

                    # Update progress
                    with counter_lock:
                        # Increment the completed count
                        completed_count = len(results)
                        logger.info(f"Progress: {completed_count}/{total_count} URLs processed")

                    return result
            except Exception as e:
                logger.error(f"Error in worker thread for URL {url}: {e}")

                # Add error information to result
                result["error"] = str(e)

                # Add result to results list even if there was an error
                with results_lock:
                    results.append(result)

                # Update progress
                with counter_lock:
                    # Increment the completed count
                    completed_count = len(results)
                    logger.info(f"Progress: {completed_count}/{total_count} URLs processed")

                return result

        try:
            # Create and start threads
            threads = []
            for url in urls:
                thread = threading.Thread(target=worker_func, args=(url,))
                thread.daemon = True  # Make thread a daemon so it exits when main thread exits
                threads.append(thread)
                thread.start()

                # Add a small delay between thread starts to avoid overwhelming the system
                time.sleep(0.5)

                # Limit the number of concurrent threads
                while sum(1 for t in threads if t.is_alive()) >= self.config.max_threads:
                    time.sleep(0.1)

            # Wait for all threads to complete
            for thread in threads:
                thread.join()

            logger.info(f"Multi-threaded crawling completed. Processed {len(results)} URLs.")

            return results

        except Exception as e:
            logger.error(f"Error in multi-threaded crawling: {e}")
            return results  # Return any results we have so far

    def crawl_url(self, url: str) -> Dict[str, Any]:
        """
        Crawl a single URL to find interaction elements.

        Args:
            url: URL to crawl

        Returns:
            Dictionary containing crawl results
        """
        # Set up page with anti-crawler measures
        page = self.context.new_page()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        result = {
            "url": url,
            "timestamp": timestamp,
            "elements": [],
            "elements_count": 0
        }

        try:
            # Set referrer if enabled
            if self.config.use_referrers:
                referrer = AntiCrawlerUtils.get_random_referrer(self.config.custom_referrers)
                logger.debug(f"Using referrer: {referrer}")

                # Add referrer to extra headers
                page.set_extra_http_headers({"Referer": referrer})

            # Navigate to URL with error handling
            logger.info(f"Navigating to {url}")

            # Use a more robust navigation approach
            try:
                response = page.goto(
                    url,
                    wait_until="networkidle",
                    timeout=60000
                )

                # Check for anti-crawler response
                if response and response.status >= 400:
                    status = response.status
                    status_text = response.status_text
                    logger.warning(f"Received error response: {status} {status_text}")

                    # Check for common anti-crawler status codes
                    if status in [403, 429, 503]:
                        logger.warning("Possible anti-crawler protection detected")

                        # Try to get response body for more information
                        try:
                            body = response.text()
                            if "captcha" in body.lower() or "robot" in body.lower() or "blocked" in body.lower():
                                logger.warning("Anti-bot protection confirmed in response body")
                        except:
                            pass
            except Exception as e:
                logger.error(f"Navigation error: {e}")
                raise

            # Simulate human behavior if enabled
            if self.config.emulate_human_behavior:
                AntiCrawlerUtils.simulate_human_behavior(page, self.config)

            # Scroll page to load lazy elements
            if self.config.random_scroll:
                AntiCrawlerUtils.random_scrolling(page)
            else:
                self._scroll_page(page)

            # Find interaction elements
            elements = self._find_interaction_elements(page)

            # Take screenshot
            screenshot_path = os.path.join(
                self.config.output_dir,
                f"{self._sanitize_filename(url)}_{timestamp}.png"
            )
            page.screenshot(path=screenshot_path, full_page=True)
            logger.info(f"Screenshot saved to {screenshot_path}")

            # Save results
            result["elements"] = elements
            result["elements_count"] = len(elements)

            # Save JSON result
            json_path = os.path.join(
                self.config.output_dir,
                f"{self._sanitize_filename(url)}_{timestamp}.json"
            )
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            logger.info(f"Results saved to {json_path}")

            return result

        except Exception as e:
            logger.error(f"Error crawling URL {url}: {e}")
            return result
        finally:
            page.close()

    def _crawl_with_page(self, url: str, page: Page) -> Dict[str, Any]:
        """
        Crawl a single URL using an existing page object.
        This method is used by the multi-threaded crawler.

        Args:
            url: URL to crawl
            page: Playwright page object

        Returns:
            Dictionary containing crawl results
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        result = {
            "url": url,
            "timestamp": timestamp,
            "elements": [],
            "elements_count": 0
        }

        try:
            # Navigate to URL with error handling
            logger.info(f"Thread navigating to {url}")

            # Use a more robust navigation approach
            try:
                response = page.goto(
                    url,
                    wait_until="networkidle",
                    timeout=60000
                )

                # Check for anti-crawler response
                if response and response.status >= 400:
                    status = response.status
                    status_text = response.status_text
                    logger.warning(f"Received error response: {status} {status_text}")

                    # Check for common anti-crawler status codes
                    if status in [403, 429, 503]:
                        logger.warning("Possible anti-crawler protection detected")

                        # Try to get response body for more information
                        try:
                            body = response.text()
                            if "captcha" in body.lower() or "robot" in body.lower() or "blocked" in body.lower():
                                logger.warning("Anti-bot protection confirmed in response body")
                        except:
                            pass
            except Exception as e:
                logger.error(f"Navigation error: {e}")
                raise

            # Simulate human behavior if enabled
            if self.config.emulate_human_behavior:
                AntiCrawlerUtils.simulate_human_behavior(page, self.config)

            # Scroll page to load lazy elements
            if self.config.random_scroll:
                AntiCrawlerUtils.random_scrolling(page)
            else:
                self._scroll_page(page)

            # Find interaction elements
            elements = self._find_interaction_elements(page)

            # Take screenshot
            screenshot_path = os.path.join(
                self.config.output_dir,
                f"{self._sanitize_filename(url)}_{timestamp}.png"
            )
            page.screenshot(path=screenshot_path, full_page=True)
            logger.info(f"Thread screenshot saved to {screenshot_path}")

            # Save results
            result["elements"] = elements
            result["elements_count"] = len(elements)

            # Save JSON result
            json_path = os.path.join(
                self.config.output_dir,
                f"{self._sanitize_filename(url)}_{timestamp}.json"
            )
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            logger.info(f"Thread results saved to {json_path}")

            return result

        except Exception as e:
            logger.error(f"Error in thread crawling URL {url}: {e}")
            return result

    def _scroll_page(self, page: Page) -> None:
        """
        Scroll the page to load lazy elements.

        Args:
            page: Playwright page object
        """
        page_height = page.evaluate("document.body.scrollHeight")
        viewport_height = page.viewport_size["height"]

        for i in range(self.config.scroll_count):
            current_position = i * viewport_height
            if current_position >= page_height:
                break

            page.evaluate(f"window.scrollTo(0, {current_position})")
            time.sleep(1)  # Wait for content to load

        # Scroll back to top
        page.evaluate("window.scrollTo(0, 0)")

    def _find_interaction_elements(self, page: Page) -> List[Dict[str, Any]]:
        """
        Find interaction elements on the page.

        Args:
            page: Playwright page object

        Returns:
            List of dictionaries containing element information
        """
        elements_info = []
        keywords = self.get_all_keywords()

        # Find elements by text content
        for keyword in keywords:
            # Use XPath to find elements containing the keyword
            elements = page.locator(f"//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{keyword.lower()}')]")
            count = elements.count()

            for i in range(count):
                element = elements.nth(i)
                try:
                    # Get element information
                    tag_name = element.evaluate("el => el.tagName.toLowerCase()")
                    text = element.inner_text().strip()

                    # Skip if text is too long (likely not a button or interaction element)
                    if len(text) > 50:
                        continue

                    # Get element attributes
                    class_name = element.evaluate("el => el.className") or ""
                    id_value = element.evaluate("el => el.id") or ""

                    # Get XPath
                    xpath = element.evaluate("""el => {
                        const getXPath = function(element) {
                            if (element.id !== '') return `//*[@id="${element.id}"]`;
                            if (element === document.body) return '/html/body';

                            let ix = 0;
                            const siblings = element.parentNode.childNodes;

                            for (let i = 0; i < siblings.length; i++) {
                                const sibling = siblings[i];
                                if (sibling === element) return getXPath(element.parentNode) + '/' + element.tagName.toLowerCase() + '[' + (ix + 1) + ']';
                                if (sibling.nodeType === 1 && sibling.tagName === element.tagName) ix++;
                            }
                        };
                        return getXPath(el);
                    }""")

                    # Add element to results
                    element_info = {
                        "element_text": text,
                        "element_tag": tag_name,
                        "element_class": class_name,
                        "element_id": id_value,
                        "element_xpath": xpath,
                        "match_type": "keyword_match",
                        "match_keyword": keyword
                    }

                    # Check if element is already in results (avoid duplicates)
                    if not any(e["element_xpath"] == xpath for e in elements_info):
                        elements_info.append(element_info)

                except Exception as e:
                    logger.warning(f"Error processing element: {e}")

        # Find elements by attribute values (class, id, name)
        for keyword in keywords:
            # Use CSS selectors to find elements with keyword in attributes
            selectors = [
                f"[class*='{keyword}' i]",
                f"[id*='{keyword}' i]",
                f"[name*='{keyword}' i]",
                f"[aria-label*='{keyword}' i]"
            ]

            for selector in selectors:
                elements = page.locator(selector)
                count = elements.count()

                for i in range(count):
                    element = elements.nth(i)
                    try:
                        # Get element information
                        tag_name = element.evaluate("el => el.tagName.toLowerCase()")
                        text = element.inner_text().strip()

                        # Get element attributes
                        class_name = element.evaluate("el => el.className") or ""
                        id_value = element.evaluate("el => el.id") or ""

                        # Get XPath
                        xpath = element.evaluate("""el => {
                            const getXPath = function(element) {
                                if (element.id !== '') return `//*[@id="${element.id}"]`;
                                if (element === document.body) return '/html/body';

                                let ix = 0;
                                const siblings = element.parentNode.childNodes;

                                for (let i = 0; i < siblings.length; i++) {
                                    const sibling = siblings[i];
                                    if (sibling === element) return getXPath(element.parentNode) + '/' + element.tagName.toLowerCase() + '[' + (ix + 1) + ']';
                                    if (sibling.nodeType === 1 && sibling.tagName === element.tagName) ix++;
                                }
                            };
                            return getXPath(el);
                        }""")

                        # Add element to results
                        element_info = {
                            "element_text": text,
                            "element_tag": tag_name,
                            "element_class": class_name,
                            "element_id": id_value,
                            "element_xpath": xpath,
                            "match_type": "attribute_match",
                            "match_keyword": keyword
                        }

                        # Check if element is already in results (avoid duplicates)
                        if not any(e["element_xpath"] == xpath for e in elements_info):
                            elements_info.append(element_info)

                    except Exception as e:
                        logger.warning(f"Error processing element: {e}")

        return elements_info

    def _sanitize_filename(self, url: str) -> str:
        """
        Sanitize URL to use as filename.

        Args:
            url: URL to sanitize

        Returns:
            Sanitized filename
        """
        # Remove protocol and www
        filename = url.replace("http://", "").replace("https://", "").replace("www.", "")

        # Replace invalid characters
        invalid_chars = ['<', '>', ':', '"', '/', '\\', '|', '?', '*']
        for char in invalid_chars:
            filename = filename.replace(char, '_')

        # Limit length
        if len(filename) > 100:
            filename = filename[:100]

        return filename

    def create_profile(self, profile_name: str) -> str:
        """
        Create a new browser profile.

        Args:
            profile_name: Name of the profile to create

        Returns:
            Path to the created profile
        """
        profile_path = os.path.join("profiles", profile_name)

        # Create profile directory
        os.makedirs(profile_path, exist_ok=True)

        # Close existing browser if open
        self.close_browser()

        # Start browser with profile - using persistent context directly
        self.playwright = sync_playwright().start()

        # Get user agent if rotation is enabled
        user_agent = None
        if self.config.rotate_user_agent:
            user_agent = AntiCrawlerUtils.get_random_user_agent(self.config.custom_user_agents)
            logger.debug(f"Using user agent for profile: {user_agent}")

        # Prepare context options
        context_options = {
            "user_data_dir": profile_path,
            "headless": False,  # Always use headed mode for profile creation
            "viewport": {"width": 1280, "height": 800}
        }

        # Add user agent if specified
        if user_agent:
            context_options["user_agent"] = user_agent

        # Add proxy if enabled and available
        if self.config.use_proxies and self.config.proxies:
            # Use the first proxy in the list
            proxy_url = self.config.proxies[0]
            logger.info(f"Using proxy for profile: {proxy_url}")
            context_options["proxy"] = {
                "server": proxy_url
            }

        # Create a persistent context directly (without creating a browser first)
        self.context = self.playwright.chromium.launch_persistent_context(**context_options)

        # In this approach, we don't need a separate browser object
        self.browser = None

        # Open a blank page
        page = self.context.new_page()

        # Set a common referrer
        if self.config.use_referrers:
            page.set_extra_http_headers({"Referer": "https://www.google.com/"})

        # Navigate to blank page
        page.goto("about:blank")

        logger.info(f"Created browser profile: {profile_name}")
        return profile_path

    def get_profiles(self) -> List[str]:
        """
        Get list of available browser profiles.

        Returns:
            List of profile names
        """
        profiles_dir = Path("profiles")
        if not profiles_dir.exists():
            return []

        return [d.name for d in profiles_dir.iterdir() if d.is_dir()]
