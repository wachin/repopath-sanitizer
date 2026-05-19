"""
Git scanner module for scanning Git repositories.
"""

import os
import subprocess
from typing import List, Dict, Optional, Callable
from dataclasses import dataclass
from enum import Enum
from PyQt6.QtCore import QObject, pyqtSignal, QThread

from repopath_sanitizer.path_validator import PathValidator, Issue, IssueCode


class ScanStatus(Enum):
    """Enumeration of scan statuses."""
    IDLE = "idle"
    SCANNING = "scanning"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    ERROR = "error"


@dataclass
class ScanResult:
    """Represents a scan result for a file or folder."""
    path: str
    is_dir: bool
    issues: List[Issue]
    proposed_fix: Optional[str] = None
    status: str = "pending"  # pending, fixed, skipped

    def to_dict(self) -> Dict:
        """Convert scan result to dictionary for JSON export."""
        return {
            "path": self.path,
            "is_dir": self.is_dir,
            "issues": [issue.to_dict() for issue in self.issues],
            "proposed_fix": self.proposed_fix,
            "status": self.status
        }


class GitScanner(QObject):
    """Scanner for Git repositories."""

    # Signals for UI updates
    scan_started = pyqtSignal()
    scan_progress = pyqtSignal(int, int)  # current, total
    item_found = pyqtSignal(object)  # ScanResult
    scan_completed = pyqtSignal(list)  # List[ScanResult]
    scan_cancelled = pyqtSignal()
    scan_error = pyqtSignal(str)

    def __init__(self, repo_path: str = "", max_path_length: int = 260):
        """Initialize the Git scanner.

        Args:
            repo_path: Path to the Git repository
            max_path_length: Maximum path length for Windows (default: 260)
        """
        super().__init__()
        self.repo_path = repo_path
        self.max_path_length = max_path_length
        self.validator = PathValidator(max_path_length=max_path_length)
        self._status = ScanStatus.IDLE
        self._should_cancel = False
        self._scan_thread = None

    def set_repo_path(self, path: str):
        """Set the repository path to scan.

        Args:
            path: Path to the Git repository
        """
        self.repo_path = path

    def set_max_path_length(self, length: int):
        """Set the maximum path length for Windows.

        Args:
            length: Maximum path length
        """
        self.max_path_length = length
        self.validator = PathValidator(max_path_length=length)

    def status(self) -> ScanStatus:
        """Get the current scan status.

        Returns:
            Current scan status
        """
        return self._status

    def is_git_repo(self, path: str = None) -> bool:
        """Check if a directory is a Git repository.

        Git repositories are identified by the presence of a .git directory or file.

        Args:
            path: Path to check (uses repo_path if not provided)

        Returns:
            True if the directory is a Git repository, False otherwise
        """
        path = path or self.repo_path
        if not path or not os.path.isdir(path):
            return False

        git_dir = os.path.join(path, '.git')
        return os.path.exists(git_dir)

    def has_uncommitted_changes(self) -> bool:
        """Check if the repository has uncommitted changes.

        Returns:
            True if there are uncommitted changes, False otherwise
        """
        if not self.is_git_repo():
            return False

        try:
            result = subprocess.run(
                ['git', 'status', '--porcelain'],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=False
            )
            return bool(result.stdout.strip())
        except (subprocess.SubprocessError, FileNotFoundError):
            return False

    def scan(self, incremental_callback: Optional[Callable] = None):
        """Scan the Git repository for Windows-incompatible paths.

        Args:
            incremental_callback: Optional callback for incremental updates
        """
        if not self.is_git_repo():
            self.scan_error.emit(f"'{self.repo_path}' is not a Git repository")
            self._status = ScanStatus.ERROR
            return

        self._status = ScanStatus.SCANNING
        self._should_cancel = False
        self.validator.reset()

        # Start scanning in a separate thread to avoid freezing the UI
        self._scan_thread = ScanThread(
            repo_path=self.repo_path,
            validator=self.validator,
            max_path_length=self.max_path_length
        )

        # Connect signals
        self._scan_thread.progress.connect(self.scan_progress)
        self._scan_thread.item_found.connect(self.item_found)
        self._scan_thread.completed.connect(self.scan_completed)
        self._scan_thread.error.connect(self.scan_error)

        # Start the thread
        self._scan_thread.start()

    def cancel(self):
        """Cancel the ongoing scan."""
        if self._status == ScanStatus.SCANNING and self._scan_thread:
            self._should_cancel = True
            self._scan_thread.cancel()
            self._status = ScanStatus.CANCELLED


class ScanThread(QThread):
    """Worker thread for scanning Git repositories."""

    # Signals
    progress = pyqtSignal(int, int)  # current, total
    item_found = pyqtSignal(object)  # ScanResult
    completed = pyqtSignal(list)  # List[ScanResult]
    error = pyqtSignal(str)

    def __init__(self, repo_path: str, validator: PathValidator, max_path_length: int = 260):
        """Initialize the scan thread.

        Args:
            repo_path: Path to the Git repository
            validator: Path validator instance
            max_path_length: Maximum path length for Windows
        """
        super().__init__()
        self.repo_path = repo_path
        self.validator = validator
        self.max_path_length = max_path_length
        self._should_cancel = False
        self.results = []

    def run(self):
        """Run the scan in a separate thread."""
        try:
            # Get all tracked files from Git
            files = self._get_tracked_files()
            total = len(files)

            if total == 0:
                self.completed.emit([])
                return

            # Scan each file
            for i, file_path in enumerate(files):
                if self._should_cancel:
                    break

                # Make the path relative to the repository root
                rel_path = os.path.relpath(file_path, self.repo_path)

                # Check if it's a directory (by checking if it has an extension)
                is_dir = not os.path.splitext(file_path)[1] and os.path.isdir(file_path)

                # Validate the path
                is_valid, issues = self.validator.validate_path(rel_path, is_dir)

                if not is_valid:
                    # Create a scan result
                    result = ScanResult(
                        path=rel_path,
                        is_dir=is_dir,
                        issues=issues
                    )

                    # Generate a proposed fix
                    result.proposed_fix = self._generate_proposed_fix(rel_path, issues)

                    # Add to results
                    self.results.append(result)

                    # Emit signal
                    self.item_found.emit(result)

                # Update progress
                self.progress.emit(i + 1, total)

            # Emit completion signal
            self.completed.emit(self.results)

        except Exception as e:
            self.error.emit(str(e))

    def cancel(self):
        """Cancel the scan."""
        self._should_cancel = True

    def _get_tracked_files(self) -> List[str]:
        """Get all tracked files from the Git repository.

        Returns:
            List of absolute file paths
        """
        try:
            # Use git ls-files to get all tracked files
            result = subprocess.run(
                ['git', 'ls-files'],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=True
            )

            # Convert to absolute paths
            files = []
            for line in result.stdout.splitlines():
                if line:  # Skip empty lines
                    files.append(os.path.join(self.repo_path, line))

            return files

        except subprocess.SubprocessError as e:
            raise Exception(f"Failed to get tracked files: {str(e)}")
        except FileNotFoundError:
            raise Exception("Git is not installed or not in PATH")

    def _generate_proposed_fix(self, path: str, issues: List[Issue]) -> str:
        """Generate a proposed fix for a path with issues.

        Args:
            path: The path to fix
            issues: List of issues with the path

        Returns:
            A proposed fixed path
        """
        fixed_path = path
        segments = path.split(os.sep)
        fixed_segments = []

        for segment in segments:
            fixed_segment = segment

            # Apply fixes for each issue
            for issue in issues:
                if issue.code == IssueCode.FORBIDDEN_CHARS:
                    # Replace forbidden characters with safe alternatives
                    fixed_segment = fixed_segment.replace(':', ' -').replace('?', '').replace('*', '').replace('<>', '').replace('|', '-').replace('\\', '-')
                elif issue.code == IssueCode.TRAILING_SPACE:
                    fixed_segment = fixed_segment.rstrip(' ')
                elif issue.code == IssueCode.TRAILING_PERIOD:
                    fixed_segment = fixed_segment.rstrip('.')
                elif issue.code == IssueCode.RESERVED_NAME:
                    # Add a prefix to reserved names
                    name_without_ext = os.path.splitext(fixed_segment)[0]
                    ext = os.path.splitext(fixed_segment)[1]
                    fixed_segment = f"repo_{name_without_ext}{ext}"

            fixed_segments.append(fixed_segment)

        return os.sep.join(fixed_segments)
