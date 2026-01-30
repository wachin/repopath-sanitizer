from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Tuple

from .constants import APP_ID

def _state_dir() -> Path:
    xdg = os.environ.get("XDG_STATE_HOME")
    if xdg:
        d = Path(xdg)
    else:
        d = Path.home() / ".local" / "state"
    d = d / APP_ID
    d.mkdir(parents=True, exist_ok=True)
    return d

def _repo_key(repo: str) -> str:
    import hashlib
    return hashlib.sha1(repo.encode("utf-8","surrogateescape")).hexdigest()[:12]

def save_last_run(repo: str, mapping: List[Tuple[str,str]], meta: Dict[str, Any]) -> Path:
    d = _state_dir()
    p = d / f"last_run_{_repo_key(repo)}.json"
    p.write_text(json.dumps({"repo": repo, "mapping": mapping, "meta": meta}, indent=2, ensure_ascii=False), encoding="utf-8")
    return p

def load_last_run(repo: str) -> Dict[str, Any] | None:
    p = _state_dir() / f"last_run_{_repo_key(repo)}.json"
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None
