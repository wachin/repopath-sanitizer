from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional, Tuple


class GitError(RuntimeError):
    pass


def _run_git(repo: Path, args: List[str], *, check: bool = True) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    # Make output stable and avoid paging
    env["GIT_PAGER"] = "cat"
    env["LC_ALL"] = "C"
    p = subprocess.run(
        ["git", "-C", str(repo), *args],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
        check=False,
    )
    if check and p.returncode != 0:
        raise GitError(p.stderr.decode("utf-8", "replace").strip() or "git command failed")
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
    args = ["mv"]
    if dry_run:
        args.append("-n")
    args.extend(["--", src_rel, dst_rel])
    p = _run_git(repo, args, check=False)
    if p.returncode == 0:
        return True, p.stdout.decode("utf-8", "replace").strip()
    return False, p.stderr.decode("utf-8", "replace").strip()
