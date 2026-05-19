"""
Path validator module for detecting Windows-incompatible paths.
"""

import os
import re
import unicodedata
from enum import Enum
from typing import List, Dict, Tuple, Optional, Set


class IssueCode(Enum):
    """Enumeration of issue codes for Windows path compatibility."""
    FORBIDDEN_CHARS = "FORBIDDEN_CHARS"
    TRAILING_SPACE = "TRAILING_SPACE"
    TRAILING_PERIOD = "TRAILING_PERIOD"
    RESERVED_NAME = "RESERVED_NAME"
    PATH_LENGTH = "PATH_LENGTH"
    CASE_COLLISION = "CASE_COLLISION"
    UNICODE_COLLISION = "UNICODE_COLLISION"


class Issue:
    """Represents a detected issue with a file or folder path."""

    def __init__(self, code: IssueCode, description: str, severity: str = "error"):
        self.code = code
        self.description = description
        self.severity = severity

    def to_dict(self) -> Dict:
        """Convert issue to dictionary for JSON export."""
        return {
            "code": self.code.value,
            "description": self.description,
            "severity": self.severity
        }


class FixStrategy:
    """Represents a fix strategy for a detected issue."""

    def __init__(self, name: str, description: str, apply_func: callable):
        self.name = name
        self.description = description
        self.apply_func = apply_func

    def apply(self, path_segment: str) -> str:
        """Apply the fix to a path segment."""
        return self.apply_func(path_segment)


class PathValidator:
    """Validates paths for Windows compatibility."""

    # Forbidden characters in Windows paths
    FORBIDDEN_CHARS = '<>:"/\|?*'

    # Reserved device names (case-insensitive)
    RESERVED_NAMES = {
        'CON', 'PRN', 'AUX', 'NUL',
        'COM1', 'COM2', 'COM3', 'COM4', 'COM5', 'COM6', 'COM7', 'COM8', 'COM9',
        'LPT1', 'LPT2', 'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9'
    }

    # Default Windows path length limit
    DEFAULT_MAX_PATH_LENGTH = 260

    def __init__(self, max_path_length: int = DEFAULT_MAX_PATH_LENGTH):
        """Initialize the path validator.

        Args:
            max_path_length: Maximum path length for Windows (default: 260)
        """
        self.max_path_length = max_path_length
        self.fix_strategies = self._initialize_fix_strategies()
        self._seen_paths = {}  # For collision detection

    def _initialize_fix_strategies(self) -> Dict[IssueCode, List[FixStrategy]]:
        """Initialize fix strategies for different issue types."""
        strategies = {
            IssueCode.FORBIDDEN_CHARS: [
                FixStrategy(
                    name="Replace with safe alternatives",
                    description='Replace ":" with " -", "?" with "", "*" with "", "<" and ">" with "", "|" with "-", "\" with "-"',
                    apply_func=lambda s: s.replace(':', ' -').replace('?', '').replace('*', '').replace('<>', '').replace('|', '-').replace('\\', '-')
                ),
                FixStrategy(
                    name="Replace all with underscore",
                    description="Replace all forbidden characters with underscore",
                    apply_func=lambda s: re.sub(r'[<>:"/\|?*]', '_', s)
                ),
                FixStrategy(
                    name="Remove all forbidden characters",
                    description="Remove all forbidden characters from the name",
                    apply_func=lambda s: re.sub(r'[<>:"/\|?*]', '', s)
                )
            ],
            IssueCode.TRAILING_SPACE: [
                FixStrategy(
                    name="Trim trailing spaces",
                    description="Remove trailing spaces from the name",
                    apply_func=lambda s: s.rstrip(' ')
                )
            ],
            IssueCode.TRAILING_PERIOD: [
                FixStrategy(
                    name="Trim trailing periods",
                    description="Remove trailing periods from the name",
                    apply_func=lambda s: s.rstrip('.')
                )
            ],
            IssueCode.RESERVED_NAME: [
                FixStrategy(
                    name="Add prefix",
                    description='Add "repo_" prefix to the name',
                    apply_func=lambda s: f"repo_{s}"
                ),
                FixStrategy(
                    name="Add suffix",
                    description='Add "_repo" suffix to the name',
                    apply_func=lambda s: f"{s}_repo"
                ),
                FixStrategy(
                    name="Replace with underscore",
                    description="Replace with underscore",
                    apply_func=lambda s: "_"
                )
            ]
        }
        return strategies

    def validate_path(self, path: str, is_dir: bool = False) -> Tuple[bool, List[Issue]]:
        """Validate a path for Windows compatibility.

        Args:
            path: The path to validate
            is_dir: Whether the path is a directory

        Returns:
            Tuple of (is_valid, list of issues)
        """
        issues = []

        # Split path into segments
        segments = path.split(os.sep)

        for i, segment in enumerate(segments):
            if not segment:  # Skip empty segments (e.g., from leading/trailing separators)
                continue

            # Check for forbidden characters
            if self._has_forbidden_chars(segment):
                issues.append(Issue(
                    code=IssueCode.FORBIDDEN_CHARS,
                    description=f"Segment '{segment}' contains forbidden characters: {self._get_forbidden_chars_in_segment(segment)}"
                ))

            # Check for trailing spaces
            if segment.endswith(' '):
                issues.append(Issue(
                    code=IssueCode.TRAILING_SPACE,
                    description=f"Segment '{segment}' ends with a space"
                ))

            # Check for trailing periods
            if segment.endswith('.'):
                issues.append(Issue(
                    code=IssueCode.TRAILING_PERIOD,
                    description=f"Segment '{segment}' ends with a period"
                ))

            # Check for reserved names
            name_without_ext = os.path.splitext(segment)[0].upper()
            if name_without_ext in self.RESERVED_NAMES:
                issues.append(Issue(
                    code=IssueCode.RESERVED_NAME,
                    description=f"Segment '{segment}' is a reserved Windows device name"
                ))

        # Check path length
        full_path_length = len(path)
        if full_path_length > self.max_path_length:
            issues.append(Issue(
                code=IssueCode.PATH_LENGTH,
                description=f"Path length ({full_path_length}) exceeds Windows limit ({self.max_path_length})"
            ))

        # Check for case-insensitive collisions
        normalized_path = path.lower()
        if normalized_path in self._seen_paths:
            issues.append(Issue(
                code=IssueCode.CASE_COLLISION,
                description=f"Path collides with '{self._seen_paths[normalized_path]}' (case-insensitive)"
            ))
        else:
            self._seen_paths[normalized_path] = path

        # Check for Unicode normalization collisions
        nfc_path = unicodedata.normalize('NFC', path)
        nfd_path = unicodedata.normalize('NFD', path)
        if nfc_path != nfd_path:
            if nfc_path.lower() in self._seen_paths or nfd_path.lower() in self._seen_paths:
                issues.append(Issue(
                    code=IssueCode.UNICODE_COLLISION,
                    description=f"Path may collide due to Unicode normalization (NFC vs NFD)"
                ))

        return (len(issues) == 0, issues)

    def _has_forbidden_chars(self, segment: str) -> bool:
        """Check if a segment contains forbidden characters."""
        return any(char in segment for char in self.FORBIDDEN_CHARS)

    def _get_forbidden_chars_in_segment(self, segment: str) -> str:
        """Get the forbidden characters present in a segment."""
        return ''.join(char for char in segment if char in self.FORBIDDEN_CHARS)

    def get_fix_strategies(self, issue_code: IssueCode) -> List[FixStrategy]:
        """Get fix strategies for a specific issue code."""
        return self.fix_strategies.get(issue_code, [])

    def apply_fix(self, path: str, issue_code: IssueCode, strategy_name: str) -> str:
        """Apply a fix strategy to a path.

        Args:
            path: The path to fix
            issue_code: The issue code to fix
            strategy_name: The name of the fix strategy to apply

        Returns:
            The fixed path
        """
        strategies = self.get_fix_strategies(issue_code)
        for strategy in strategies:
            if strategy.name == strategy_name:
                segments = path.split(os.sep)
                fixed_segments = [strategy.apply(segment) for segment in segments]
                return os.sep.join(fixed_segments)
        return path

    def reset(self):
        """Reset the validator state (e.g., for a new scan)."""
        self._seen_paths = {}
