from __future__ import annotations

import os
import time
import unicodedata
from dataclasses import asdict
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set, Tuple

from .gitutils import list_tracked_files, list_ignored_files, list_submodules
from .models import ItemType, Issue, FixOption, ScanItem
from .pathrules import (
    ScanConfig,
    validate_rel_path,
    windows_casefold_path,
    nfc_path,
    generate_fix_options,
    disambiguate_targets,
    shorten_path,
)

def _iter_worktree_paths(repo: Path, *, include_ignored: bool) -> List[str]:
    tracked = list_tracked_files(repo)
    if include_ignored:
        ignored = list_ignored_files(repo)
        # include ignored only if they exist (they might have been deleted)
        return tracked + ignored
    return tracked

def _dirs_from_files(files: List[str]) -> Set[str]:
    dirs: Set[str] = set()
    for f in files:
        parts = f.split("/")
        for i in range(1, len(parts)):
            dirs.add("/".join(parts[:i]))
    return dirs

def detect_collisions_case_insensitive(paths: List[str]) -> Dict[str, List[str]]:
    m: Dict[str, List[str]] = {}
    for p in paths:
        k = windows_casefold_path(p)
        m.setdefault(k, []).append(p)
    return {k:v for k,v in m.items() if len(v) > 1}

def detect_collisions_nfc(paths: List[str]) -> Dict[str, List[str]]:
    m: Dict[str, List[str]] = {}
    for p in paths:
        k = nfc_path(p)
        m.setdefault(k, []).append(p)
    # collisions where multiple distinct originals map to same NFC
    out = {}
    for k,v in m.items():
        uniq = list(dict.fromkeys(v))
        if len(uniq) > 1:
            out[k] = uniq
    return out

def build_scan(repo: Path, *, config: ScanConfig, include_ignored: bool = False, scan_submodules: bool = False) -> Tuple[List[ScanItem], Dict]:
    files = _iter_worktree_paths(repo, include_ignored=include_ignored)
    dirs = sorted(_dirs_from_files(files))
    items: List[ScanItem] = []

    # Build candidate set for collision detection (include files + dirs)
    all_paths = files + dirs

    case_coll = detect_collisions_case_insensitive(all_paths)
    nfc_coll = detect_collisions_nfc(all_paths)

    # Per item validation
    for rel in sorted(all_paths, key=lambda s: (s.count("/"), s)):
        # Never touch .git internals (shouldn't appear in git ls-files, but double guard)
        if rel == ".git" or rel.startswith(".git/"):
            continue
        abs_path = str(repo / rel)
        p = repo / rel
        is_dir = p.is_dir()
        is_link = p.is_symlink()
        item_type = ItemType.SYMLINK if is_link else (ItemType.FOLDER if is_dir else ItemType.FILE)

        issues_raw = validate_rel_path(rel, config=config)
        issues: List[Issue] = [Issue(code=c, message=m) for c,m in issues_raw]

        # collision issues
        k_ci = windows_casefold_path(rel)
        if k_ci in case_coll:
            issues.append(Issue(code="CASE_COLLISION", message=f"Case-insensitive collision group: {case_coll[k_ci]}"))
        k_nfc = nfc_path(rel)
        if k_nfc in nfc_coll:
            issues.append(Issue(code="UNICODE_NFC_COLLISION", message=f"NFC normalization collision group: {nfc_coll[k_nfc]}"))

        # symlink warning
        warnings: List[str] = []
        if is_link:
            warnings.append("Symlink detected. Windows behavior depends on git config and permissions. Consider keeping or replacing.")
            issues.append(Issue(code="SYMLINK", message="Symlink detected (warning)."))

        if issues:
            # Fix options
            opts_raw = generate_fix_options(rel, config=config)
            fix_options: List[FixOption] = []
            for key,label,newp,warns in opts_raw:
                fix_options.append(FixOption(key=key, label=label, preview_path=newp, warnings=warns))
            proposed = fix_options[0].preview_path if fix_options else rel

            # Long path strategy (optional)
            if len(rel) > config.max_path:
                short = shorten_path(rel, config.max_path)
                fix_options.append(FixOption(key="shorten", label=f"Shorten to <= {config.max_path}", preview_path=short, warnings=["Heuristic truncation with hash suffix"]))
                if proposed == rel:
                    proposed = short

            items.append(ScanItem(
                item_type=item_type,
                rel_path=rel,
                abs_path=abs_path,
                issues=issues,
                proposed_fix=proposed,
                fix_options=fix_options,
                chosen_fix_key=fix_options[0].key if fix_options else None,
                warnings=warnings,
                selected=True,
            ))

    # Optionally scan submodules
    meta = {
        "repo": str(repo),
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "config": asdict(config),
        "include_ignored": include_ignored,
        "scan_submodules": scan_submodules,
        "collisions": {
            "case_insensitive": case_coll,
            "nfc": nfc_coll,
        }
    }
    if scan_submodules:
        subs = list_submodules(repo)
        meta["submodules"] = [str(p) for p in subs]
        # Caller may run build_scan on submodules separately if desired.
    return items, meta

def plan_renames(items: List[ScanItem], *, config: ScanConfig) -> Tuple[List[Tuple[str,str]], List[str]]:
    """Return (rename_ops, warnings). rename_ops is list of (src_rel, dst_rel)."""
    selected = [it for it in items if it.selected and it.proposed_fix and it.proposed_fix != it.rel_path]
    # Deepest first to avoid parent/child rename conflicts
    selected.sort(key=lambda it: it.rel_path.count("/"), reverse=True)

    # Detect target collisions (case-insensitive)
    targets = [it.proposed_fix for it in selected]
    disamb = disambiguate_targets(targets)

    ops: List[Tuple[str,str]] = []
    warnings: List[str] = []

    used_ci: Set[str] = set()
    for it in selected:
        dst = disamb.get(it.proposed_fix, it.proposed_fix)
        if dst != it.proposed_fix:
            warnings.append(f"Collision: {it.proposed_fix!r} adjusted to {dst!r}")
        # Extra guard: avoid .git paths
        if it.rel_path.startswith(".git/") or dst.startswith(".git/") or it.rel_path == ".git" or dst == ".git":
            warnings.append(f"Refusing to rename .git internals: {it.rel_path} -> {dst}")
            continue
        k = dst.casefold()
        if k in used_ci:
            # Shouldn't happen due to disambiguate, but guard anyway.
            dst = dst + "_x"
            warnings.append(f"Additional collision guard applied: {it.rel_path!r} -> {dst!r}")
        used_ci.add(k)
        ops.append((it.rel_path, dst))
    return ops, warnings
