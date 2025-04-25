#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Main entry point for the command-line interface of the web interaction element crawler.

This script handles command-line arguments and initializes the crawler with the
appropriate settings.
"""

import argparse
import os
import sys
from pathlib import Path

from src.crawler.crawler import InteractionCrawler
from src.utils.config import Config
from src.utils.logger import setup_logger

logger = setup_logger()

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Web Interaction Element Crawler - Command Line Interface"
    )

    # Basic arguments
    parser.add_argument(
        "csv_file",
        help="Path to CSV file containing URLs to crawl"
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run browser in headless mode"
    )
    parser.add_argument(
        "--output-dir",
        default="output",
        help="Directory to save results (default: output)"
    )
    parser.add_argument(
        "--profile",
        help="Browser profile to use"
    )

    # Crawler settings
    crawler_group = parser.add_argument_group("Crawler Settings")
    crawler_group.add_argument(
        "--similarity",
        type=int,
        default=70,
        help="Similarity threshold for keyword matching (0-100, default: 70)"
    )
    crawler_group.add_argument(
        "--scroll-count",
        type=int,
        default=3,
        help="Number of times to scroll the page (default: 3)"
    )
    crawler_group.add_argument(
        "--delay",
        type=float,
        default=2.0,
        help="Delay between URLs in seconds (default: 2.0)"
    )

    # Anti-crawler settings
    anti_crawler_group = parser.add_argument_group("Anti-Crawler Settings")
    anti_crawler_group.add_argument(
        "--random-delay",
        action="store_true",
        help="Use random delay between requests"
    )
    anti_crawler_group.add_argument(
        "--min-delay",
        type=float,
        default=1.0,
        help="Minimum delay in seconds (default: 1.0)"
    )
    anti_crawler_group.add_argument(
        "--max-delay",
        type=float,
        default=5.0,
        help="Maximum delay in seconds (default: 5.0)"
    )
    anti_crawler_group.add_argument(
        "--rotate-user-agent",
        action="store_true",
        help="Rotate user agents for each request"
    )
    anti_crawler_group.add_argument(
        "--use-referrers",
        action="store_true",
        help="Add HTTP referrer headers"
    )
    anti_crawler_group.add_argument(
        "--rate-limit",
        action="store_true",
        help="Enable rate limiting"
    )
    anti_crawler_group.add_argument(
        "--requests-per-minute",
        type=int,
        default=20,
        help="Maximum requests per minute (default: 20)"
    )
    anti_crawler_group.add_argument(
        "--retry-count",
        type=int,
        default=3,
        help="Number of retry attempts on failure (default: 3)"
    )
    anti_crawler_group.add_argument(
        "--retry-backoff",
        type=float,
        default=2.0,
        help="Exponential backoff factor for retries (default: 2.0)"
    )
    anti_crawler_group.add_argument(
        "--emulate-human",
        action="store_true",
        help="Emulate human-like behavior"
    )

    # Multi-threading settings
    threading_group = parser.add_argument_group("Multi-Threading Settings")
    threading_group.add_argument(
        "--multithreading",
        action="store_true",
        help="Enable multi-threaded crawling for different domains"
    )
    threading_group.add_argument(
        "--threads",
        type=int,
        default=4,
        help="Maximum number of threads to use (default: 4)"
    )
    threading_group.add_argument(
        "--domains-per-thread",
        type=int,
        default=2,
        help="Maximum number of domains per thread (default: 2)"
    )

    return parser.parse_args()

def main():
    """Main function to run the crawler from command line."""
    args = parse_arguments()

    # Validate CSV file
    if not os.path.exists(args.csv_file):
        logger.error(f"CSV file not found: {args.csv_file}")
        sys.exit(1)

    # Create output directory if it doesn't exist
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Initialize configuration
    config = Config()

    # Basic settings
    config.headless = args.headless
    config.output_dir = str(output_dir)
    config.similarity_threshold = args.similarity
    config.scroll_count = args.scroll_count
    config.delay = args.delay
    config.profile_name = args.profile

    # Anti-crawler settings
    config.random_delay = args.random_delay
    config.min_delay = args.min_delay
    config.max_delay = args.max_delay
    config.rotate_user_agent = args.rotate_user_agent
    config.use_referrers = args.use_referrers
    config.rate_limit = args.rate_limit
    config.requests_per_minute = args.requests_per_minute
    config.retry_count = args.retry_count
    config.retry_backoff = args.retry_backoff
    config.emulate_human_behavior = args.emulate_human

    # Multi-threading settings
    config.use_multithreading = args.multithreading
    config.max_threads = args.threads
    config.max_domains_per_thread = args.domains_per_thread

    # Initialize and run crawler
    try:
        crawler = InteractionCrawler(config)
        crawler.crawl_from_csv(args.csv_file)
    except Exception as e:
        logger.error(f"Error during crawling: {e}")
        sys.exit(1)
    finally:
        logger.info("Crawling completed")

if __name__ == "__main__":
    main()
