from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Dict


class ItemType(str, Enum):
    FILE = "File"
    FOLDER = "Folder"
    SYMLINK = "Symlink"


@dataclass
class Issue:
    code: str
    message: str
    segment: Optional[str] = None


@dataclass
class FixOption:
    key: str
    label: str
    preview_path: str
    warnings: List[str] = field(default_factory=list)


@dataclass
class ScanItem:
    item_type: ItemType
    rel_path: str
    abs_path: str
    issues: List[Issue] = field(default_factory=list)
    proposed_fix: Optional[str] = None
    fix_options: List[FixOption] = field(default_factory=list)
    chosen_fix_key: Optional[str] = None
    status: str = "Pending"
    selected: bool = True
    warnings: List[str] = field(default_factory=list)
