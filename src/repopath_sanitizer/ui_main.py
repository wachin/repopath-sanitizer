from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from PyQt6.QtCore import Qt, QSettings, QSize
from PyQt6.QtGui import QAction, QIcon
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QProgressBar,
    QRadioButton,
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from .constants import APP_NAME, ORG_NAME, DEFAULT_WIN_MAX_PATH
from .gitutils import is_git_repo, repo_root, has_uncommitted_changes, stash_push, stash_pop
from .models import ScanItem
from .pathrules import ScanConfig
from .report import to_json, json_dumps, to_text_summary
from .state import save_last_run, load_last_run
from .worker import ScanWorker, ApplyWorker
from PyQt6.QtCore import QThread


COL_TYPE = 0
COL_PATH = 1
COL_ISSUES = 2
COL_FIX = 3
COL_STATUS = 4


class SettingsDialog(QDialog):
    def __init__(self, parent: QWidget, config: ScanConfig):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.config = config
        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.max_path = QSpinBox()
        self.max_path.setRange(120, 4096)
        self.max_path.setValue(config.max_path)

        self.chk_nfc = QCheckBox("Normalize Unicode to NFC (optional strategy)")
        self.chk_nfc.setChecked(config.normalize_unicode_nfc)
        self.chk_spaces = QCheckBox("Collapse multiple spaces to single space (optional strategy)")
        self.chk_spaces.setChecked(config.collapse_spaces)

        form.addRow("Windows max path length (warn/shorten):", self.max_path)
        form.addRow(self.chk_nfc)
        form.addRow(self.chk_spaces)
        layout.addLayout(form)

        btns = QHBoxLayout()
        ok = QPushButton("OK")
        cancel = QPushButton("Cancel")
        ok.clicked.connect(self.accept)
        cancel.clicked.connect(self.reject)
        btns.addStretch(1)
        btns.addWidget(ok)
        btns.addWidget(cancel)
        layout.addLayout(btns)

    def get_config(self) -> ScanConfig:
        return ScanConfig(
            max_path=int(self.max_path.value()),
            normalize_unicode_nfc=self.chk_nfc.isChecked(),
            collapse_spaces=self.chk_spaces.isChecked(),
        )


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.settings = QSettings(ORG_NAME, "RepoPathSanitizer")
        self.resize(1200, 720)

        self.repo_path = ""
        self.items: List[ScanItem] = []
        self.meta: Dict = {}
        self.config = ScanConfig(max_path=int(self.settings.value("max_path", DEFAULT_WIN_MAX_PATH)))

        self._scan_thread: Optional[QThread] = None
        self._scan_worker: Optional[ScanWorker] = None
        self._apply_thread: Optional[QThread] = None
        self._apply_worker: Optional[ApplyWorker] = None

        self._build_ui()

    def _build_ui(self):
        # Toolbar
        tb = QToolBar("Main")
        tb.setIconSize(QSize(16, 16))
        self.addToolBar(tb)

        act_settings = QAction("Settings", self)
        act_settings.triggered.connect(self._open_settings)
        tb.addAction(act_settings)

        act_undo = QAction("Undo last run", self)
        act_undo.triggered.connect(self._undo_last_run)
        tb.addAction(act_undo)

        # Top controls
        top = QWidget()
        top_l = QHBoxLayout(top)
        self.repo_edit = QLineEdit()
        self.repo_edit.setPlaceholderText("Select a Git repository…")
        self.repo_edit.setReadOnly(True)
        btn_pick = QPushButton("Browse…")
        btn_pick.clicked.connect(self._pick_repo)
        self.btn_scan = QPushButton("Scan")
        self.btn_scan.clicked.connect(self._start_scan)

        self.chk_include_ignored = QCheckBox("Include ignored files")
        self.chk_include_ignored.setChecked(False)
        self.chk_scan_submodules = QCheckBox("Scan submodules (list only)")
        self.chk_scan_submodules.setChecked(False)

        top_l.addWidget(QLabel("Repository:"))
        top_l.addWidget(self.repo_edit, 1)
        top_l.addWidget(btn_pick)
        top_l.addWidget(self.btn_scan)
        top_l.addSpacing(12)
        top_l.addWidget(self.chk_include_ignored)
        top_l.addWidget(self.chk_scan_submodules)

        # Progress row
        pr = QWidget()
        pr_l = QHBoxLayout(pr)
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress_label = QLabel("Idle.")
        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.setEnabled(False)
        self.btn_cancel.clicked.connect(self._cancel_scan)
        pr_l.addWidget(self.progress, 2)
        pr_l.addWidget(self.progress_label, 3)
        pr_l.addWidget(self.btn_cancel)

        # Results + details splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)

        left = QWidget()
        left_l = QVBoxLayout(left)

        self.master_check = QCheckBox("Select All")
        self.master_check.setChecked(True)
        self.master_check.stateChanged.connect(self._toggle_all)
        left_l.addWidget(self.master_check)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["Type", "Current Path", "Issue(s)", "Proposed Fix", "Status"])
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.itemSelectionChanged.connect(self._on_selection_changed)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setColumnWidth(0, 90)
        self.table.setColumnWidth(1, 360)
        self.table.setColumnWidth(2, 280)
        self.table.setColumnWidth(3, 280)
        self.table.setColumnWidth(4, 120)
        left_l.addWidget(self.table, 1)

        splitter.addWidget(left)

        # Details panel
        right = QWidget()
        right_l = QVBoxLayout(right)

        self.details_title = QLabel("Details")
        self.details_title.setStyleSheet("font-weight: bold; font-size: 16px;")
        right_l.addWidget(self.details_title)

        self.details_issues = QTextEdit()
        self.details_issues.setReadOnly(True)
        self.details_issues.setPlaceholderText("Select an item to see details…")

        right_l.addWidget(QLabel("Detected issues:"))
        right_l.addWidget(self.details_issues, 2)

        right_l.addWidget(QLabel("Fix strategy:"))
        self.fix_combo = QComboBox()
        self.fix_combo.currentIndexChanged.connect(self._on_fix_changed)
        right_l.addWidget(self.fix_combo)

        self.preview_label = QLabel("Preview: —")
        self.preview_label.setWordWrap(True)
        right_l.addWidget(self.preview_label)

        right_l.addWidget(QLabel("Warnings / collisions:"))
        self.details_warn = QTextEdit()
        self.details_warn.setReadOnly(True)
        right_l.addWidget(self.details_warn, 1)

        splitter.addWidget(right)
        splitter.setSizes([800, 400])

        # Bottom action buttons
        bottom = QWidget()
        bottom_l = QHBoxLayout(bottom)
        self.btn_apply = QPushButton("Apply Fixes")
        self.btn_apply.clicked.connect(self._apply_fixes)
        self.btn_export = QPushButton("Export Report")
        self.btn_export.clicked.connect(self._export_report)
        self.btn_rescan = QPushButton("Rescan")
        self.btn_rescan.clicked.connect(self._start_scan)
        bottom_l.addWidget(self.btn_apply)
        bottom_l.addWidget(self.btn_export)
        bottom_l.addWidget(self.btn_rescan)
        bottom_l.addStretch(1)

        # Main layout
        central = QWidget()
        main_l = QVBoxLayout(central)
        main_l.addWidget(top)
        main_l.addWidget(pr)
        main_l.addWidget(splitter, 1)
        main_l.addWidget(bottom)
        self.setCentralWidget(central)

        self._update_buttons()

    def _open_settings(self):
        dlg = SettingsDialog(self, self.config)
        if dlg.exec():
            self.config = dlg.get_config()
            self.settings.setValue("max_path", self.config.max_path)

    def _pick_repo(self):
        d = QFileDialog.getExistingDirectory(self, "Select repository folder", str(Path.home()))
        if not d:
            return
        p = Path(d)
        if not is_git_repo(p):
            QMessageBox.warning(self, "Not a Git repository", "The selected folder is not inside a Git working tree.")
            return
        root = repo_root(p)
        self.repo_path = str(root)
        self.repo_edit.setText(self.repo_path)
        self.settings.setValue("last_repo", self.repo_path)
        self._update_buttons()

    def _cancel_scan(self):
        if self._scan_worker:
            self._scan_worker.cancel()
        self.btn_cancel.setEnabled(False)

    def _start_scan(self):
        if not self.repo_path:
            last = self.settings.value("last_repo", "")
            if last:
                self.repo_path = str(last)
                self.repo_edit.setText(self.repo_path)
        if not self.repo_path:
            QMessageBox.information(self, "Select repository", "Please select a repository first.")
            return

        repo = Path(self.repo_path)
        if not is_git_repo(repo):
            QMessageBox.warning(self, "Invalid repository", "Repository is not a valid Git working tree.")
            return

        self.progress.setValue(0)
        self.progress_label.setText("Starting scan…")
        self.btn_cancel.setEnabled(True)
        self.btn_scan.setEnabled(False)

        self._scan_thread = QThread()
        self._scan_worker = ScanWorker(
            repo=repo,
            config=self.config,
            include_ignored=self.chk_include_ignored.isChecked(),
            scan_submodules=self.chk_scan_submodules.isChecked(),
        )
        self._scan_worker.moveToThread(self._scan_thread)
        self._scan_thread.started.connect(self._scan_worker.run)
        self._scan_worker.progress.connect(self._on_progress)
        self._scan_worker.finished.connect(self._on_scan_finished)
        self._scan_worker.cancelled.connect(self._on_scan_cancelled)
        self._scan_worker.failed.connect(self._on_scan_failed)
        self._scan_thread.start()

    def _on_progress(self, pct: int, msg: str):
        self.progress.setValue(pct)
        self.progress_label.setText(msg)

    def _on_scan_finished(self, items: list, meta: dict):
        self.items = items
        self.meta = meta
        self.progress_label.setText(f"Scan complete. {len(items)} item(s) need attention.")
        self.btn_cancel.setEnabled(False)
        self.btn_scan.setEnabled(True)
        if self._scan_thread:
            self._scan_thread.quit()
            self._scan_thread.wait()
        self._populate_table()
        self._update_buttons()

    def _on_scan_cancelled(self, msg: str):
        self.progress_label.setText(msg)
        self.btn_cancel.setEnabled(False)
        self.btn_scan.setEnabled(True)
        if self._scan_thread:
            self._scan_thread.quit()
            self._scan_thread.wait()
        self._update_buttons()

    def _on_scan_failed(self, err: str):
        QMessageBox.critical(self, "Scan failed", err)
        self.btn_cancel.setEnabled(False)
        self.btn_scan.setEnabled(True)
        if self._scan_thread:
            self._scan_thread.quit()
            self._scan_thread.wait()
        self._update_buttons()

    def _populate_table(self):
        self.table.setRowCount(0)
        for it in self.items:
            row = self.table.rowCount()
            self.table.insertRow(row)

            # Checkbox in Type column
            chk = QCheckBox(it.item_type.value)
            chk.setChecked(it.selected)
            chk.stateChanged.connect(lambda s, r=row: self._on_row_checked(r, s))
            self.table.setCellWidget(row, COL_TYPE, chk)

            self.table.setItem(row, COL_PATH, QTableWidgetItem(it.rel_path))
            issues_txt = "; ".join([i.code for i in it.issues])
            self.table.setItem(row, COL_ISSUES, QTableWidgetItem(issues_txt))
            self.table.setItem(row, COL_FIX, QTableWidgetItem(it.proposed_fix or ""))
            self.table.setItem(row, COL_STATUS, QTableWidgetItem(it.status))

        if self.items:
            self.table.selectRow(0)

    def _on_row_checked(self, row: int, state: int):
        if 0 <= row < len(self.items):
            self.items[row].selected = (state == Qt.CheckState.Checked.value)
        self._sync_master_checkbox()
        self._update_buttons()

    def _toggle_all(self, state: int):
        checked = (state == Qt.CheckState.Checked.value)
        for r, it in enumerate(self.items):
            it.selected = checked
            w = self.table.cellWidget(r, COL_TYPE)
            if isinstance(w, QCheckBox):
                w.blockSignals(True)
                w.setChecked(checked)
                w.blockSignals(False)
        self._update_buttons()

    def _sync_master_checkbox(self):
        if not self.items:
            self.master_check.setChecked(False)
            return
        all_on = all(it.selected for it in self.items)
        any_on = any(it.selected for it in self.items)
        self.master_check.blockSignals(True)
        self.master_check.setTristate(True)
        if all_on:
            self.master_check.setCheckState(Qt.CheckState.Checked)
        elif any_on:
            self.master_check.setCheckState(Qt.CheckState.PartiallyChecked)
        else:
            self.master_check.setCheckState(Qt.CheckState.Unchecked)
        self.master_check.blockSignals(False)

    def _on_selection_changed(self):
        row = self.table.currentRow()
        if row < 0 or row >= len(self.items):
            return
        it = self.items[row]
        self._show_details(it)

    def _show_details(self, it: ScanItem):
        self.details_title.setText(f"Details: {it.rel_path}")
        lines = []
        for iss in it.issues:
            lines.append(f"- [{iss.code}] {iss.message}")
        self.details_issues.setPlainText("\n".join(lines) if lines else "(no issues)")
        self.fix_combo.blockSignals(True)
        self.fix_combo.clear()
        for opt in it.fix_options:
            self.fix_combo.addItem(opt.label, opt.key)
        # Choose current
        idx = 0
        if it.chosen_fix_key:
            for i in range(self.fix_combo.count()):
                if self.fix_combo.itemData(i) == it.chosen_fix_key:
                    idx = i
                    break
        self.fix_combo.setCurrentIndex(idx)
        self.fix_combo.blockSignals(False)

        self.preview_label.setText(f"Preview: {it.proposed_fix or it.rel_path}")
        warn_lines = []
        warn_lines.extend(it.warnings)
        for opt in it.fix_options:
            if opt.key == it.chosen_fix_key and opt.warnings:
                warn_lines.extend(opt.warnings)
        self.details_warn.setPlainText("\n".join(f"- {w}" for w in warn_lines) if warn_lines else "(none)")

    def _on_fix_changed(self, idx: int):
        row = self.table.currentRow()
        if row < 0 or row >= len(self.items):
            return
        it = self.items[row]
        key = self.fix_combo.itemData(idx)
        it.chosen_fix_key = key
        # Update proposed fix to match chosen option
        for opt in it.fix_options:
            if opt.key == key:
                it.proposed_fix = opt.preview_path
                break
        self.table.item(row, COL_FIX).setText(it.proposed_fix or "")
        self._show_details(it)

    def _apply_fixes(self):
        if not self.items:
            QMessageBox.information(self, "Nothing to apply", "No scan results available.")
            return
        repo = Path(self.repo_path)

        # Safety: uncommitted changes
        if has_uncommitted_changes(repo):
            msg = QMessageBox(self)
            msg.setWindowTitle("Uncommitted changes detected")
            msg.setText("This repository has uncommitted changes. Applying renames may complicate your working tree.")
            msg.setInformativeText("Choose what to do:")
            btn_abort = msg.addButton("Abort", QMessageBox.ButtonRole.RejectRole)
            btn_continue = msg.addButton("Continue anyway", QMessageBox.ButtonRole.AcceptRole)
            btn_stash = msg.addButton("Auto-stash (recommended)", QMessageBox.ButtonRole.ActionRole)
            msg.setDefaultButton(btn_stash)
            msg.exec()
            clicked = msg.clickedButton()
            if clicked == btn_abort:
                return
            do_stash = (clicked == btn_stash)
        else:
            do_stash = False

        # Preview plan (dry run) and confirm
        planned_ops, applied_ops, warnings = self._run_apply(dry_run=True)
        if not planned_ops:
            QMessageBox.information(self, "No changes", "No renames are planned for the selected items.")
            return

        preview_txt = "\n".join([f"{s} -> {d}" for s,d in planned_ops[:200]])
        if len(planned_ops) > 200:
            preview_txt += f"\n… and {len(planned_ops)-200} more"
        confirm = QMessageBox.question(
            self,
            "Confirm apply",
            f"This will apply {len(planned_ops)} git mv operations.\n\nPreview:\n{preview_txt}\n\nProceed?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return

        stashed = False
        if do_stash:
            stashed = stash_push(repo)
            if not stashed:
                QMessageBox.warning(self, "Stash failed", "Could not stash changes. Aborting for safety.")
                return

        planned_ops, applied_ops, warnings = self._run_apply(dry_run=False)

        # Save rollback plan (reverse mapping)
        if applied_ops:
            save_last_run(self.repo_path, applied_ops, {"timestamp": self.meta.get("timestamp"), "planned": planned_ops, "warnings": warnings})

        if stashed:
            # Try to restore stash
            stash_pop(repo)

        # Show result and next steps
        QMessageBox.information(
            self,
            "Apply completed",
            f"Applied {len(applied_ops)} rename(s).\n\nNext steps:\n- Run tests\n- Review git status/diff\n- Commit and push",
        )
        # Mark statuses
        applied_set = set(applied_ops)
        for it in self.items:
            if (it.rel_path, it.proposed_fix) in applied_set:
                it.status = "Renamed"
        self._populate_table()

    def _run_apply(self, dry_run: bool):
        repo = Path(self.repo_path)

        # Run in current thread for simplicity (fast enough for typical rename counts).
        # If you expect many thousands of renames, this can be moved to QThread.
        from .engine import plan_renames
        from .gitutils import git_mv

        planned_ops, warnings = plan_renames(self.items, config=self.config)
        applied_ops: List[Tuple[str,str]] = []
        for src,dst in planned_ops:
            ok, msg = git_mv(repo, src, dst, dry_run=dry_run)
            if not ok:
                warnings.append(f"git mv failed for {src} -> {dst}: {msg}")
                if not dry_run:
                    break
            else:
                if not dry_run:
                    applied_ops.append((src,dst))
        return planned_ops, applied_ops, warnings

    def _export_report(self):
        if not self.items:
            QMessageBox.information(self, "Nothing to export", "Run a scan first.")
            return
        repo = self.repo_path
        from .engine import plan_renames
        planned_ops, warnings = plan_renames(self.items, config=self.config)
        data = to_json(repo, self.meta, self.items, planned_ops=planned_ops, applied_ops=[], extra_warnings=warnings)
        js = json_dumps(data)
        txt = to_text_summary(repo, planned_ops, warnings)

        outdir = QFileDialog.getExistingDirectory(self, "Select export folder", str(Path.home()))
        if not outdir:
            return
        outdir = str(outdir)
        json_path = Path(outdir) / "repopath_sanitizer_report.json"
        txt_path = Path(outdir) / "repopath_sanitizer_report.txt"
        json_path.write_text(js, encoding="utf-8")
        txt_path.write_text(txt, encoding="utf-8")

        QMessageBox.information(self, "Export complete", f"Saved:\n- {json_path}\n- {txt_path}")

    def _undo_last_run(self):
        if not self.repo_path:
            QMessageBox.information(self, "Select repository", "Select a repository first.")
            return
        last = load_last_run(self.repo_path)
        if not last:
            QMessageBox.information(self, "Nothing to undo", "No previous run found for this repository.")
            return
        mapping = last.get("mapping", [])
        if not mapping:
            QMessageBox.information(self, "Nothing to undo", "Stored mapping is empty.")
            return

        preview = "\n".join([f"{s} <- {d}" for s,d in mapping[:200]])
        if len(mapping) > 200:
            preview += f"\n… and {len(mapping)-200} more"
        confirm = QMessageBox.question(
            self,
            "Confirm undo",
            f"This will attempt to undo the last applied renames using git mv in reverse order.\n\nPreview:\n{preview}\n\nProceed?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return

        repo = Path(self.repo_path)
        from .gitutils import git_mv
        # Reverse order, and swap
        reversed_ops = list(reversed(mapping))
        failures = []
        for src,dst in reversed_ops:
            ok, msg = git_mv(repo, dst, src, dry_run=False)
            if not ok:
                failures.append(f"{dst} -> {src}: {msg}")
        if failures:
            QMessageBox.warning(self, "Undo completed with errors", "Some operations failed:\n" + "\n".join(failures[:20]))
        else:
            QMessageBox.information(self, "Undo completed", "Successfully reverted the last run's renames.")

    def _update_buttons(self):
        has_repo = bool(self.repo_path)
        has_items = bool(self.items)
        self.btn_scan.setEnabled(has_repo)
        self.btn_apply.setEnabled(has_items and any(it.selected for it in self.items))
        self.btn_export.setEnabled(has_items)
        self.btn_rescan.setEnabled(has_repo)
