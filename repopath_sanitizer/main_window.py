"""
Main window module for the RepoPath Sanitizer application.
"""

import os
import subprocess
from typing import List, Optional
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QLineEdit, QFileDialog, QTableWidget, QTableWidgetItem,
    QHeaderView, QSplitter, QTextEdit, QProgressBar, QMessageBox,
    QCheckBox, QComboBox, QDialog, QDialogButtonBox, QTabWidget, QMenu
)
from PyQt6.QtCore import Qt, pyqtSignal, pyqtSlot
from PyQt6.QtGui import QIcon, QAction, QKeySequence

from repopath_sanitizer.git_scanner import GitScanner, ScanResult, ScanStatus
from repopath_sanitizer.report_generator import ReportGenerator
from repopath_sanitizer.path_validator import IssueCode


class RepoPathSanitizerWindow(QMainWindow):
    """Main window for the RepoPath Sanitizer application."""

    def __init__(self):
        """Initialize the main window."""
        super().__init__()

        # Initialize scanner
        self.scanner = GitScanner()
        self.scan_results = []
        self.current_repo_path = ""

        # Setup UI
        self._init_ui()
        self._setup_menu()
        self._connect_signals()

    def _init_ui(self):
        """Initialize the user interface."""
        self.setWindowTitle("RepoPath Sanitizer")
        self.setMinimumSize(1000, 700)

        # Create central widget and main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # Repository selection section
        repo_layout = QHBoxLayout()

        self.repo_label = QLabel("Repository:")
        self.repo_path_edit = QLineEdit()
        self.repo_path_edit.setPlaceholderText("Select a Git repository to scan")
        self.repo_path_edit.setReadOnly(True)

        self.browse_button = QPushButton("Browse...")
        self.browse_button.clicked.connect(self._browse_repository)

        repo_layout.addWidget(self.repo_label)
        repo_layout.addWidget(self.repo_path_edit)
        repo_layout.addWidget(self.browse_button)

        # Scan control section
        scan_layout = QHBoxLayout()

        self.scan_button = QPushButton("Scan Repository")
        self.scan_button.setEnabled(False)
        self.scan_button.clicked.connect(self._scan_repository)

        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.setEnabled(False)
        self.cancel_button.clicked.connect(self._cancel_scan)

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)

        scan_layout.addWidget(self.scan_button)
        scan_layout.addWidget(self.cancel_button)
        scan_layout.addWidget(self.progress_bar)

        # Create splitter for resizable panels
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Results table
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(5)
        self.results_table.setHorizontalHeaderLabels(["Type", "Current Path", "Issue(s)", "Proposed Fix", "Status"])
        self.results_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.results_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.results_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.results_table.itemSelectionChanged.connect(self._update_details_panel)

        # Context menu for opening file manager
        self.results_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.results_table.customContextMenuRequested.connect(self._show_context_menu)

        # Details panel
        details_widget = QWidget()
        details_layout = QVBoxLayout(details_widget)

        self.details_title = QLabel("Details")
        self.details_title.setStyleSheet("font-weight: bold; font-size: 14px;")

        self.details_text = QTextEdit()
        self.details_text.setReadOnly(True)

        self.fix_options_group = QWidget()
        fix_options_layout = QVBoxLayout(self.fix_options_group)

        self.fix_options_label = QLabel("Fix Options:")
        self.fix_options_label.setStyleSheet("font-weight: bold;")

        self.fix_options_combo = QComboBox()
        self.fix_options_combo.currentIndexChanged.connect(self._update_fix_preview)

        self.fix_preview_label = QLabel("Preview:")
        self.fix_preview_label.setStyleSheet("font-weight: bold;")

        self.fix_preview_text = QTextEdit()
        self.fix_preview_text.setReadOnly(True)
        self.fix_preview_text.setMaximumHeight(100)

        self.apply_fix_button = QPushButton("Apply Fix")
        self.apply_fix_button.setEnabled(False)
        self.apply_fix_button.clicked.connect(self._apply_fix)

        fix_options_layout.addWidget(self.fix_options_label)
        fix_options_layout.addWidget(self.fix_options_combo)
        fix_options_layout.addWidget(self.fix_preview_label)
        fix_options_layout.addWidget(self.fix_preview_text)
        fix_options_layout.addWidget(self.apply_fix_button)

        details_layout.addWidget(self.details_title)
        details_layout.addWidget(self.details_text)
        details_layout.addWidget(self.fix_options_group)

        # Add widgets to splitter
        splitter.addWidget(self.results_table)
        splitter.addWidget(details_widget)
        splitter.setSizes([600, 400])

        # Export section
        export_layout = QHBoxLayout()

        self.export_json_button = QPushButton("Export JSON Report")
        self.export_json_button.setEnabled(False)
        self.export_json_button.clicked.connect(self._export_json_report)

        self.export_text_button = QPushButton("Export Text Report")
        self.export_text_button.setEnabled(False)
        self.export_text_button.clicked.connect(self._export_text_report)

        self.copy_commit_msg_button = QPushButton("Copy Commit Message")
        self.copy_commit_msg_button.setEnabled(False)
        self.copy_commit_msg_button.clicked.connect(self._copy_commit_message)

        export_layout.addWidget(self.export_json_button)
        export_layout.addWidget(self.export_text_button)
        export_layout.addWidget(self.copy_commit_msg_button)

        # Add all sections to main layout
        main_layout.addLayout(repo_layout)
        main_layout.addLayout(scan_layout)
        main_layout.addWidget(splitter)
        main_layout.addLayout(export_layout)

    def _setup_menu(self):
        """Setup the application menu bar."""
        menubar = self.menuBar()

        # File menu
        file_menu = menubar.addMenu("&File")

        open_action = QAction("&Open Repository...", self)
        open_action.setShortcut(QKeySequence.StandardKey.Open)
        open_action.triggered.connect(self._browse_repository)
        file_menu.addAction(open_action)

        exit_action = QAction("E&xit", self)
        exit_action.setShortcut(QKeySequence.StandardKey.Quit)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # Tools menu
        tools_menu = menubar.addMenu("&Tools")

        scan_action = QAction("&Scan Repository", self)
        scan_action.setShortcut(QKeySequence("F5"))
        scan_action.triggered.connect(self._scan_repository)
        tools_menu.addAction(scan_action)

        cancel_action = QAction("&Cancel Scan", self)
        cancel_action.setShortcut(QKeySequence("Esc"))
        cancel_action.triggered.connect(self._cancel_scan)
        tools_menu.addAction(cancel_action)

        # Help menu
        help_menu = menubar.addMenu("&Help")

        about_action = QAction("&About", self)
        about_action.triggered.connect(self._show_about_dialog)
        help_menu.addAction(about_action)

    def _connect_signals(self):
        """Connect signals from the scanner to UI updates."""
        self.scanner.scan_started.connect(self._on_scan_started)
        self.scanner.scan_progress.connect(self._on_scan_progress)
        self.scanner.item_found.connect(self._on_item_found)
        self.scanner.scan_completed.connect(self._on_scan_completed)
        self.scanner.scan_cancelled.connect(self._on_scan_cancelled)
        self.scanner.scan_error.connect(self._on_scan_error)

    def _browse_repository(self):
        """Open a file dialog to select a repository."""
        directory = QFileDialog.getExistingDirectory(
            self,
            "Select Git Repository",
            os.path.expanduser("~")
        )

        if directory:
            self.repo_path_edit.setText(directory)
            self.current_repo_path = directory
            self.scanner.set_repo_path(directory)

            # Enable scan button if it's a valid Git repository
            if self.scanner.is_git_repo():
                self.scan_button.setEnabled(True)
                self.statusBar().showMessage(f"Repository: {directory}")
            else:
                self.scan_button.setEnabled(False)
                QMessageBox.warning(
                    self,
                    "Not a Git Repository",
                    f"The selected directory is not a Git repository: {directory}"
                )

    def _scan_repository(self):
        """Scan the selected repository for Windows-incompatible paths."""
        if not self.current_repo_path:
            QMessageBox.warning(
                self,
                "No Repository Selected",
                "Please select a Git repository to scan."
            )
            return

        # Check for uncommitted changes
        if self.scanner.has_uncommitted_changes():
            reply = QMessageBox.question(
                self,
                "Uncommitted Changes",
                "The repository has uncommitted changes. Scanning and fixing paths may cause conflicts.\n\n"
                "Do you want to continue?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )

            if reply == QMessageBox.StandardButton.No:
                return

            # Ask about stashing
            stash_reply = QMessageBox.question(
                self,
                "Stash Changes",
                "Do you want to stash the uncommitted changes before fixing paths?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )

            if stash_reply == QMessageBox.StandardButton.Yes:
                try:
                    subprocess.run(
                        ["git", "stash"],
                        cwd=self.current_repo_path,
                        check=True,
                        capture_output=True
                    )
                    self.statusBar().showMessage("Changes stashed successfully")
                except subprocess.SubprocessError:
                    QMessageBox.warning(
                        self,
                        "Stash Failed",
                        "Failed to stash changes. Please stash manually before fixing paths."
                    )
                    return

        # Clear previous results
        self.results_table.setRowCount(0)
        self.scan_results = []

        # Disable UI elements during scan
        self.scan_button.setEnabled(False)
        self.browse_button.setEnabled(False)
        self.cancel_button.setEnabled(True)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)

        # Start scanning
        self.scanner.scan()

    def _cancel_scan(self):
        """Cancel the ongoing scan."""
        self.scanner.cancel()

    def _on_scan_started(self):
        """Handle scan started signal."""
        self.statusBar().showMessage("Scanning repository...")

    def _on_scan_progress(self, current: int, total: int):
        """Handle scan progress signal."""
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(current)
        self.statusBar().showMessage(f"Scanning: {current}/{total} files")

    def _on_item_found(self, result: ScanResult):
        """Handle item found signal."""
        # Add result to list
        self.scan_results.append(result)

        # Add to table
        row = self.results_table.rowCount()
        self.results_table.insertRow(row)

        # Type
        type_item = QTableWidgetItem("Folder" if result.is_dir else "File")
        type_item.setData(Qt.ItemDataRole.UserRole, result)
        self.results_table.setItem(row, 0, type_item)

        # Current Path
        path_item = QTableWidgetItem(result.path)
        self.results_table.setItem(row, 1, path_item)

        # Issues
        issues_text = "; ".join([issue.code.value for issue in result.issues])
        issues_item = QTableWidgetItem(issues_text)
        self.results_table.setItem(row, 2, issues_item)

        # Proposed Fix
        fix_item = QTableWidgetItem(result.proposed_fix or "")
        self.results_table.setItem(row, 3, fix_item)

        # Status
        status_item = QTableWidgetItem(result.status)
        self.results_table.setItem(row, 4, status_item)

    def _on_scan_completed(self, results: List[ScanResult]):
        """Handle scan completed signal."""
        self.progress_bar.setVisible(False)
        self.cancel_button.setEnabled(False)
        self.scan_button.setEnabled(True)
        self.browse_button.setEnabled(True)

        # Enable export buttons if there are results
        if results:
            self.export_json_button.setEnabled(True)
            self.export_text_button.setEnabled(True)
            self.copy_commit_msg_button.setEnabled(True)
            self.statusBar().showMessage(f"Scan completed: Found {len(results)} issue(s)")
        else:
            self.statusBar().showMessage("Scan completed: No issues found")
            QMessageBox.information(
                self,
                "No Issues Found",
                "No Windows-incompatible paths found in the repository."
            )

    def _on_scan_cancelled(self):
        """Handle scan cancelled signal."""
        self.progress_bar.setVisible(False)
        self.cancel_button.setEnabled(False)
        self.scan_button.setEnabled(True)
        self.browse_button.setEnabled(True)
        self.statusBar().showMessage("Scan cancelled")

    def _on_scan_error(self, error_message: str):
        """Handle scan error signal."""
        self.progress_bar.setVisible(False)
        self.cancel_button.setEnabled(False)
        self.scan_button.setEnabled(True)
        self.browse_button.setEnabled(True)

        QMessageBox.critical(
            self,
            "Scan Error",
            f"An error occurred during scanning: {error_message}"
        )
        self.statusBar().showMessage(f"Error: {error_message}")

    def _update_details_panel(self):
        """Update the details panel with information about the selected item."""
        selected_items = self.results_table.selectedItems()
        if not selected_items:
            self.details_text.clear()
            self.fix_options_combo.clear()
            self.fix_preview_text.clear()
            self.apply_fix_button.setEnabled(False)
            return

        # Get the selected row
        row = selected_items[0].row()
        type_item = self.results_table.item(row, 0)
        result = type_item.data(Qt.ItemDataRole.UserRole)

        # Update details text
        details = f"Type: {'Folder' if result.is_dir else 'File'}\n"
        details += f"Path: {result.path}\n\n"
        details += "Detected Issues:\n"

        for issue in result.issues:
            details += f"  - {issue.code.value}: {issue.description}\n"

        self.details_text.setPlainText(details)

        # Update fix options
        self.fix_options_combo.clear()
        self.fix_options_combo.addItem("Select a fix strategy...")

        # Group issues by type
        issues_by_type = {}
        for issue in result.issues:
            if issue.code not in issues_by_type:
                issues_by_type[issue.code] = []
            issues_by_type[issue.code].append(issue)

        # Add fix options for each issue type
        for issue_code, issues in issues_by_type.items():
            strategies = self.scanner.validator.get_fix_strategies(issue_code)
            for strategy in strategies:
                self.fix_options_combo.addItem(strategy.name, (issue_code, strategy))

        # Update fix preview
        self._update_fix_preview()

        # Enable apply button if there are fix options
        self.apply_fix_button.setEnabled(self.fix_options_combo.count() > 1)

    def _update_fix_preview(self):
        """Update the fix preview based on the selected fix strategy."""
        if self.fix_options_combo.currentIndex() <= 0:
            self.fix_preview_text.clear()
            return

        # Get the selected fix strategy
        issue_code, strategy = self.fix_options_combo.currentData()

        # Get the selected result
        selected_items = self.results_table.selectedItems()
        if not selected_items:
            return

        row = selected_items[0].row()
        type_item = self.results_table.item(row, 0)
        result = type_item.data(Qt.ItemDataRole.UserRole)

        # Apply the fix
        fixed_path = self.scanner.validator.apply_fix(result.path, issue_code, strategy.name)

        # Update preview
        preview = f"Original: {result.path}\n"
        preview += f"Fixed: {fixed_path}\n\n"
        preview += f"Strategy: {strategy.description}"

        self.fix_preview_text.setPlainText(preview)

    def _apply_fix(self):
        """Apply the selected fix to the selected item."""
        if self.fix_options_combo.currentIndex() <= 0:
            return

        # Get the selected fix strategy
        issue_code, strategy = self.fix_options_combo.currentData()

        # Get the selected result
        selected_items = self.results_table.selectedItems()
        if not selected_items:
            return

        row = selected_items[0].row()
        type_item = self.results_table.item(row, 0)
        result = type_item.data(Qt.ItemDataRole.UserRole)

        # Apply the fix
        fixed_path = self.scanner.validator.apply_fix(result.path, issue_code, strategy.name)

        # Confirm before applying
        reply = QMessageBox.question(
            self,
            "Apply Fix",
            f"Are you sure you want to rename:\n\n{result.path}\n\nto:\n\n{fixed_path}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.No:
            return

        # Apply the fix using git mv
        try:
            # Remove any surrounding quotes from paths
            source_path = result.path.strip('"')
            target_path = fixed_path.strip('"')

            subprocess.run(
                ["git", "mv", "--", source_path, target_path],
                cwd=self.current_repo_path,
                check=True,
                capture_output=True,
                text=True
            )

            # Update the result
            result.proposed_fix = fixed_path
            result.status = "fixed"

            # Update the table
            self.results_table.item(row, 3).setText(fixed_path)
            self.results_table.item(row, 4).setText("fixed")

            # Update details panel
            self._update_details_panel()

            self.statusBar().showMessage(f"Successfully renamed: {result.path} -> {fixed_path}")

        except subprocess.CalledProcessError as e:
            error_msg = e.stderr if e.stderr else str(e)
            QMessageBox.critical(
                self,
                "Fix Failed",
                f"Failed to apply fix: {error_msg}"
            )
            self.statusBar().showMessage(f"Failed to apply fix: {result.path}")

    def _show_context_menu(self, position):
        """Show context menu for the results table."""
        selected_items = self.results_table.selectedItems()
        if not selected_items:
            return

        # Get the selected row
        row = selected_items[0].row()
        type_item = self.results_table.item(row, 0)
        result = type_item.data(Qt.ItemDataRole.UserRole)

        # Create context menu
        menu = QMenu(self)

        # Add "Open in File Manager" action
        open_action = QAction("Open in File Manager", self)
        open_action.triggered.connect(lambda: self._open_in_file_manager(result.path))
        menu.addAction(open_action)

        # Show menu
        menu.exec(self.results_table.mapToGlobal(position))

    def _open_in_file_manager(self, path: str):
        """Open the file or folder in the system file manager."""
        try:
            full_path = os.path.join(self.current_repo_path, path)

            if not os.path.exists(full_path):
                QMessageBox.warning(
                    self,
                    "Path Not Found",
                    f"The path does not exist: {full_path}"
                )
                return

            if os.path.isdir(full_path):
                # Open directory in file manager
                subprocess.run(["xdg-open", full_path], check=False)
            else:
                # Open parent directory and select the file
                parent_dir = os.path.dirname(full_path)
                if not os.path.exists(parent_dir):
                    QMessageBox.warning(
                        self,
                        "Parent Directory Not Found",
                        f"The parent directory does not exist: {parent_dir}"
                    )
                    return
                subprocess.run(["xdg-open", parent_dir], check=False)
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error Opening File Manager",
                f"Failed to open file manager: {str(e)}"
            )

    def _export_json_report(self):
        """Export the scan results as a JSON report."""
        if not self.scan_results:
            return

        # Get save file path
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save JSON Report",
            os.path.join(os.path.expanduser("~"), "repopath-sanitizer-report.json"),
            "JSON Files (*.json)"
        )

        if not file_path:
            return

        try:
            # Generate and save report
            report_generator = ReportGenerator(self.current_repo_path, self.scan_results)
            report_generator.save_json(file_path)

            self.statusBar().showMessage(f"JSON report saved to: {file_path}")
            QMessageBox.information(
                self,
                "Report Saved",
                f"JSON report saved to:\n{file_path}"
            )
        except Exception as e:
            QMessageBox.critical(
                self,
                "Export Failed",
                f"Failed to export JSON report: {str(e)}"
            )

    def _export_text_report(self):
        """Export the scan results as a plain text report."""
        if not self.scan_results:
            return

        # Get save file path
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Text Report",
            os.path.join(os.path.expanduser("~"), "repopath-sanitizer-report.txt"),
            "Text Files (*.txt)"
        )

        if not file_path:
            return

        try:
            # Generate and save report
            report_generator = ReportGenerator(self.current_repo_path, self.scan_results)
            report_generator.save_text(file_path)

            self.statusBar().showMessage(f"Text report saved to: {file_path}")
            QMessageBox.information(
                self,
                "Report Saved",
                f"Text report saved to:\n{file_path}"
            )
        except Exception as e:
            QMessageBox.critical(
                self,
                "Export Failed",
                f"Failed to export text report: {str(e)}"
            )

    def _copy_commit_message(self):
        """Copy the commit message to the clipboard."""
        if not self.scan_results:
            return

        try:
            # Generate commit message
            report_generator = ReportGenerator(self.current_repo_path, self.scan_results)
            commit_message = report_generator.to_commit_message()

            # Copy to clipboard
            clipboard = self.clipboard()
            clipboard.setText(commit_message)

            self.statusBar().showMessage("Commit message copied to clipboard")
        except Exception as e:
            QMessageBox.critical(
                self,
                "Copy Failed",
                f"Failed to copy commit message: {str(e)}"
            )

    def _show_about_dialog(self):
        """Show the about dialog."""
        about_text = """
        <h3>RepoPath Sanitizer</h3>
        <p>Version 1.0.0</p>
        <p>A PyQt6 application for detecting Windows-incompatible paths in Git repositories.</p>
        <p>Copyright © 2023 RepoPath Sanitizer Team</p>
        <p>Licensed under the MIT License</p>
        """

        QMessageBox.about(self, "About RepoPath Sanitizer", about_text)
