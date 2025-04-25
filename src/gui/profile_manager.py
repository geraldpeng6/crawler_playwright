#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Profile manager dialog for the web interaction element crawler.

This module contains the dialog for managing browser profiles.
"""

import os
import shutil
from pathlib import Path

from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QListWidget, QMessageBox, QInputDialog,
    QDialogButtonBox
)

from src.crawler.crawler import InteractionCrawler
from src.utils.config import Config
from src.utils.logger import get_logger

logger = get_logger()

class ProfileManagerDialog(QDialog):
    """Dialog for managing browser profiles."""
    
    def __init__(self, parent=None):
        """Initialize the profile manager dialog."""
        super().__init__(parent)
        
        self.config = Config()
        self.crawler = InteractionCrawler(self.config)
        
        self.init_ui()
        self.load_profiles()
        
    def init_ui(self):
        """Initialize the user interface."""
        # Set window properties
        self.setWindowTitle("Browser Profile Manager")
        self.setMinimumSize(500, 400)
        
        # Create layout
        layout = QVBoxLayout(self)
        
        # Profile list
        list_label = QLabel("Available Profiles:")
        self.profile_list = QListWidget()
        self.profile_list.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        
        # Buttons
        buttons_layout = QHBoxLayout()
        
        self.create_button = QPushButton("Create Profile")
        self.create_button.clicked.connect(self.create_profile)
        
        self.delete_button = QPushButton("Delete Profile")
        self.delete_button.clicked.connect(self.delete_profile)
        
        self.open_button = QPushButton("Open Browser")
        self.open_button.clicked.connect(self.open_browser)
        
        buttons_layout.addWidget(self.create_button)
        buttons_layout.addWidget(self.delete_button)
        buttons_layout.addWidget(self.open_button)
        
        # Dialog buttons
        dialog_buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Close
        )
        dialog_buttons.rejected.connect(self.reject)
        
        # Add widgets to layout
        layout.addWidget(list_label)
        layout.addWidget(self.profile_list)
        layout.addLayout(buttons_layout)
        layout.addWidget(dialog_buttons)
        
    def load_profiles(self):
        """Load profiles from disk."""
        self.profile_list.clear()
        
        profiles = self.crawler.get_profiles()
        for profile in profiles:
            self.profile_list.addItem(profile)
            
    def create_profile(self):
        """Create a new browser profile."""
        # Get profile name
        name, ok = QInputDialog.getText(
            self, "Create Profile", "Enter profile name:"
        )
        
        if ok and name:
            # Check if profile already exists
            if name in self.crawler.get_profiles():
                QMessageBox.warning(
                    self, "Warning", f"Profile '{name}' already exists."
                )
                return
                
            # Create profile
            try:
                profile_path = self.crawler.create_profile(name)
                
                # Show message
                QMessageBox.information(
                    self, "Profile Created", 
                    f"Profile '{name}' created successfully.\n\n"
                    "Please log in to the websites you want to crawl in the opened browser.\n"
                    "When you're done, close the browser and click OK."
                )
                
                # Reload profiles
                self.load_profiles()
                
            except Exception as e:
                QMessageBox.critical(
                    self, "Error", f"Error creating profile: {str(e)}"
                )
                
    def delete_profile(self):
        """Delete the selected browser profile."""
        # Get selected profile
        selected_items = self.profile_list.selectedItems()
        if not selected_items:
            QMessageBox.warning(
                self, "Warning", "Please select a profile to delete."
            )
            return
            
        profile_name = selected_items[0].text()
        
        # Confirm deletion
        reply = QMessageBox.question(
            self, "Confirm Deletion", 
            f"Are you sure you want to delete profile '{profile_name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # Delete profile
            try:
                profile_path = os.path.join("profiles", profile_name)
                shutil.rmtree(profile_path)
                
                # Reload profiles
                self.load_profiles()
                
                # Show message
                QMessageBox.information(
                    self, "Profile Deleted", 
                    f"Profile '{profile_name}' deleted successfully."
                )
                
            except Exception as e:
                QMessageBox.critical(
                    self, "Error", f"Error deleting profile: {str(e)}"
                )
                
    def open_browser(self):
        """Open browser with the selected profile."""
        # Get selected profile
        selected_items = self.profile_list.selectedItems()
        if not selected_items:
            QMessageBox.warning(
                self, "Warning", "Please select a profile to open."
            )
            return
            
        profile_name = selected_items[0].text()
        
        # Open browser
        try:
            # Close existing browser if open
            if hasattr(self, 'crawler') and self.crawler:
                self.crawler.close_browser()
                
            # Set profile
            self.config.profile_name = profile_name
            
            # Create new crawler
            self.crawler = InteractionCrawler(self.config)
            
            # Open browser
            self.crawler.start_browser()
            
            # Open a blank page
            context = self.crawler.context
            page = context.new_page()
            page.goto("about:blank")
            
            # Show message
            QMessageBox.information(
                self, "Browser Opened", 
                f"Browser opened with profile '{profile_name}'.\n\n"
                "Please log in to the websites you want to crawl.\n"
                "When you're done, close the browser and click OK."
            )
            
            # Close browser
            self.crawler.close_browser()
            
        except Exception as e:
            QMessageBox.critical(
                self, "Error", f"Error opening browser: {str(e)}"
            )
