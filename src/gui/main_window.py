#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Main window for the GUI interface of the web interaction element crawler.

This module contains the main window class for the GUI interface.
"""

import os
import sys
import glob
import time
import threading
from pathlib import Path
from typing import List, Optional, Tuple

from PyQt6.QtCore import Qt, QSize, pyqtSignal, QThread
from PyQt6.QtGui import QIcon, QFont, QTextCursor
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QLineEdit, QFileDialog,
    QTextEdit, QSpinBox, QDoubleSpinBox, QCheckBox,
    QComboBox, QTabWidget, QGroupBox, QMessageBox,
    QProgressBar, QSplitter, QDialog
)

from src.crawler.crawler import InteractionCrawler
from src.utils.config import Config
from src.utils.csv_parser import parse_csv, mark_url_as_processed, save_csv
from src.utils.logger import get_logger
from src.gui.profile_manager import ProfileManagerDialog
from src.utils.config_manager import save_config, load_config
from src.utils.proxy_tester import test_proxy, get_current_ip

logger = get_logger()

class LogHandler(QThread):
    """Thread for handling log messages and updating the GUI."""

    log_signal = pyqtSignal(str)

    def __init__(self, log_widget):
        """Initialize the log handler."""
        super().__init__()
        self.log_widget = log_widget
        self.running = True

    def run(self):
        """Run the log handler thread."""
        # This is a placeholder for a more sophisticated log handler
        # In a real implementation, this would read from a log queue
        pass

    def add_log(self, message):
        """Add a log message to the log widget."""
        self.log_signal.emit(message)

    def update_log_widget(self, message):
        """Update the log widget with a new message."""
        self.log_widget.moveCursor(QTextCursor.MoveOperation.End)
        self.log_widget.insertPlainText(message + "\n")
        self.log_widget.moveCursor(QTextCursor.MoveOperation.End)

    def stop(self):
        """Stop the log handler thread."""
        self.running = False
        self.wait()

class CrawlerThread(QThread):
    """Thread for running the crawler in the background."""

    progress_signal = pyqtSignal(int, int)  # current, total
    log_signal = pyqtSignal(str)
    finished_signal = pyqtSignal(bool, str)  # success, message

    def __init__(self, config: Config, csv_path: str):
        """Initialize the crawler thread."""
        super().__init__()
        self.config = config
        self.csv_path = csv_path

    def run(self):
        """Run the crawler thread."""
        try:
            # Parse CSV file with config for processing status
            urls, url_column, df = parse_csv(self.csv_path, self.config)
            if not urls:
                self.finished_signal.emit(False, "No URLs found in CSV file")
                return

            # Store CSV data for updating processing status
            self.csv_df = df
            self.url_column = url_column

            # Initialize crawler
            crawler = InteractionCrawler(self.config)

            # Set custom keywords
            if self.config.custom_keywords:
                crawler.set_custom_keywords(self.config.custom_keywords)

            # Check if we should use multi-threading
            if self.config.use_multithreading and len(urls) > 1:
                self.log_signal.emit(f"Using multi-threaded crawling with {self.config.max_threads} threads")
                self.crawl_multithreaded(crawler, urls)
            else:
                self.log_signal.emit("Using sequential crawling")
                self.crawl_sequential(crawler, urls)

        except Exception as e:
            self.log_signal.emit(f"Error during crawling: {str(e)}")
            self.finished_signal.emit(False, f"Error: {str(e)}")

    def crawl_sequential(self, crawler, urls):
        """Crawl URLs sequentially."""
        try:
            # Start browser
            crawler.start_browser()

            # Process each URL
            for i, url in enumerate(urls):
                self.log_signal.emit(f"Processing URL {i+1}/{len(urls)}: {url}")
                try:
                    result = crawler.crawl_url(url)
                    self.log_signal.emit(f"Found {result['elements_count']} elements on {url}")

                    # Mark URL as processed
                    if self.config.track_processed_urls:
                        if mark_url_as_processed(self.csv_df, url, self.url_column, self.config):
                            save_csv(self.csv_df, self.csv_path)
                            self.log_signal.emit(f"Marked URL as processed in CSV file")
                except Exception as e:
                    self.log_signal.emit(f"Error processing URL {url}: {str(e)}")

                # Update progress
                self.progress_signal.emit(i + 1, len(urls))

                # Add delay between URLs
                if i < len(urls) - 1:
                    if self.config.random_delay:
                        from src.utils.anti_crawler import AntiCrawlerUtils
                        # Use random delay
                        delay = AntiCrawlerUtils.get_random_delay(
                            self.config.min_delay,
                            self.config.max_delay
                        )
                        self.log_signal.emit(f"Waiting {delay:.2f} seconds before next URL...")
                        import time
                        time.sleep(delay)
                    else:
                        # Use fixed delay
                        self.log_signal.emit(f"Waiting {self.config.delay:.2f} seconds before next URL...")
                        import time
                        time.sleep(self.config.delay)

            # Close browser
            crawler.close_browser()

            self.finished_signal.emit(True, f"Crawling completed. Processed {len(urls)} URLs.")

        except Exception as e:
            self.log_signal.emit(f"Error during sequential crawling: {str(e)}")
            self.finished_signal.emit(False, f"Error: {str(e)}")

    def crawl_multithreaded(self, crawler, urls):
        """Crawl URLs using multiple threads."""
        try:
            # Use the crawler's multithreaded crawling method
            self.log_signal.emit("Starting multi-threaded crawling...")

            # Create a progress monitor thread
            progress_monitor_running = True

            def progress_monitor():
                """Monitor progress of multi-threaded crawling."""
                last_count = 0
                while progress_monitor_running:
                    try:
                        # Get current progress
                        current_count = sum(1 for r in results if r is not None)

                        # Update progress if changed
                        if current_count != last_count:
                            self.progress_signal.emit(current_count, len(urls))
                            last_count = current_count

                        # Sleep to avoid high CPU usage
                        time.sleep(0.5)
                    except Exception:
                        # Ignore errors in progress monitoring
                        pass

            # Start progress monitor thread
            results = []
            monitor_thread = threading.Thread(target=progress_monitor)
            monitor_thread.daemon = True
            monitor_thread.start()

            try:
                # Start multi-threaded crawling
                results = crawler.crawl_urls_multithreaded(urls)

                # Update progress to completion
                self.progress_signal.emit(len(urls), len(urls))

                # Count successful results
                successful = sum(1 for r in results if r.get("elements_count", 0) > 0)

                # Mark successful URLs as processed
                if self.config.track_processed_urls:
                    processed_count = 0
                    for result in results:
                        if result and result.get("elements_count", 0) > 0:
                            url = result.get("url")
                            if url and mark_url_as_processed(self.csv_df, url, self.url_column, self.config):
                                processed_count += 1

                    # Save the CSV file with processed status
                    if processed_count > 0:
                        save_csv(self.csv_df, self.csv_path)
                        self.log_signal.emit(f"Marked {processed_count} URLs as processed in CSV file")

                self.log_signal.emit(f"Multi-threaded crawling completed. Successfully processed {successful} of {len(urls)} URLs.")
                self.finished_signal.emit(True, f"Crawling completed. Successfully processed {successful} of {len(urls)} URLs.")
            finally:
                # Stop progress monitor
                progress_monitor_running = False
                monitor_thread.join(timeout=1.0)  # Wait for monitor thread to finish

        except Exception as e:
            self.log_signal.emit(f"Error during multi-threaded crawling: {str(e)}")
            self.finished_signal.emit(False, f"Error: {str(e)}")

class CrawlerGUI(QMainWindow):
    """Main window for the crawler GUI."""

    def __init__(self):
        """Initialize the main window."""
        super().__init__()

        # Load configuration from file
        self.config = load_config()
        self.crawler = None
        self.crawler_thread = None
        self.log_handler = None

        self.init_ui()

        # Load UI values from config
        self.load_ui_from_config()

    def init_ui(self):
        """Initialize the user interface."""
        # Set window properties
        self.setWindowTitle("Web Interaction Element Crawler")
        self.setMinimumSize(800, 600)

        # Create central widget and main layout
        central_widget = QWidget()
        main_layout = QVBoxLayout(central_widget)

        # Create tab widget
        tab_widget = QTabWidget()

        # Create tabs
        crawler_tab = self.create_crawler_tab()
        settings_tab = self.create_settings_tab()

        # Add tabs to tab widget
        tab_widget.addTab(crawler_tab, "Crawler")
        tab_widget.addTab(settings_tab, "Settings")

        # Add tab widget to main layout
        main_layout.addWidget(tab_widget)

        # Set central widget
        self.setCentralWidget(central_widget)

        # Initialize log handler
        self.log_handler = LogHandler(self.log_text)
        self.log_handler.log_signal.connect(self.log_handler.update_log_widget)
        self.log_handler.start()

        # Log initialization
        logger.info("GUI initialized")
        self.log_handler.add_log("Web Interaction Element Crawler GUI initialized")

    def create_crawler_tab(self):
        """Create the crawler tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Input section
        input_group = QGroupBox("Input")
        input_layout = QVBoxLayout(input_group)

        # CSV file selection
        csv_layout = QHBoxLayout()
        csv_label = QLabel("CSV File (from csv_files folder):")

        # CSV dropdown for files in current directory
        self.csv_combo = QComboBox()
        self.csv_combo.setMinimumWidth(200)
        self.csv_combo.currentIndexChanged.connect(self.on_csv_selected)

        # Refresh button for CSV dropdown
        csv_refresh_button = QPushButton("🔄")
        csv_refresh_button.setToolTip("Refresh CSV file list")
        csv_refresh_button.setMaximumWidth(30)
        csv_refresh_button.clicked.connect(self.update_csv_dropdown)

        # Open folder button
        csv_folder_button = QPushButton("📁")
        csv_folder_button.setToolTip("Open CSV files folder")
        csv_folder_button.setMaximumWidth(30)
        csv_folder_button.clicked.connect(self.open_csv_folder)

        # Browse button
        csv_browse_button = QPushButton("Browse...")
        csv_browse_button.clicked.connect(self.browse_csv)

        # Path display
        self.csv_path_edit = QLineEdit()
        self.csv_path_edit.setReadOnly(True)

        # Update the dropdown
        self.update_csv_dropdown()

        # Add widgets to layout
        csv_layout.addWidget(csv_label)
        csv_layout.addWidget(self.csv_combo)
        csv_layout.addWidget(csv_refresh_button)
        csv_layout.addWidget(csv_folder_button)
        csv_layout.addWidget(csv_browse_button)

        # Add path display in a separate row
        csv_path_layout = QHBoxLayout()
        csv_path_layout.addWidget(QLabel("Path:"))
        csv_path_layout.addWidget(self.csv_path_edit)

        # Output directory selection
        output_layout = QHBoxLayout()
        output_label = QLabel("Output Directory:")
        self.output_dir_edit = QLineEdit()
        self.output_dir_edit.setText(self.config.output_dir)
        output_browse_button = QPushButton("Browse...")
        output_browse_button.clicked.connect(self.browse_output_dir)

        output_layout.addWidget(output_label)
        output_layout.addWidget(self.output_dir_edit)
        output_layout.addWidget(output_browse_button)

        # Profile selection
        profile_layout = QHBoxLayout()
        profile_label = QLabel("Browser Profile:")
        self.profile_combo = QComboBox()
        self.profile_combo.addItem("None")
        self.update_profile_list()
        profile_manage_button = QPushButton("Manage Profiles...")
        profile_manage_button.clicked.connect(self.manage_profiles)

        profile_layout.addWidget(profile_label)
        profile_layout.addWidget(self.profile_combo)
        profile_layout.addWidget(profile_manage_button)

        # Add layouts to input group
        input_layout.addLayout(csv_layout)
        input_layout.addLayout(csv_path_layout)
        input_layout.addLayout(output_layout)
        input_layout.addLayout(profile_layout)

        # Options section
        options_group = QGroupBox("Options")
        options_layout = QVBoxLayout(options_group)

        # Headless mode
        headless_layout = QHBoxLayout()
        self.headless_checkbox = QCheckBox("Headless Mode")
        self.headless_checkbox.setToolTip("Run browser without visible window")
        headless_layout.addWidget(self.headless_checkbox)
        headless_layout.addStretch()

        # Crawler options
        crawler_options_layout = QHBoxLayout()

        # Similarity threshold
        similarity_label = QLabel("Similarity Threshold:")
        self.similarity_spin = QSpinBox()
        self.similarity_spin.setRange(0, 100)
        self.similarity_spin.setValue(self.config.similarity_threshold)
        self.similarity_spin.setToolTip("Threshold for keyword matching (0-100)")

        # Scroll count
        scroll_label = QLabel("Scroll Count:")
        self.scroll_spin = QSpinBox()
        self.scroll_spin.setRange(0, 20)
        self.scroll_spin.setValue(self.config.scroll_count)
        self.scroll_spin.setToolTip("Number of times to scroll the page")

        # Delay
        delay_label = QLabel("Delay (seconds):")
        self.delay_spin = QDoubleSpinBox()
        self.delay_spin.setRange(0, 60)
        self.delay_spin.setValue(self.config.delay)
        self.delay_spin.setToolTip("Delay between URLs in seconds")

        crawler_options_layout.addWidget(similarity_label)
        crawler_options_layout.addWidget(self.similarity_spin)
        crawler_options_layout.addSpacing(20)
        crawler_options_layout.addWidget(scroll_label)
        crawler_options_layout.addWidget(self.scroll_spin)
        crawler_options_layout.addSpacing(20)
        crawler_options_layout.addWidget(delay_label)
        crawler_options_layout.addWidget(self.delay_spin)
        crawler_options_layout.addStretch()

        # Add layouts to options group
        options_layout.addLayout(headless_layout)
        options_layout.addLayout(crawler_options_layout)

        # Custom keywords section
        keywords_group = QGroupBox("Custom Keywords")
        keywords_layout = QVBoxLayout(keywords_group)

        keywords_label = QLabel("Enter custom keywords (one per line):")
        self.keywords_text = QTextEdit()
        self.keywords_text.setPlaceholderText("Enter custom keywords here...")

        keywords_layout.addWidget(keywords_label)
        keywords_layout.addWidget(self.keywords_text)

        # Control section
        control_layout = QHBoxLayout()

        self.start_button = QPushButton("Start Crawling")
        self.start_button.clicked.connect(self.start_crawling)

        self.stop_button = QPushButton("Stop")
        self.stop_button.clicked.connect(self.stop_crawling)
        self.stop_button.setEnabled(False)

        control_layout.addWidget(self.start_button)
        control_layout.addWidget(self.stop_button)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("%v/%m URLs (%p%)")

        # Log section
        log_group = QGroupBox("Log")
        log_layout = QVBoxLayout(log_group)

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Courier", 9))

        log_layout.addWidget(self.log_text)

        # Add all sections to main layout
        layout.addWidget(input_group)
        layout.addWidget(options_group)
        layout.addWidget(keywords_group)
        layout.addLayout(control_layout)
        layout.addWidget(self.progress_bar)
        layout.addWidget(log_group)

        return tab

    def create_settings_tab(self):
        """Create the settings tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Create tab widget for settings categories
        settings_tabs = QTabWidget()

        # Anti-crawler settings tab
        anti_crawler_tab = self.create_anti_crawler_tab()
        settings_tabs.addTab(anti_crawler_tab, "Anti-Crawler")

        # Advanced settings tab
        advanced_tab = self.create_advanced_settings_tab()
        settings_tabs.addTab(advanced_tab, "Advanced")

        # Add tab widget to main layout
        layout.addWidget(settings_tabs)

        return tab

    def create_anti_crawler_tab(self):
        """Create the anti-crawler settings tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Delay settings
        delay_group = QGroupBox("Delay Settings")
        delay_layout = QVBoxLayout(delay_group)

        # Random delay
        random_delay_layout = QHBoxLayout()
        self.random_delay_checkbox = QCheckBox("Use Random Delay")
        self.random_delay_checkbox.setChecked(self.config.random_delay)
        self.random_delay_checkbox.setToolTip("Add random delay between requests")
        random_delay_layout.addWidget(self.random_delay_checkbox)
        random_delay_layout.addStretch()

        # Min/Max delay
        delay_range_layout = QHBoxLayout()
        min_delay_label = QLabel("Min Delay (seconds):")
        self.min_delay_spin = QDoubleSpinBox()
        self.min_delay_spin.setRange(0, 30)
        self.min_delay_spin.setValue(self.config.min_delay)
        self.min_delay_spin.setToolTip("Minimum delay between requests in seconds")

        max_delay_label = QLabel("Max Delay (seconds):")
        self.max_delay_spin = QDoubleSpinBox()
        self.max_delay_spin.setRange(0, 60)
        self.max_delay_spin.setValue(self.config.max_delay)
        self.max_delay_spin.setToolTip("Maximum delay between requests in seconds")

        delay_range_layout.addWidget(min_delay_label)
        delay_range_layout.addWidget(self.min_delay_spin)
        delay_range_layout.addSpacing(20)
        delay_range_layout.addWidget(max_delay_label)
        delay_range_layout.addWidget(self.max_delay_spin)
        delay_range_layout.addStretch()

        # Rate limiting
        rate_limit_layout = QHBoxLayout()
        self.rate_limit_checkbox = QCheckBox("Enable Rate Limiting")
        self.rate_limit_checkbox.setChecked(self.config.rate_limit)
        self.rate_limit_checkbox.setToolTip("Limit request rate")

        requests_per_minute_label = QLabel("Requests Per Minute:")
        self.requests_per_minute_spin = QSpinBox()
        self.requests_per_minute_spin.setRange(1, 100)
        self.requests_per_minute_spin.setValue(self.config.requests_per_minute)
        self.requests_per_minute_spin.setToolTip("Maximum number of requests per minute")

        rate_limit_layout.addWidget(self.rate_limit_checkbox)
        rate_limit_layout.addSpacing(20)
        rate_limit_layout.addWidget(requests_per_minute_label)
        rate_limit_layout.addWidget(self.requests_per_minute_spin)
        rate_limit_layout.addStretch()

        # Add layouts to delay group
        delay_layout.addLayout(random_delay_layout)
        delay_layout.addLayout(delay_range_layout)
        delay_layout.addLayout(rate_limit_layout)

        # Browser emulation settings
        emulation_group = QGroupBox("Browser Emulation")
        emulation_layout = QVBoxLayout(emulation_group)

        # User agent rotation
        user_agent_layout = QHBoxLayout()
        self.rotate_user_agent_checkbox = QCheckBox("Rotate User Agents")
        self.rotate_user_agent_checkbox.setChecked(self.config.rotate_user_agent)
        self.rotate_user_agent_checkbox.setToolTip("Rotate user agents for each request")
        user_agent_layout.addWidget(self.rotate_user_agent_checkbox)
        user_agent_layout.addStretch()

        # Custom user agents
        user_agents_label = QLabel("Custom User Agents (one per line, leave empty for defaults):")
        self.user_agents_text = QTextEdit()
        self.user_agents_text.setPlaceholderText("Enter custom user agents here...")
        self.user_agents_text.setMaximumHeight(100)

        # HTTP referrers
        referrer_layout = QHBoxLayout()
        self.use_referrers_checkbox = QCheckBox("Use HTTP Referrers")
        self.use_referrers_checkbox.setChecked(self.config.use_referrers)
        self.use_referrers_checkbox.setToolTip("Add HTTP referrer headers")
        referrer_layout.addWidget(self.use_referrers_checkbox)
        referrer_layout.addStretch()

        # Custom referrers
        referrers_label = QLabel("Custom Referrers (one per line, leave empty for defaults):")
        self.referrers_text = QTextEdit()
        self.referrers_text.setPlaceholderText("Enter custom referrers here...")
        self.referrers_text.setMaximumHeight(100)

        # Human behavior emulation
        behavior_layout = QHBoxLayout()
        self.emulate_human_behavior_checkbox = QCheckBox("Emulate Human Behavior")
        self.emulate_human_behavior_checkbox.setChecked(self.config.emulate_human_behavior)
        self.emulate_human_behavior_checkbox.setToolTip("Simulate human-like behavior")

        self.random_scroll_checkbox = QCheckBox("Random Scrolling")
        self.random_scroll_checkbox.setChecked(self.config.random_scroll)
        self.random_scroll_checkbox.setToolTip("Use random scrolling patterns")

        self.mouse_movement_checkbox = QCheckBox("Simulate Mouse Movements")
        self.mouse_movement_checkbox.setChecked(self.config.mouse_movement)
        self.mouse_movement_checkbox.setToolTip("Simulate mouse movements")

        behavior_layout.addWidget(self.emulate_human_behavior_checkbox)
        behavior_layout.addWidget(self.random_scroll_checkbox)
        behavior_layout.addWidget(self.mouse_movement_checkbox)
        behavior_layout.addStretch()

        # Add layouts to emulation group
        emulation_layout.addLayout(user_agent_layout)
        emulation_layout.addWidget(user_agents_label)
        emulation_layout.addWidget(self.user_agents_text)
        emulation_layout.addLayout(referrer_layout)
        emulation_layout.addWidget(referrers_label)
        emulation_layout.addWidget(self.referrers_text)
        emulation_layout.addLayout(behavior_layout)

        # Retry settings
        retry_group = QGroupBox("Retry Settings")
        retry_layout = QHBoxLayout(retry_group)

        retry_count_label = QLabel("Retry Count:")
        self.retry_count_spin = QSpinBox()
        self.retry_count_spin.setRange(0, 10)
        self.retry_count_spin.setValue(self.config.retry_count)
        self.retry_count_spin.setToolTip("Number of retry attempts on failure")

        retry_backoff_label = QLabel("Backoff Factor:")
        self.retry_backoff_spin = QDoubleSpinBox()
        self.retry_backoff_spin.setRange(1.0, 5.0)
        self.retry_backoff_spin.setValue(self.config.retry_backoff)
        self.retry_backoff_spin.setToolTip("Exponential backoff factor for retries")

        retry_layout.addWidget(retry_count_label)
        retry_layout.addWidget(self.retry_count_spin)
        retry_layout.addSpacing(20)
        retry_layout.addWidget(retry_backoff_label)
        retry_layout.addWidget(self.retry_backoff_spin)
        retry_layout.addStretch()

        # Add groups to main layout
        layout.addWidget(delay_group)
        layout.addWidget(emulation_group)
        layout.addWidget(retry_group)
        layout.addStretch()

        return tab

    def create_advanced_settings_tab(self):
        """Create the advanced settings tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Multi-threading settings
        threading_group = QGroupBox("Multi-Threading Settings")
        threading_layout = QVBoxLayout(threading_group)

        # Use multi-threading
        use_threading_layout = QHBoxLayout()
        self.use_multithreading_checkbox = QCheckBox("Enable Multi-Threading")
        self.use_multithreading_checkbox.setChecked(self.config.use_multithreading)
        self.use_multithreading_checkbox.setToolTip("Enable parallel crawling of different domains")
        use_threading_layout.addWidget(self.use_multithreading_checkbox)
        use_threading_layout.addStretch()

        # Thread count
        thread_settings_layout = QHBoxLayout()

        max_threads_label = QLabel("Maximum Threads:")
        self.max_threads_spin = QSpinBox()
        self.max_threads_spin.setRange(1, 16)
        self.max_threads_spin.setValue(self.config.max_threads)
        self.max_threads_spin.setToolTip("Maximum number of concurrent threads")

        max_domains_label = QLabel("Max Domains Per Thread:")
        self.max_domains_spin = QSpinBox()
        self.max_domains_spin.setRange(1, 10)
        self.max_domains_spin.setValue(self.config.max_domains_per_thread)
        self.max_domains_spin.setToolTip("Maximum number of domains a single thread can handle")

        thread_settings_layout.addWidget(max_threads_label)
        thread_settings_layout.addWidget(self.max_threads_spin)
        thread_settings_layout.addSpacing(20)
        thread_settings_layout.addWidget(max_domains_label)
        thread_settings_layout.addWidget(self.max_domains_spin)
        thread_settings_layout.addStretch()

        # Add layouts to threading group
        threading_layout.addLayout(use_threading_layout)
        threading_layout.addLayout(thread_settings_layout)

        # Threading explanation
        threading_explanation = QLabel(
            "Multi-threading allows crawling different domains in parallel. "
            "This can significantly speed up crawling when processing multiple websites. "
            "Each thread uses a separate browser instance. "
            "Note: Rate limiting is still applied per domain to avoid detection."
        )
        threading_explanation.setWordWrap(True)
        threading_explanation.setStyleSheet("color: gray;")
        threading_layout.addWidget(threading_explanation)

        # Proxy settings
        proxy_group = QGroupBox("Proxy Settings")
        proxy_layout = QVBoxLayout(proxy_group)

        # Use proxies
        use_proxies_layout = QHBoxLayout()
        self.use_proxies_checkbox = QCheckBox("Use Proxy Servers")
        self.use_proxies_checkbox.setChecked(self.config.use_proxies)
        self.use_proxies_checkbox.setToolTip("Use proxy servers for requests")
        use_proxies_layout.addWidget(self.use_proxies_checkbox)

        # Test proxy button
        self.test_proxy_button = QPushButton("Test Proxy")
        self.test_proxy_button.setToolTip("Test proxy functionality and show latency and IP location")
        self.test_proxy_button.clicked.connect(self.test_proxy)
        use_proxies_layout.addWidget(self.test_proxy_button)
        use_proxies_layout.addStretch()

        # Proxy list
        proxies_label = QLabel("Proxy Servers (one per line, format: protocol://host:port):")
        self.proxies_text = QTextEdit()
        self.proxies_text.setPlaceholderText("Enter proxy servers here...")

        # Set proxy text from config
        if self.config.proxies:
            self.proxies_text.setPlainText("\n".join(self.config.proxies))

        # Add layouts to proxy group
        proxy_layout.addLayout(use_proxies_layout)
        proxy_layout.addWidget(proxies_label)
        proxy_layout.addWidget(self.proxies_text)

        # Custom headers
        headers_group = QGroupBox("Custom HTTP Headers")
        headers_layout = QVBoxLayout(headers_group)

        headers_label = QLabel("Custom HTTP Headers (one per line, format: Header-Name: Value):")
        self.headers_text = QTextEdit()
        self.headers_text.setPlaceholderText("Enter custom HTTP headers here...")

        headers_layout.addWidget(headers_label)
        headers_layout.addWidget(self.headers_text)

        # URL Processing Status settings
        processing_group = QGroupBox("URL Processing Status")
        processing_layout = QVBoxLayout(processing_group)

        # Track processed URLs
        track_processed_layout = QHBoxLayout()
        self.track_processed_checkbox = QCheckBox("Track Processed URLs")
        self.track_processed_checkbox.setChecked(self.config.track_processed_urls)
        self.track_processed_checkbox.setToolTip("Mark URLs as processed in the CSV file")
        track_processed_layout.addWidget(self.track_processed_checkbox)
        track_processed_layout.addStretch()

        # Process only unprocessed URLs
        process_unprocessed_layout = QHBoxLayout()
        self.process_unprocessed_checkbox = QCheckBox("Process Only Unprocessed URLs")
        self.process_unprocessed_checkbox.setChecked(self.config.process_only_unprocessed)
        self.process_unprocessed_checkbox.setToolTip("Only process URLs that haven't been processed yet")
        process_unprocessed_layout.addWidget(self.process_unprocessed_checkbox)
        process_unprocessed_layout.addStretch()

        # Status column name
        status_column_layout = QHBoxLayout()
        status_column_label = QLabel("Status Column Name:")
        self.status_column_edit = QLineEdit()
        self.status_column_edit.setText(self.config.processed_status_column)
        self.status_column_edit.setToolTip("Name of the column in the CSV file to track processing status")
        status_column_layout.addWidget(status_column_label)
        status_column_layout.addWidget(self.status_column_edit)

        # Add explanation
        processing_explanation = QLabel(
            "When a URL is successfully processed, it will be marked with 't' in the specified column. "
            "If 'Process Only Unprocessed URLs' is checked, only URLs without a 't' in this column will be processed. "
            "Any value other than 't' (including empty, null, etc.) is considered unprocessed."
        )
        processing_explanation.setWordWrap(True)
        processing_explanation.setStyleSheet("color: gray;")

        # Add layouts to processing group
        processing_layout.addLayout(track_processed_layout)
        processing_layout.addLayout(process_unprocessed_layout)
        processing_layout.addLayout(status_column_layout)
        processing_layout.addWidget(processing_explanation)

        # Add groups to main layout
        layout.addWidget(threading_group)
        layout.addWidget(proxy_group)
        layout.addWidget(processing_group)
        layout.addWidget(headers_group)
        layout.addStretch()

        return tab

    def get_csv_files(self) -> List[Tuple[str, str]]:
        """
        Scan the CSV directory for CSV files.

        Returns:
            List of tuples containing (display_name, full_path) for each CSV file
        """
        csv_files = []

        # Ensure CSV directory exists
        csv_dir = os.path.join(os.getcwd(), "csv_files")
        os.makedirs(csv_dir, exist_ok=True)

        # Get all CSV files in the CSV directory
        for csv_file in glob.glob(os.path.join(csv_dir, "*.csv")):
            # Get just the filename for display
            filename = os.path.basename(csv_file)
            csv_files.append((filename, csv_file))

        # Sort by filename
        csv_files.sort(key=lambda x: x[0].lower())

        return csv_files

    def update_csv_dropdown(self):
        """Update the CSV dropdown with files from the CSV directory."""
        # Save current selection if any
        current_path = self.csv_path_edit.text()

        # Clear the dropdown
        self.csv_combo.clear()

        # Add a placeholder item
        self.csv_combo.addItem("Select a CSV file...", "")

        # Get CSV files and add to dropdown
        csv_files = self.get_csv_files()
        for display_name, file_path in csv_files:
            self.csv_combo.addItem(display_name, file_path)

        # Restore previous selection if it exists
        if current_path:
            for i in range(self.csv_combo.count()):
                if self.csv_combo.itemData(i) == current_path:
                    self.csv_combo.setCurrentIndex(i)
                    break

        # Log the number of CSV files found
        if self.log_handler:
            self.log_handler.add_log(f"Found {len(csv_files)} CSV files in the csv_files folder")

    def on_csv_selected(self, index):
        """Handle CSV selection from dropdown."""
        if index > 0:  # Skip the placeholder item
            file_path = self.csv_combo.itemData(index)
            if file_path:
                self.csv_path_edit.setText(file_path)
                self.log_handler.add_log(f"Selected CSV file: {file_path}")

    def browse_csv(self):
        """Open file dialog to select CSV file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select CSV File", "", "CSV Files (*.csv);;All Files (*)"
        )

        if file_path:
            # Get the CSV directory
            csv_dir = os.path.join(os.getcwd(), "csv_files")
            os.makedirs(csv_dir, exist_ok=True)

            # Get the filename
            filename = os.path.basename(file_path)

            # Create the destination path
            dest_path = os.path.join(csv_dir, filename)

            # Check if the file is already in the CSV directory
            if file_path != dest_path:
                # Copy the file to the CSV directory
                try:
                    import shutil
                    shutil.copy2(file_path, dest_path)
                    self.log_handler.add_log(f"Copied CSV file to: {dest_path}")
                    file_path = dest_path
                except Exception as e:
                    self.log_handler.add_log(f"Error copying CSV file: {str(e)}")

            # Set the path in the UI
            self.csv_path_edit.setText(file_path)
            self.log_handler.add_log(f"Selected CSV file: {file_path}")

            # Update the dropdown
            self.update_csv_dropdown()

            # Select the file in the dropdown
            for i in range(self.csv_combo.count()):
                if self.csv_combo.itemData(i) == file_path:
                    self.csv_combo.setCurrentIndex(i)
                    break

    def open_csv_folder(self):
        """Open the CSV files folder in the file explorer."""
        csv_dir = os.path.join(os.getcwd(), "csv_files")
        os.makedirs(csv_dir, exist_ok=True)

        try:
            # Open the folder using the appropriate command for the OS
            import platform
            import subprocess

            if platform.system() == "Windows":
                os.startfile(csv_dir)
            elif platform.system() == "Darwin":  # macOS
                subprocess.call(["open", csv_dir])
            else:  # Linux
                subprocess.call(["xdg-open", csv_dir])

            self.log_handler.add_log(f"Opened CSV files folder: {csv_dir}")
        except Exception as e:
            self.log_handler.add_log(f"Error opening CSV files folder: {str(e)}")
            QMessageBox.warning(
                self, "Error", f"Could not open CSV files folder: {str(e)}"
            )

    def browse_output_dir(self):
        """Open directory dialog to select output directory."""
        dir_path = QFileDialog.getExistingDirectory(
            self, "Select Output Directory", self.config.output_dir
        )

        if dir_path:
            self.output_dir_edit.setText(dir_path)
            self.config.output_dir = dir_path
            self.log_handler.add_log(f"Selected output directory: {dir_path}")

    def update_profile_list(self):
        """Update the profile list in the combo box."""
        # Save current selection
        current_profile = self.profile_combo.currentText()

        # Clear combo box
        self.profile_combo.clear()
        self.profile_combo.addItem("None")

        # Get profiles
        try:
            crawler = InteractionCrawler(self.config)
            profiles = crawler.get_profiles()

            for profile in profiles:
                self.profile_combo.addItem(profile)

            # Restore selection if possible
            index = self.profile_combo.findText(current_profile)
            if index >= 0:
                self.profile_combo.setCurrentIndex(index)

        except Exception as e:
            self.log_handler.add_log(f"Error updating profile list: {str(e)}")

    def manage_profiles(self):
        """Open the profile manager dialog."""
        dialog = ProfileManagerDialog(self)
        if dialog.exec():
            self.update_profile_list()

    def update_config_from_ui(self):
        """Update configuration from UI values."""
        # Basic settings
        self.config.output_dir = self.output_dir_edit.text()
        self.config.headless = self.headless_checkbox.isChecked()
        self.config.similarity_threshold = self.similarity_spin.value()
        self.config.scroll_count = self.scroll_spin.value()
        self.config.delay = self.delay_spin.value()

        # Get profile
        profile = self.profile_combo.currentText()
        self.config.profile_name = None if profile == "None" else profile

        # Get custom keywords
        keywords_text = self.keywords_text.toPlainText()
        if keywords_text:
            self.config.custom_keywords = [
                line.strip() for line in keywords_text.split("\n") if line.strip()
            ]
        else:
            self.config.custom_keywords = []

        # Anti-crawler delay settings
        self.config.random_delay = self.random_delay_checkbox.isChecked()
        self.config.min_delay = self.min_delay_spin.value()
        self.config.max_delay = self.max_delay_spin.value()
        self.config.rate_limit = self.rate_limit_checkbox.isChecked()
        self.config.requests_per_minute = self.requests_per_minute_spin.value()

        # Browser emulation settings
        self.config.rotate_user_agent = self.rotate_user_agent_checkbox.isChecked()
        self.config.use_referrers = self.use_referrers_checkbox.isChecked()
        self.config.emulate_human_behavior = self.emulate_human_behavior_checkbox.isChecked()
        self.config.random_scroll = self.random_scroll_checkbox.isChecked()
        self.config.mouse_movement = self.mouse_movement_checkbox.isChecked()

        # Custom user agents
        user_agents_text = self.user_agents_text.toPlainText()
        if user_agents_text:
            self.config.custom_user_agents = [
                line.strip() for line in user_agents_text.split("\n") if line.strip()
            ]
        else:
            self.config.custom_user_agents = []

        # Custom referrers
        referrers_text = self.referrers_text.toPlainText()
        if referrers_text:
            self.config.custom_referrers = [
                line.strip() for line in referrers_text.split("\n") if line.strip()
            ]
        else:
            self.config.custom_referrers = []

        # Retry settings
        self.config.retry_count = self.retry_count_spin.value()
        self.config.retry_backoff = self.retry_backoff_spin.value()

        # Proxy settings
        self.config.use_proxies = self.use_proxies_checkbox.isChecked()

        # Custom proxies
        proxies_text = self.proxies_text.toPlainText()
        if proxies_text:
            self.config.proxies = [
                line.strip() for line in proxies_text.split("\n") if line.strip()
            ]
        else:
            self.config.proxies = []

        # Custom headers
        headers_text = self.headers_text.toPlainText()
        if headers_text:
            headers = {}
            for line in headers_text.split("\n"):
                line = line.strip()
                if line and ":" in line:
                    key, value = line.split(":", 1)
                    headers[key.strip()] = value.strip()
            self.config.custom_headers = headers
        else:
            self.config.custom_headers = {}

        # Multi-threading settings
        self.config.use_multithreading = self.use_multithreading_checkbox.isChecked()
        self.config.max_threads = self.max_threads_spin.value()
        self.config.max_domains_per_thread = self.max_domains_spin.value()

        # URL processing status settings
        self.config.track_processed_urls = self.track_processed_checkbox.isChecked()
        self.config.process_only_unprocessed = self.process_unprocessed_checkbox.isChecked()
        self.config.processed_status_column = self.status_column_edit.text()

    def start_crawling(self):
        """Start the crawling process."""
        # Check if CSV file is selected
        csv_path = self.csv_path_edit.text()
        if not csv_path:
            QMessageBox.warning(self, "Warning", "Please select a CSV file.")
            return

        # Update configuration
        self.update_config_from_ui()

        # Create output directory if it doesn't exist
        os.makedirs(self.config.output_dir, exist_ok=True)

        # Disable start button and enable stop button
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)

        # Reset progress bar
        self.progress_bar.setValue(0)

        # Start crawler thread
        self.crawler_thread = CrawlerThread(self.config, csv_path)
        self.crawler_thread.progress_signal.connect(self.update_progress)
        self.crawler_thread.log_signal.connect(self.log_handler.add_log)
        self.crawler_thread.finished_signal.connect(self.crawling_finished)
        self.crawler_thread.start()

        self.log_handler.add_log("Crawling started...")

    def stop_crawling(self):
        """Stop the crawling process."""
        if self.crawler_thread and self.crawler_thread.isRunning():
            # Ask for confirmation
            reply = QMessageBox.question(
                self, "Confirm Stop",
                "Are you sure you want to stop the crawling process?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )

            if reply == QMessageBox.StandardButton.Yes:
                self.crawler_thread.terminate()
                self.crawler_thread.wait()
                self.log_handler.add_log("Crawling stopped by user.")
                self.crawling_finished(False, "Stopped by user")

    def update_progress(self, current, total):
        """Update the progress bar."""
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(current)

    def crawling_finished(self, success, message):
        """Handle crawling finished event."""
        # Enable start button and disable stop button
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)

        # Log message
        self.log_handler.add_log(message)

        # Show message box
        if success:
            QMessageBox.information(self, "Crawling Completed", message)
        else:
            QMessageBox.warning(self, "Crawling Failed", message)

    def load_ui_from_config(self):
        """Load UI values from configuration."""
        # Basic settings
        self.output_dir_edit.setText(self.config.output_dir)
        self.headless_checkbox.setChecked(self.config.headless)
        self.similarity_spin.setValue(self.config.similarity_threshold)
        self.scroll_spin.setValue(self.config.scroll_count)
        self.delay_spin.setValue(self.config.delay)

        # Profile
        if self.config.profile_name:
            index = self.profile_combo.findText(self.config.profile_name)
            if index >= 0:
                self.profile_combo.setCurrentIndex(index)

        # Custom keywords
        if self.config.custom_keywords:
            self.keywords_text.setPlainText("\n".join(self.config.custom_keywords))

        # Anti-crawler delay settings
        self.random_delay_checkbox.setChecked(self.config.random_delay)
        self.min_delay_spin.setValue(self.config.min_delay)
        self.max_delay_spin.setValue(self.config.max_delay)
        self.rate_limit_checkbox.setChecked(self.config.rate_limit)
        self.requests_per_minute_spin.setValue(self.config.requests_per_minute)

        # Browser emulation settings
        self.rotate_user_agent_checkbox.setChecked(self.config.rotate_user_agent)
        self.use_referrers_checkbox.setChecked(self.config.use_referrers)
        self.emulate_human_behavior_checkbox.setChecked(self.config.emulate_human_behavior)
        self.random_scroll_checkbox.setChecked(self.config.random_scroll)
        self.mouse_movement_checkbox.setChecked(self.config.mouse_movement)

        # Custom user agents
        if self.config.custom_user_agents:
            self.user_agents_text.setPlainText("\n".join(self.config.custom_user_agents))

        # Custom referrers
        if self.config.custom_referrers:
            self.referrers_text.setPlainText("\n".join(self.config.custom_referrers))

        # Retry settings
        self.retry_count_spin.setValue(self.config.retry_count)
        self.retry_backoff_spin.setValue(self.config.retry_backoff)

        # Proxy settings
        self.use_proxies_checkbox.setChecked(self.config.use_proxies)
        if self.config.proxies:
            self.proxies_text.setPlainText("\n".join(self.config.proxies))

        # Custom headers
        if self.config.custom_headers:
            headers_text = "\n".join([f"{key}: {value}" for key, value in self.config.custom_headers.items()])
            self.headers_text.setPlainText(headers_text)

        # Multi-threading settings
        self.use_multithreading_checkbox.setChecked(self.config.use_multithreading)
        self.max_threads_spin.setValue(self.config.max_threads)
        self.max_domains_spin.setValue(self.config.max_domains_per_thread)

        # URL processing status settings
        self.track_processed_checkbox.setChecked(self.config.track_processed_urls)
        self.process_unprocessed_checkbox.setChecked(self.config.process_only_unprocessed)
        self.status_column_edit.setText(self.config.processed_status_column)

    def test_proxy(self):
        """Test proxy functionality and display results."""
        # Update configuration from UI
        self.update_config_from_ui()

        # Check if proxy is enabled
        if not self.config.use_proxies:
            QMessageBox.warning(
                self, "Proxy Test",
                "Proxy is not enabled. Please enable proxy and add at least one proxy server."
            )
            return

        # Check if there are any proxies configured
        if not self.config.proxies:
            QMessageBox.warning(
                self, "Proxy Test",
                "No proxy servers configured. Please add at least one proxy server."
            )
            return

        # Get the first proxy for testing
        proxy_url = self.config.proxies[0]

        # Show a message that we're testing
        self.log_handler.add_log(f"Testing proxy: {proxy_url}")

        # Get current IP first
        success, current_ip_info = get_current_ip()

        if not success:
            QMessageBox.warning(
                self, "Proxy Test",
                f"Failed to get current IP information: {current_ip_info.get('error', 'Unknown error')}"
            )
            return

        # Test the proxy
        proxy_result = test_proxy(proxy_url)

        if proxy_result["success"]:
            # Format the message
            message = (
                f"Proxy test successful!\n\n"
                f"Current IP: {current_ip_info['ip']}\n"
                f"Current Location: {current_ip_info['location']}\n"
                f"Current Latency: {current_ip_info['latency']} ms\n\n"
                f"Proxy IP: {proxy_result['ip']}\n"
                f"Proxy Location: {proxy_result['location']}\n"
                f"Proxy Latency: {proxy_result['latency']} ms"
            )

            # Check if the proxy IP is different from the current IP
            if proxy_result['ip'] == current_ip_info['ip']:
                message += "\n\nWarning: Proxy IP is the same as your current IP. The proxy may not be working correctly."

            QMessageBox.information(self, "Proxy Test Result", message)
            self.log_handler.add_log("Proxy test completed successfully.")
        else:
            QMessageBox.critical(
                self, "Proxy Test Failed",
                f"Failed to test proxy: {proxy_result['error']}\n\n"
                f"Please check your proxy configuration and try again."
            )
            self.log_handler.add_log(f"Proxy test failed: {proxy_result['error']}")

    def closeEvent(self, event):
        """Handle window close event."""
        # Update configuration from UI
        self.update_config_from_ui()

        # Save configuration to file
        save_config(self.config)

        # Stop log handler
        if self.log_handler:
            self.log_handler.stop()

        # Stop crawler thread
        if self.crawler_thread and self.crawler_thread.isRunning():
            self.crawler_thread.terminate()
            self.crawler_thread.wait()

        event.accept()
