from __future__ import annotations

import argparse
from pathlib import Path

from .engine import build_scan, plan_renames
from .gitutils import is_git_repo, repo_root
from .pathrules import ScanConfig
from .report import to_json, json_dumps, to_text_summary

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="repopath-sanitizer", description="RepoPath Sanitizer (GUI + CLI)")
    p.add_argument("--cli", action="store_true", help="Run in CLI mode (no GUI)")
    p.add_argument("--repo", type=str, default=".", help="Repository path (default: .)")
    p.add_argument("--include-ignored", action="store_true", help="Include .gitignore ignored files")
    p.add_argument("--scan-submodules", action="store_true", help="List submodules (does not recursively scan in CLI)")
    p.add_argument("--max-path", type=int, default=260, help="Windows max path length threshold")
    p.add_argument("--nfc", action="store_true", help="Enable Unicode NFC normalization strategy")
    p.add_argument("--collapse-spaces", action="store_true", help="Collapse multiple spaces strategy")
    p.add_argument("--json", type=str, default="", help="Write JSON report to this path")
    p.add_argument("--text", type=str, default="", help="Write plain text summary to this path")
    return p

def run_cli(args: argparse.Namespace) -> int:
    repo = Path(args.repo)
    if not is_git_repo(repo):
        print("Not a Git working tree:", repo)
        return 2
    repo = repo_root(repo)

    cfg = ScanConfig(max_path=args.max_path, normalize_unicode_nfc=args.nfc, collapse_spaces=args.collapse_spaces)
    items, meta = build_scan(repo, config=cfg, include_ignored=args.include_ignored, scan_submodules=args.scan_submodules)
    planned_ops, warnings = plan_renames(items, config=cfg)
    data = to_json(str(repo), meta, items, planned_ops=planned_ops, applied_ops=[], extra_warnings=warnings)
    js = json_dumps(data)
    txt = to_text_summary(str(repo), planned_ops, warnings)

    if args.json:
        Path(args.json).write_text(js, encoding="utf-8")
    else:
        print(js)

    if args.text:
        Path(args.text).write_text(txt, encoding="utf-8")
    return 0
