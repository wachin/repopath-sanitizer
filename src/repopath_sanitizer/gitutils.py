from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional, Tuple

from .diagnostics import log_error, log_info


class GitError(RuntimeError):
    pass


def _run_git(repo: Path, args: List[str], *, check: bool = True) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    # Make output stable and avoid paging
    env["GIT_PAGER"] = "cat"
    env["LC_ALL"] = "C"
    cmd = ["git", "-C", str(repo), *args]
    log_info("Running git command: %r", cmd)
    p = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
        check=False,
    )
    stdout = p.stdout.decode("utf-8", "replace").strip()
    stderr = p.stderr.decode("utf-8", "replace").strip()
    if p.returncode == 0:
        log_info("Git command ok rc=%s stdout=%r stderr=%r", p.returncode, stdout, stderr)
    else:
        log_error("Git command failed rc=%s stdout=%r stderr=%r", p.returncode, stdout, stderr)
    if check and p.returncode != 0:
        raise GitError(stderr or "git command failed")
    return p


def is_git_repo(path: Path) -> bool:
    try:
        p = _run_git(path, ["rev-parse", "--is-inside-work-tree"], check=True)
        return p.stdout.strip() == b"true"
    except Exception:
        return False


def repo_root(path: Path) -> Path:
    p = _run_git(path, ["rev-parse", "--show-toplevel"], check=True)
    return Path(p.stdout.decode("utf-8", "replace").strip())


def has_uncommitted_changes(repo: Path) -> bool:
    p = _run_git(repo, ["status", "--porcelain"], check=True)
    return bool(p.stdout.strip())


def stash_push(repo: Path, message: str = "RepoPath Sanitizer auto-stash") -> bool:
    p = _run_git(repo, ["stash", "push", "-u", "-m", message], check=False)
    return p.returncode == 0


def stash_pop(repo: Path) -> bool:
    p = _run_git(repo, ["stash", "pop"], check=False)
    return p.returncode == 0


def list_tracked_files(repo: Path) -> List[str]:
    # -z to safely handle weird names
    p = _run_git(repo, ["ls-files", "-z"], check=True)
    raw = p.stdout
    if not raw:
        return []
    return [s.decode("utf-8", "surrogateescape") for s in raw.split(b"\x00") if s]


def list_tracked_index_entries(repo: Path) -> List[Tuple[str, str]]:
    """Return ``(mode, path)`` pairs from the Git index."""
    p = _run_git(repo, ["ls-files", "-z", "-s"], check=True)
    raw = p.stdout
    if not raw:
        return []

    entries: List[Tuple[str, str]] = []
    for record in raw.split(b"\x00"):
        if not record:
            continue
        meta, sep, path = record.partition(b"\t")
        if not sep:
            continue
        mode = meta.split(maxsplit=1)[0].decode("ascii", "replace")
        entries.append((mode, path.decode("utf-8", "surrogateescape")))
    return entries


def list_untracked_files(repo: Path) -> List[str]:
    # Non-ignored untracked files are useful during development before git add.
    p = _run_git(repo, ["ls-files", "-z", "--others", "--exclude-standard"], check=True)
    raw = p.stdout
    if not raw:
        return []
    return [s.decode("utf-8", "surrogateescape") for s in raw.split(b"\x00") if s]


def list_ignored_files(repo: Path) -> List[str]:
    # Files ignored by .gitignore / exclude, also including untracked
    p = _run_git(repo, ["ls-files", "-z", "--others", "-i", "--exclude-standard"], check=True)
    raw = p.stdout
    if not raw:
        return []
    return [s.decode("utf-8", "surrogateescape") for s in raw.split(b"\x00") if s]


def list_submodules(repo: Path) -> List[Path]:
    # Parse git submodule status; robust even if no .gitmodules present
    p = _run_git(repo, ["submodule", "status", "--recursive"], check=False)
    if p.returncode != 0:
        return []
    subpaths: List[Path] = []
    for line in p.stdout.decode("utf-8", "replace").splitlines():
        # format: " 7b1c... path (....)"
        parts = line.strip().split()
        if len(parts) >= 2:
            subpaths.append(repo / parts[1])
    return subpaths


def git_mv(repo: Path, src_rel: str, dst_rel: str, *, dry_run: bool = False) -> Tuple[bool, str]:
    src_path = repo / src_rel
    dst_path = repo / dst_rel

    if not dry_run:
        dst_path.parent.mkdir(parents=True, exist_ok=True)
        log_info("Ensured destination parent exists for git mv: %s", dst_path.parent)

    args = ["mv"]
    if dry_run:
        args.append("-n")
    args.extend(["--", src_rel, dst_rel])
    p = _run_git(repo, args, check=False)
    if p.returncode == 0:
        if not dry_run:
            _prune_empty_parents(repo, src_path.parent)
        return True, p.stdout.decode("utf-8", "replace").strip()
    return False, p.stderr.decode("utf-8", "replace").strip()


def _prune_empty_parents(repo: Path, path: Path) -> None:
    """Remove empty directories left behind after file-level renames."""
    repo = repo.resolve()
    try:
        current = path.resolve()
    except FileNotFoundError:
        return

    while current != repo:
        try:
            current.rmdir()
            log_info("Removed empty directory after rename: %s", current)
        except OSError:
            break
        current = current.parent
