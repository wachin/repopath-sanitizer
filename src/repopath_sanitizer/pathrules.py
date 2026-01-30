from __future__ import annotations

import os
import re
import unicodedata
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Set, Tuple

from .constants import DEFAULT_WIN_MAX_PATH

FORBIDDEN_CHARS = set('<>:"/\\|?*')
# Control chars 0-31
CONTROL_RE = re.compile(r"[\x00-\x1F]")

RESERVED_DEVICE_NAMES = {
    "CON","PRN","AUX","NUL",
    *{f"COM{i}" for i in range(1, 10)},
    *{f"LPT{i}" for i in range(1, 10)},
}

MULTISPACE_RE = re.compile(r" {2,}")

SUBSTITUTIONS = {
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

def _is_reserved_device(seg: str) -> bool:
    # Windows checks device names per segment, ignoring extension
    base = seg.split(".")[0]
    return base.upper() in RESERVED_DEVICE_NAMES

def _has_trailing_space_or_period(seg: str) -> bool:
    return seg.endswith(" ") or seg.endswith(".")

def _contains_forbidden(seg: str) -> bool:
    return any(c in FORBIDDEN_CHARS for c in seg) or bool(CONTROL_RE.search(seg))

def _normalize_nfc(s: str) -> str:
    return unicodedata.normalize("NFC", s)

def windows_casefold_path(rel_path: str) -> str:
    # Use casefold for better Unicode case-insensitive comparisons
    return rel_path.casefold()

def nfc_path(rel_path: str) -> str:
    return _normalize_nfc(rel_path)

@dataclass
class ScanConfig:
    max_path: int = DEFAULT_WIN_MAX_PATH
    normalize_unicode_nfc: bool = False
    collapse_spaces: bool = False

@dataclass
class SegmentFix:
    original: str
    fixed: str
    changes: List[str]

def validate_segments(segments: List[str]) -> List[Tuple[str, str]]:
    issues: List[Tuple[str, str]] = []
    for seg in segments:
        if seg in ("", ".", ".."):
            continue
        if _contains_forbidden(seg):
            issues.append(("FORBIDDEN_CHARS", f"Segment contains forbidden Windows characters or control chars: {seg!r}"))
        if _has_trailing_space_or_period(seg):
            issues.append(("TRAILING_SPACE_PERIOD", f"Segment ends with a trailing space or period: {seg!r}"))
        if _is_reserved_device(seg):
            issues.append(("RESERVED_DEVICE", f"Segment is a reserved Windows device name: {seg!r}"))
    return issues

def validate_rel_path(rel_path: str, *, config: Optional[ScanConfig] = None) -> List[Tuple[str, str]]:
    if config is None:
        config = ScanConfig()
    segments = rel_path.split("/")
    issues = validate_segments(segments)
    # length warning is handled at full path stage; include code here for UI
    if len(rel_path) >= config.max_path:
        issues.append(("PATH_TOO_LONG", f"Relative path length {len(rel_path)} exceeds configured limit {config.max_path}."))
    return issues

def fix_segment(seg: str, *, config: ScanConfig) -> SegmentFix:
    out = seg
    changes: List[str] = []

    # Forbidden/control chars substitutions/removals
    for ch, repl in SUBSTITUTIONS.items():
        if ch in out:
            out2 = out.replace(ch, repl)
            if out2 != out:
                out = out2
                changes.append(f"Replace {ch!r} -> {repl!r}")

    if CONTROL_RE.search(out):
        out2 = CONTROL_RE.sub("", out)
        if out2 != out:
            out = out2
            changes.append("Remove control chars (0–31)")

    # Trim trailing space/period
    if _has_trailing_space_or_period(out):
        out2 = out.rstrip(" .")
        if out2 != out:
            out = out2
            changes.append("Trim trailing spaces/periods")

    # Reserved device names
    if _is_reserved_device(out):
        out2 = out + "_"
        out = out2
        changes.append("Append '_' to reserved device name")

    # Collapse multiple spaces (optional)
    if config.collapse_spaces:
        out2 = MULTISPACE_RE.sub(" ", out)
        if out2 != out:
            out = out2
            changes.append("Collapse multiple spaces")

    # Unicode normalize NFC (optional)
    if config.normalize_unicode_nfc:
        out2 = _normalize_nfc(out)
        if out2 != out:
            out = out2
            changes.append("Normalize Unicode to NFC")

    return SegmentFix(original=seg, fixed=out, changes=changes)

def generate_fix_options(rel_path: str, *, config: ScanConfig) -> List[Tuple[str, str, List[str]]]:
    """Return list of (key,label,new_rel_path,warnings) tuples."""
    segments = rel_path.split("/")
    fixed_segments = []
    warnings: List[str] = []
    any_changes = False
    changes_all: List[str] = []
    for seg in segments:
        fx = fix_segment(seg, config=config)
        fixed_segments.append(fx.fixed)
        if fx.fixed != seg:
            any_changes = True
            changes_all.extend([f"{seg!r}: {c}" for c in fx.changes])

    fixed_path = "/".join(fixed_segments)

    opts: List[Tuple[str, str, List[str]]] = []
    if any_changes and fixed_path != rel_path:
        opts.append(("auto", "Auto sanitize (recommended)", fixed_path, changes_all.copy()))
    else:
        opts.append(("none", "No change", rel_path, []))

    # Option: NFC only
    nfc = _normalize_nfc(rel_path)
    if nfc != rel_path:
        opts.append(("nfc", "Normalize Unicode to NFC", nfc, ["Normalize full path to NFC"]))

    # Option: collapse spaces only
    if MULTISPACE_RE.search(rel_path):
        collapsed = MULTISPACE_RE.sub(" ", rel_path)
        if collapsed != rel_path:
            opts.append(("spaces", "Collapse multiple spaces", collapsed, ["Collapse multiple spaces"]))

    return opts

def disambiguate_targets(targets: List[str]) -> Dict[str, str]:
    """If multiple items map to same target (case-insensitive), append suffixes."""
    out: Dict[str, str] = {}
    seen_ci: Dict[str, int] = {}
    for t in targets:
        key = t.casefold()
        if key not in seen_ci:
            seen_ci[key] = 0
            out[t] = t
        else:
            seen_ci[key] += 1
            n = seen_ci[key]
            root, dot, ext = t.rpartition(".")
            if dot:
                base = root
                newt = f"{base}_{n}.{ext}"
            else:
                newt = f"{t}_{n}"
            out[t] = newt
    return out

def shorten_path(rel_path: str, max_len: int) -> str:
    """Simple shortening: truncate long segments keeping suffix hash."""
    if len(rel_path) <= max_len:
        return rel_path
    segs = rel_path.split("/")
    # Try to truncate longest segment(s)
    def h(s: str) -> str:
        import hashlib
        return hashlib.sha1(s.encode("utf-8","surrogateescape")).hexdigest()[:6]
    for i in range(len(segs)):
        if len("/".join(segs)) <= max_len:
            break
        if len(segs[i]) > 12:
            segs[i] = segs[i][:8] + "-" + h(segs[i])
    shortened = "/".join(segs)
    if len(shortened) > max_len:
        # As a last resort, truncate the entire string
        shortened = shortened[: max_len-7] + "-" + h(rel_path)
    return shortened
