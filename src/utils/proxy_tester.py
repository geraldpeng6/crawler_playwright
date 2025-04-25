#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Proxy tester for the web interaction element crawler.

This module provides functions to test proxy functionality.
"""

import time
import json
import requests
from typing import Dict, Any, Optional, Tuple
from src.utils.logger import get_logger

logger = get_logger()

def test_proxy(proxy_url: str) -> Dict[str, Any]:
    """
    Test a proxy server and get information about it.
    
    Args:
        proxy_url: Proxy URL in format protocol://host:port
        
    Returns:
        Dictionary containing test results
    """
    result = {
        "success": False,
        "latency": None,
        "ip": None,
        "location": None,
        "error": None
    }
    
    try:
        # Set up proxies
        proxies = {
            "http": proxy_url,
            "https": proxy_url
        }
        
        # Measure latency
        start_time = time.time()
        
        # Make request to IP info service
        response = requests.get(
            "https://ipinfo.io/json",
            proxies=proxies,
            timeout=10
        )
        
        # Calculate latency
        latency = (time.time() - start_time) * 1000  # Convert to milliseconds
        
        # Check if request was successful
        if response.status_code == 200:
            # Parse response
            data = response.json()
            
            # Update result
            result["success"] = True
            result["latency"] = round(latency, 2)
            result["ip"] = data.get("ip", "Unknown")
            
            # Get location information
            city = data.get("city", "")
            region = data.get("region", "")
            country = data.get("country", "")
            
            # Format location
            location_parts = [part for part in [city, region, country] if part]
            result["location"] = ", ".join(location_parts) if location_parts else "Unknown"
            
            logger.info(f"Proxy test successful: {result}")
        else:
            result["error"] = f"HTTP Error: {response.status_code}"
            logger.warning(f"Proxy test failed: {result['error']}")
    except Exception as e:
        result["error"] = str(e)
        logger.error(f"Proxy test error: {e}")
    
    return result

def get_current_ip() -> Tuple[bool, Dict[str, Any]]:
    """
    Get current IP address and location information without using a proxy.
    
    Returns:
        Tuple containing success flag and result dictionary
    """
    result = {
        "ip": None,
        "location": None,
        "latency": None,
        "error": None
    }
    
    try:
        # Measure latency
        start_time = time.time()
        
        # Make request to IP info service
        response = requests.get("https://ipinfo.io/json", timeout=10)
        
        # Calculate latency
        latency = (time.time() - start_time) * 1000  # Convert to milliseconds
        
        # Check if request was successful
        if response.status_code == 200:
            # Parse response
            data = response.json()
            
            # Update result
            result["ip"] = data.get("ip", "Unknown")
            result["latency"] = round(latency, 2)
            
            # Get location information
            city = data.get("city", "")
            region = data.get("region", "")
            country = data.get("country", "")
            
            # Format location
            location_parts = [part for part in [city, region, country] if part]
            result["location"] = ", ".join(location_parts) if location_parts else "Unknown"
            
            logger.info(f"Current IP: {result['ip']}, Location: {result['location']}")
            return True, result
        else:
            result["error"] = f"HTTP Error: {response.status_code}"
            logger.warning(f"Failed to get current IP: {result['error']}")
            return False, result
    except Exception as e:
        result["error"] = str(e)
        logger.error(f"Error getting current IP: {e}")
        return False, result
