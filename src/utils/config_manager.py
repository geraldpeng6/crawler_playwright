#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Configuration manager for the web interaction element crawler.

This module provides functions to save and load configuration settings.
"""

import os
import json
from pathlib import Path
from src.utils.config import Config
from src.utils.logger import get_logger

logger = get_logger()

CONFIG_FILE = "crawler_config.json"

def save_config(config: Config) -> bool:
    """
    Save configuration to a JSON file.
    
    Args:
        config: Configuration object to save
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Convert config to dictionary
        config_dict = config.to_dict()
        
        # Save to JSON file
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config_dict, f, ensure_ascii=False, indent=2)
            
        logger.info(f"Configuration saved to {CONFIG_FILE}")
        return True
    except Exception as e:
        logger.error(f"Error saving configuration: {e}")
        return False

def load_config() -> Config:
    """
    Load configuration from a JSON file.
    
    Returns:
        Configuration object
    """
    # Create default config
    config = Config()
    
    # Check if config file exists
    if not os.path.exists(CONFIG_FILE):
        logger.info(f"Configuration file {CONFIG_FILE} not found, using defaults")
        return config
    
    try:
        # Load from JSON file
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            config_dict = json.load(f)
            
        # Create config from dictionary
        config = Config.from_dict(config_dict)
        logger.info(f"Configuration loaded from {CONFIG_FILE}")
        return config
    except Exception as e:
        logger.error(f"Error loading configuration: {e}")
        return config
