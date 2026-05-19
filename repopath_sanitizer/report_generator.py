"""
Report generator module for exporting scan results.
"""

import json
import os
from datetime import datetime
from typing import List, Dict, Optional
from dataclasses import asdict

from repopath_sanitizer.git_scanner import ScanResult
from repopath_sanitizer.path_validator import IssueCode


class ReportGenerator:
    """Generates reports from scan results."""

    def __init__(self, repo_path: str, results: List[ScanResult]):
        """Initialize the report generator.

        Args:
            repo_path: Path to the scanned repository
            results: List of scan results
        """
        self.repo_path = repo_path
        self.results = results
        self.timestamp = datetime.now().isoformat()

    def to_json(self, include_warnings: bool = True) -> str:
        """Generate a JSON report.

        Args:
            include_warnings: Whether to include warnings in the report

        Returns:
            JSON report as a string
        """
        report = {
            "repo_path": self.repo_path,
            "scan_timestamp": self.timestamp,
            "summary": self._generate_summary(),
            "issues": [result.to_dict() for result in self.results]
        }

        if include_warnings:
            report["warnings"] = self._generate_warnings()

        return json.dumps(report, indent=2)

    def to_text(self, include_warnings: bool = True) -> str:
        """Generate a plain text report.

        Args:
            include_warnings: Whether to include warnings in the report

        Returns:
            Plain text report as a string
        """
        lines = []

        # Header
        lines.append("RepoPath Sanitizer - Scan Report")
        lines.append("=" * 50)
        lines.append(f"Repository: {self.repo_path}")
        lines.append(f"Scan Date: {self.timestamp}")
        lines.append("")

        # Summary
        summary = self._generate_summary()
        lines.append("Summary:")
        lines.append(f"  Total Issues: {summary['total_issues']}")
        lines.append(f"  Files with Issues: {summary['files_with_issues']}")
        lines.append(f"  Folders with Issues: {summary['folders_with_issues']}")
        lines.append("")

        # Issues by type
        lines.append("Issues by Type:")
        for issue_type, count in summary['issues_by_type'].items():
            lines.append(f"  {issue_type}: {count}")
        lines.append("")

        # Detailed issues
        lines.append("Detailed Issues:")
        lines.append("-" * 50)

        for result in self.results:
            item_type = "Folder" if result.is_dir else "File"
            lines.append(f"{item_type}: {result.path}")

            for issue in result.issues:
                lines.append(f"  - {issue.code.value}: {issue.description}")

            if result.proposed_fix:
                lines.append(f"  Proposed Fix: {result.proposed_fix}")

            lines.append("")

        # Warnings
        if include_warnings and self._generate_warnings():
            lines.append("Warnings:")
            lines.append("-" * 50)

            for warning in self._generate_warnings():
                lines.append(f"  - {warning}")

            lines.append("")

        # Footer
        lines.append("End of Report")

        return "\n".join(lines)

    def to_commit_message(self) -> str:
        """Generate a commit message based on the scan results.

        Returns:
            Commit message as a string
        """
        summary = self._generate_summary()

        lines = []
        lines.append("Fix Windows-incompatible paths")
        lines.append("")

        if summary['total_issues'] == 0:
            lines.append("No Windows-incompatible paths found.")
        else:
            lines.append(f"Fixed {summary['total_issues']} Windows-incompatible path(s):")
            lines.append("")

            # Group by issue type
            issues_by_type = {}
            for result in self.results:
                for issue in result.issues:
                    if issue.code.value not in issues_by_type:
                        issues_by_type[issue.code.value] = []
                    issues_by_type[issue.code.value].append(result.path)

            # Add details for each issue type
            for issue_type, paths in issues_by_type.items():
                lines.append(f"- {issue_type}:")
                for path in paths:
                    lines.append(f"  - {path}")

        return "\n".join(lines)

    def _generate_summary(self) -> Dict:
        """Generate a summary of the scan results.

        Returns:
            Dictionary containing summary information
        """
        total_issues = 0
        files_with_issues = 0
        folders_with_issues = 0
        issues_by_type = {}

        for result in self.results:
            total_issues += len(result.issues)

            if result.is_dir:
                folders_with_issues += 1
            else:
                files_with_issues += 1

            for issue in result.issues:
                issue_type = issue.code.value
                if issue_type not in issues_by_type:
                    issues_by_type[issue_type] = 0
                issues_by_type[issue_type] += 1

        return {
            "total_issues": total_issues,
            "files_with_issues": files_with_issues,
            "folders_with_issues": folders_with_issues,
            "issues_by_type": issues_by_type
        }

    def _generate_warnings(self) -> List[str]:
        """Generate warnings based on the scan results.

        Returns:
            List of warning messages
        """
        warnings = []

        # Check for case collisions
        case_collisions = [r for r in self.results if any(i.code == IssueCode.CASE_COLLISION for i in r.issues)]
        if case_collisions:
            warnings.append(f"Found {len(case_collisions)} case-insensitive path collision(s) that need manual resolution")

        # Check for Unicode collisions
        unicode_collisions = [r for r in self.results if any(i.code == IssueCode.UNICODE_COLLISION for i in r.issues)]
        if unicode_collisions:
            warnings.append(f"Found {len(unicode_collisions)} Unicode normalization collision(s) that may cause issues on Windows")

        # Check for reserved names
        reserved_names = [r for r in self.results if any(i.code == IssueCode.RESERVED_NAME for i in r.issues)]
        if reserved_names:
            warnings.append(f"Found {len(reserved_names)} path(s) using Windows reserved device names")

        return warnings

    def save_json(self, file_path: str, include_warnings: bool = True) -> None:
        """Save the JSON report to a file.

        Report will be saved in the specified directory with a filename based on the repository name.

        Args:
            file_path: Path to save the report
            include_warnings: Whether to include warnings in the report
        """
        # Ensure directory exists
        os.makedirs(os.path.dirname(file_path), exist_ok=True)

        # Write report to file
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(self.to_json(include_warnings=include_warnings))

    def save_text(self, file_path: str, include_warnings: bool = True) -> None:
        """Save the plain text report to a file.

        Args:
            file_path: Path to save the report
            include_warnings: Whether to include warnings in the report
        """
        # Ensure directory exists
        os.makedirs(os.path.dirname(file_path), exist_ok=True)

        # Write report to file
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(self.to_text(include_warnings=include_warnings))

    def save_commit_message(self, file_path: str) -> None:
        """Save the commit message to a file.

        Args:
            file_path: Path to save the commit message
        """
        # Ensure directory exists
        os.makedirs(os.path.dirname(file_path), exist_ok=True)

        # Write commit message to file
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(self.to_commit_message())
