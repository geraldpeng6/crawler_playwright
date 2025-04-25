#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GUI entry point for the web interaction element crawler.

This script initializes and runs the graphical user interface for the crawler.
"""

import sys
from src.gui.main_window import CrawlerGUI
from src.utils.logger import setup_logger
from PyQt6.QtWidgets import QApplication

logger = setup_logger()

def main():
    """Initialize and run the GUI application."""
    try:
        app = QApplication(sys.argv)
        app.setApplicationName("Web Interaction Element Crawler")
        
        # Set application style
        app.setStyle("Fusion")
        
        # Create and show the main window
        main_window = CrawlerGUI()
        main_window.show()
        
        # Run the application
        sys.exit(app.exec())
    except Exception as e:
        logger.error(f"Error starting GUI: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
