from __future__ import annotations

import json
from dataclasses import asdict
from typing import Any, Dict, List, Tuple

from .models import ScanItem

def to_json(repo: str, meta: Dict[str, Any], items: List[ScanItem], planned_ops: List[Tuple[str,str]] | None = None, applied_ops: List[Tuple[str,str]] | None = None, extra_warnings: List[str] | None = None) -> Dict[str, Any]:
    return {
        "repo": repo,
        "scan": meta,
        "items": [
            {
                "type": it.item_type.value,
                "current_path": it.rel_path,
                "issues": [asdict(x) for x in it.issues],
                "proposed_fix": it.proposed_fix,
                "chosen_fix_key": it.chosen_fix_key,
                "status": it.status,
                "warnings": it.warnings,
            }
            for it in items
        ],
        "planned_renames": planned_ops or [],
        "applied_renames": applied_ops or [],
        "warnings": extra_warnings or [],
    }

def json_dumps(data: Dict[str, Any]) -> str:
    return json.dumps(data, indent=2, ensure_ascii=False, sort_keys=False)

def to_text_summary(repo: str, planned_ops: List[tuple[str,str]], warnings: List[str]) -> str:
    lines: List[str] = []
    lines.append(f"RepoPath Sanitizer report for: {repo}")
    lines.append("")
    lines.append("Planned renames (git mv):")
    if not planned_ops:
        lines.append("  (none)")
    else:
        for s,d in planned_ops:
            lines.append(f"  - {s}  ->  {d}")
    if warnings:
        lines.append("")
        lines.append("Warnings:")
        for w in warnings:
            lines.append(f"  - {w}")
    lines.append("")
    lines.append("Suggested next steps:")
    lines.append("  1) Run your test suite")
    lines.append("  2) Review `git status` and diff")
    lines.append("  3) Commit (example message):")
    lines.append('     "Sanitize paths for Windows checkout (RepoPath Sanitizer)"')
    lines.append("  4) Push")
    return "\n".join(lines)
