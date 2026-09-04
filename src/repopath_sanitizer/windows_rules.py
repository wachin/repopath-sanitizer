"""
Reusable Windows path restriction rules.

This module defines every filesystem-level restriction enforced by Windows NTFS
and Win32 that can cause problems when a cross-platform repository is cloned
on Windows.  Any developer can import these constants and functions into their
own project.

Typical usage::

    from repopath_sanitizer.windows_rules import (
        FORBIDDEN_CHARS,
        RESERVED_DEVICE_NAMES,
        MAX_PATH_LENGTH,
        MAX_SEGMENT_LENGTH,
        is_valid_filename,
        sanitize_filename,
    )

    if not is_valid_filename("my:file.txt"):
        safe = sanitize_filename("my:file.txt")
"""

from __future__ import annotations

import re
import unicodedata
from typing import Dict, List, Tuple

# ---------------------------------------------------------------------------
# Path length limits
# ---------------------------------------------------------------------------

#: Maximum total path length on Windows (legacy Win32 MAX_PATH).
MAX_PATH_LENGTH: int = 260

#: Maximum length of a single path segment (file or folder name) on NTFS.
MAX_SEGMENT_LENGTH: int = 255

# ---------------------------------------------------------------------------
# Forbidden characters (cannot appear in a file or folder name on Windows)
# ---------------------------------------------------------------------------

FORBIDDEN_CHARS: frozenset[str] = frozenset('<>:"/\\|?*')

# Control characters 0x00 – 0x1F are also forbidden in NTFS filenames.
_CONTROL_RE = re.compile(r"[\x00-\x1F]")

# ---------------------------------------------------------------------------
# Reserved device names (Windows treats these as special regardless of extension)
# ---------------------------------------------------------------------------

RESERVED_DEVICE_NAMES: frozenset[str] = frozenset({
    "CON", "PRN", "AUX", "NUL",
    *(f"COM{i}" for i in range(1, 10)),
    *(f"LPT{i}" for i in range(1, 10)),
})

# ---------------------------------------------------------------------------
# Trailing whitespace / trailing period rules
# ---------------------------------------------------------------------------

# Windows silently strips trailing spaces and periods from filenames.
# Files that end with a space or period will be unreachable on Windows.
_TRAILING_SPACE_OR_PERIOD_RE = re.compile(r"[ .]+$")

# ---------------------------------------------------------------------------
# Multiple-space collapsing (optional strategy)
# ---------------------------------------------------------------------------

MULTISPACE_RE = re.compile(r" {2,}")

# ---------------------------------------------------------------------------
# Character substitution map  (forbidden_char -> replacement)
# ---------------------------------------------------------------------------

SUBSTITUTIONS: Dict[str, str] = {
    ":": " -",
    "|": "-",
    "\\": "-",
    "/": "-",
    "<": "",
    ">": "",
    '"': "",
    "?": "",
    "*": "",
}

# ---------------------------------------------------------------------------
# Public helper functions
# ---------------------------------------------------------------------------


def contains_forbidden(segment: str) -> bool:
    """Return *True* if *segment* contains any Windows-forbidden character."""
    return any(c in FORBIDDEN_CHARS for c in segment) or bool(_CONTROL_RE.search(segment))


def has_trailing_space_or_period(segment: str) -> bool:
    """Return *True* if *segment* ends with a space or period."""
    return segment.endswith(" ") or segment.endswith(".")


def is_reserved_device_name(segment: str) -> bool:
    """Return *True* if *segment* is a reserved Windows device name."""
    base = segment.split(".")[0]
    return base.upper() in RESERVED_DEVICE_NAMES


def normalize_nfc(text: str) -> str:
    """Normalize *text* to Unicode NFC form."""
    return unicodedata.normalize("NFC", text)


def windows_casefold(text: str) -> str:
    """Casefold a path for Windows case-insensitive comparison."""
    return text.casefold()


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def validate_filename(segment: str) -> List[Tuple[str, str]]:
    """Return a list of ``(issue_code, message)`` tuples for *segment*.

    Empty list means the segment is valid.
    """
    issues: List[Tuple[str, str]] = []
    if segment in ("", ".", ".."):
        return issues
    if contains_forbidden(segment):
        issues.append((
            "FORBIDDEN_CHARS",
            f"Segment contains forbidden Windows characters or control chars: {segment!r}",
        ))
    if has_trailing_space_or_period(segment):
        issues.append((
            "TRAILING_SPACE_PERIOD",
            f"Segment ends with a trailing space or period: {segment!r}",
        ))
    if is_reserved_device_name(segment):
        issues.append((
            "RESERVED_DEVICE",
            f"Segment is a reserved Windows device name: {segment!r}",
        ))
    if len(segment) > MAX_SEGMENT_LENGTH:
        issues.append((
            "SEGMENT_TOO_LONG",
            f"Segment length {len(segment)} exceeds NTFS limit {MAX_SEGMENT_LENGTH}: {segment!r}",
        ))
    return issues


def validate_relative_path(rel_path: str) -> List[Tuple[str, str]]:
    """Validate every segment of *rel_path* and the full path length."""
    issues: List[Tuple[str, str]] = []
    for seg in rel_path.split("/"):
        issues.extend(validate_filename(seg))
    if len(rel_path) >= MAX_PATH_LENGTH:
        issues.append((
            "PATH_TOO_LONG",
            f"Relative path length {len(rel_path)} exceeds limit {MAX_PATH_LENGTH}.",
        ))
    return issues


def is_valid_filename(segment: str) -> bool:
    """Return *True* if *segment* is a valid Windows filename."""
    return len(validate_filename(segment)) == 0


# ---------------------------------------------------------------------------
# Sanitization
# ---------------------------------------------------------------------------


def _hash_suffix(s: str) -> str:
    """Return a short deterministic hash suffix for *s*."""
    import hashlib
    return hashlib.sha1(s.encode("utf-8", "surrogateescape")).hexdigest()[:6]


def sanitize_segment(segment: str, *, max_length: int = MAX_SEGMENT_LENGTH) -> str:
    """Sanitize a single path segment for Windows compatibility.

    Applies substitutions for forbidden characters, removes control characters,
    trims trailing spaces/periods, appends ``_`` to reserved device names,
    and shortens the segment if it exceeds *max_length*.
    """
    out = segment

    # Substitute forbidden / control characters
    for ch, repl in SUBSTITUTIONS.items():
        if ch in out:
            out = out.replace(ch, repl)

    # Remove control characters 0x00-0x1F
    out = _CONTROL_RE.sub("", out)

    # Trim trailing space / period
    out = _TRAILING_SPACE_OR_PERIOD_RE.sub("", out)

    # Reserved device name → append underscore
    if is_reserved_device_name(out):
        out = out + "_"

    # Shorten if too long
    if len(out) > max_length:
        suffix = "-" + _hash_suffix(segment)
        root, dot, ext = out.rpartition(".")
        ext_part = dot + ext if dot and root and len(ext) <= 32 else ""
        base = root if ext_part else out
        keep = max(1, max_length - len(suffix) - len(ext_part))
        shortened_base = base[:keep].rstrip(" .")
        if not shortened_base:
            shortened_base = base[:keep]
        out = f"{shortened_base}{suffix}{ext_part}"[:max_length]

    return out


def sanitize_relative_path(
    rel_path: str,
    *,
    max_path_length: int = MAX_PATH_LENGTH,
    max_segment_length: int = MAX_SEGMENT_LENGTH,
) -> str:
    """Sanitize every segment of *rel_path* for Windows compatibility."""
    segments = rel_path.split("/")
    fixed = [sanitize_segment(seg, max_length=max_segment_length) for seg in segments]
    result = "/".join(fixed)

    # If the full path is still too long, truncate the longest segments
    if len(result) > max_path_length:
        parts = result.split("/")
        def _h(s: str) -> str:
            return _hash_suffix(s)
        for i in range(len(parts)):
            if len("/".join(parts)) <= max_path_length:
                break
            if len(parts[i]) > 12:
                parts[i] = parts[i][:8] + "-" + _h(parts[i])
        result = "/".join(parts)
        if len(result) > max_path_length:
            result = result[: max_path_length - 7] + "-" + _hash_suffix(rel_path)

    return result
