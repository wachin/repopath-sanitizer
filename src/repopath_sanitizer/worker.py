from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

from PyQt6.QtCore import QObject, pyqtSignal, QThread

from .engine import build_scan, plan_renames
from .models import ScanItem
from .pathrules import ScanConfig


class ScanWorker(QObject):
    progress = pyqtSignal(int, str)
    finished = pyqtSignal(list, dict)
    cancelled = pyqtSignal(str)
    failed = pyqtSignal(str)

    def __init__(self, repo: Path, config: ScanConfig, include_ignored: bool, scan_submodules: bool):
        super().__init__()
        self.repo = repo
        self.config = config
        self.include_ignored = include_ignored
        self.scan_submodules = scan_submodules
        self._cancel = False

    def cancel(self):
        self._cancel = True

    def run(self):
        try:
            self.progress.emit(0, "Listing repository files…")
            if self._cancel:
                self.cancelled.emit("Scan cancelled.")
                return
            items, meta = build_scan(
                self.repo,
                config=self.config,
                include_ignored=self.include_ignored,
                scan_submodules=self.scan_submodules,
            )
            if self._cancel:
                self.cancelled.emit("Scan cancelled.")
                return
            self.progress.emit(100, f"Found {len(items)} problematic paths.")
            self.finished.emit(items, meta)
        except Exception as e:
            self.failed.emit(str(e))


class ApplyWorker(QObject):
    progress = pyqtSignal(int, str)
    finished = pyqtSignal(list, list, list)  # planned_ops, applied_ops, warnings
    failed = pyqtSignal(str)

    def __init__(self, repo: Path, items: List[ScanItem], config: ScanConfig, dry_run: bool):
        super().__init__()
        self.repo = repo
        self.items = items
        self.config = config
        self.dry_run = dry_run

    def run(self):
        try:
            from .gitutils import git_mv
            planned_ops, warnings = plan_renames(self.items, config=self.config)
            applied: List[tuple[str,str]] = []
            total = max(1, len(planned_ops))
            for i,(src,dst) in enumerate(planned_ops, start=1):
                self.progress.emit(int((i-1)/total*100), f"{'Previewing' if self.dry_run else 'Renaming'}: {src} -> {dst}")
                ok, msg = git_mv(self.repo, src, dst, dry_run=self.dry_run)
                if not ok:
                    warnings.append(f"git mv failed for {src} -> {dst}: {msg}")
                    if not self.dry_run:
                        # Stop on first failure when applying
                        break
                else:
                    if not self.dry_run:
                        applied.append((src,dst))
            self.progress.emit(100, "Done.")
            self.finished.emit(planned_ops, applied, warnings)
        except Exception as e:
            self.failed.emit(str(e))
