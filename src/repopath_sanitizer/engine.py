from __future__ import annotations

import os
import time
import unicodedata
from dataclasses import asdict
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set, Tuple

from .diagnostics import log_info
from .gitutils import list_tracked_index_entries, list_untracked_files, list_ignored_files, list_submodules
from .models import ItemType, Issue, FixOption, ScanItem
from .pathrules import (
    ScanConfig,
    validate_rel_path,
    windows_casefold_path,
    nfc_path,
    generate_fix_options,
    shorten_path,
    build_windows_checkout_path,
    estimate_windows_checkout_length,
)

def _dedupe_paths(paths: Iterable[str]) -> List[str]:
    return list(dict.fromkeys(paths))

def _iter_worktree_paths(repo: Path, *, include_ignored: bool) -> Tuple[List[str], List[str], List[str], List[str], Set[str]]:
    tracked_entries = list_tracked_index_entries(repo)
    tracked = [path for _mode, path in tracked_entries]
    tracked_symlinks = {path for mode, path in tracked_entries if mode == "120000"}
    untracked = list_untracked_files(repo)
    ignored: List[str] = []
    if include_ignored:
        ignored = list_ignored_files(repo)
    return tracked, untracked, ignored, _dedupe_paths([*tracked, *untracked, *ignored]), tracked_symlinks

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
    log_info(
        "build_scan start repo=%s include_ignored=%s scan_submodules=%s max_path=%s max_segment=%s",
        repo,
        include_ignored,
        scan_submodules,
        config.max_path,
        config.max_segment,
    )
    tracked_files, untracked_files, ignored_files, files, tracked_symlinks = _iter_worktree_paths(
        repo,
        include_ignored=include_ignored,
    )
    dirs = sorted(_dirs_from_files(files))
    dir_set = set(dirs)
    items: List[ScanItem] = []

    # Build candidate set for collision detection (include files + dirs)
    all_paths = files + dirs

    case_coll = detect_collisions_case_insensitive(all_paths)
    nfc_coll = detect_collisions_nfc(all_paths)

    # Per item validation
    repo_name = repo.name
    for rel in sorted(all_paths, key=lambda s: (s.count("/"), s)):
        # Never touch .git internals (shouldn't appear in git ls-files, but double guard)
        if rel == ".git" or rel.startswith(".git/"):
            continue
        abs_path = str(repo / rel)
        p = repo / rel
        is_dir = rel in dir_set
        is_link = False if is_dir else (rel in tracked_symlinks or p.is_symlink())
        item_type = ItemType.SYMLINK if is_link else (ItemType.FOLDER if is_dir else ItemType.FILE)

        issues_raw = validate_rel_path(rel, config=config)
        issues: List[Issue] = [Issue(code=c, message=m) for c,m in issues_raw]

        checkout_len = estimate_windows_checkout_length(
            rel,
            repo_name=repo_name,
            checkout_root=config.windows_checkout_root,
        )
        if checkout_len >= config.max_path:
            checkout_path = build_windows_checkout_path(
                rel,
                repo_name=repo_name,
                checkout_root=config.windows_checkout_root,
            )
            issues.append(Issue(
                code="CHECKOUT_PATH_TOO_LONG",
                message=(
                    f"Estimated Windows checkout path length {checkout_len} exceeds configured limit "
                    f"{config.max_path}: {checkout_path}"
                ),
            ))

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
        "repo_name": repo_name,
        "tracked_files": tracked_files,
        "untracked_files": untracked_files,
        "ignored_files": ignored_files,
        "derived_dirs": dirs,
        "all_paths": all_paths,
        "collisions": {
            "case_insensitive": case_coll,
            "nfc": nfc_coll,
        }
    }
    if scan_submodules:
        subs = list_submodules(repo)
        meta["submodules"] = [str(p) for p in subs]
        # Caller may run build_scan on submodules separately if desired.
    log_info(
        "build_scan finished repo=%s tracked=%s untracked=%s ignored=%s derived_dirs=%s flagged_items=%s",
        repo,
        len(tracked_files),
        len(untracked_files),
        len(ignored_files),
        len(dirs),
        len(items),
    )
    return items, meta

def _is_git_tracked_item(item: ScanItem) -> bool:
    return item.item_type in (ItemType.FILE, ItemType.SYMLINK)

def _add_numeric_suffix(rel_path: str, n: int) -> str:
    parent, slash, name = rel_path.rpartition("/")
    root, dot, ext = name.rpartition(".")
    if dot and root:
        new_name = f"{root}_{n}.{ext}"
    else:
        new_name = f"{name}_{n}"
    return f"{parent}{slash}{new_name}" if slash else new_name

def plan_renames(items: List[ScanItem], *, config: ScanConfig, existing_paths: Optional[Iterable[str]] = None, tracked_paths: Optional[Iterable[str]] = None) -> Tuple[List[Tuple[str,str]], List[str]]:
    """Return (rename_ops, warnings). rename_ops is list of (src_rel, dst_rel)."""
    log_info("plan_renames start items=%s", len(items))
    selected = [it for it in items if it.selected and it.proposed_fix and it.proposed_fix != it.rel_path]
    warnings: List[str] = []

    skipped_dirs = [it.rel_path for it in selected if it.item_type == ItemType.FOLDER]
    if skipped_dirs:
        warnings.append(
            "Folder-only rename plans are skipped; Git tracks files, so contained tracked files carry directory fixes."
        )

    selected = [it for it in selected if _is_git_tracked_item(it)]
    if tracked_paths is not None:
        tracked_set = set(tracked_paths)
        skipped_untracked = [it.rel_path for it in selected if it.rel_path not in tracked_set]
        if skipped_untracked:
            warnings.append(
                "Untracked files are reported but not renamed automatically. Add them to Git or rename them manually first."
            )
        selected = [it for it in selected if it.rel_path in tracked_set]
    # Shallow first keeps planned output stable while each operation remains file-level.
    selected.sort(key=lambda it: (it.rel_path.count("/"), it.rel_path))

    ops: List[Tuple[str,str]] = []
    existing_ci = {
        p.casefold()
        for p in (existing_paths or [])
        if p not in {it.rel_path for it in selected}
    }
    used_ci: Set[str] = set()
    for it in selected:
        dst = it.proposed_fix
        # Extra guard: avoid .git paths
        if it.rel_path.startswith(".git/") or dst.startswith(".git/") or it.rel_path == ".git" or dst == ".git":
            warnings.append(f"Refusing to rename .git internals: {it.rel_path} -> {dst}")
            continue
        k = dst.casefold()
        suffix = 1
        while k in used_ci:
            dst = _add_numeric_suffix(it.proposed_fix, suffix)
            k = dst.casefold()
            suffix += 1
        if dst != it.proposed_fix:
            warnings.append(f"Collision: {it.proposed_fix!r} adjusted to {dst!r}")
        if k in existing_ci:
            warnings.append(f"Refusing target that already exists in repository: {it.rel_path!r} -> {dst!r}")
            continue
        used_ci.add(k)
        ops.append((it.rel_path, dst))
    log_info("plan_renames finished ops=%s warnings=%s", len(ops), len(warnings))
    return ops, warnings
