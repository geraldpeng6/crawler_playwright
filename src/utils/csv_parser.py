#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CSV parsing module for the web interaction element crawler.

This module provides functionality for parsing CSV files containing URLs.
"""

import pandas as pd
import os
from typing import List, Tuple, Optional, Dict, Any
from src.utils.logger import get_logger
from src.utils.config import Config

logger = get_logger()

def parse_csv(file_path: str, config: Optional[Config] = None) -> Tuple[List[str], Optional[str], Optional[pd.DataFrame]]:
    """
    Parse a CSV file and extract URLs.

    Args:
        file_path: Path to the CSV file
        config: Configuration object with processing status settings

    Returns:
        Tuple containing a list of URLs, the name of the URL column, and the DataFrame
    """
    try:
        # Read CSV file
        df = pd.read_csv(file_path)

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
            return [], None

        # Filter URLs based on processing status if configured
        filtered_urls = []
        if config and config.track_processed_urls and config.process_only_unprocessed:
            # Check if processed column exists
            processed_col = config.processed_status_column
            if processed_col not in df.columns:
                # Add the column if it doesn't exist
                df[processed_col] = ""
                logger.info(f"Added '{processed_col}' column to CSV file")

            # Filter URLs that haven't been processed (any value that is not "t")
            for i, row in df.iterrows():
                url = row[url_column]
                processed = str(row.get(processed_col, "")).strip().lower()
                if processed != "t":  # Only "t" is considered as processed, anything else is unprocessed
                    filtered_urls.append(url)

            logger.info(f"Found {len(filtered_urls)} unprocessed URLs out of {len(df)} total")
        else:
            # Use all URLs
            filtered_urls = df[url_column].tolist()
            logger.info(f"Found {len(filtered_urls)} URLs in CSV file")

        return filtered_urls, url_column, df

    except Exception as e:
        logger.error(f"Error parsing CSV file: {e}")
        return [], None, None

def mark_url_as_processed(df: pd.DataFrame, url: str, url_column: str, config: Config) -> bool:
    """
    Mark a URL as processed in the CSV file.

    Args:
        df: DataFrame containing the CSV data
        url: URL to mark as processed
        url_column: Name of the column containing URLs
        config: Configuration object with processing status settings

    Returns:
        True if successful, False otherwise
    """
    try:
        if not config.track_processed_urls:
            return True

        # Find the row with the URL
        row_idx = df[df[url_column] == url].index
        if len(row_idx) == 0:
            logger.warning(f"URL {url} not found in CSV file")
            return False

        # Mark as processed
        processed_col = config.processed_status_column
        if processed_col not in df.columns:
            df[processed_col] = ""

        df.loc[row_idx, processed_col] = "t"
        logger.debug(f"Marked URL {url} as processed (t)")
        return True

    except Exception as e:
        logger.error(f"Error marking URL as processed: {e}")
        return False

def save_csv(df: pd.DataFrame, file_path: str) -> bool:
    """
    Save DataFrame to CSV file.

    Args:
        df: DataFrame to save
        file_path: Path to save the CSV file

    Returns:
        True if successful, False otherwise
    """
    try:
        df.to_csv(file_path, index=False)
        logger.debug(f"Saved CSV file to {file_path}")
        return True
    except Exception as e:
        logger.error(f"Error saving CSV file: {e}")
        return False
