from pathlib import Path
import subprocess

from repopath_sanitizer.engine import build_scan
from repopath_sanitizer.pathrules import (
    ScanConfig,
    build_windows_checkout_path,
    disambiguate_targets,
    estimate_windows_checkout_length,
    generate_fix_options,
    nfc_path,
    shorten_path,
    shorten_segment,
    validate_rel_path,
    windows_casefold_path,
)

def test_forbidden_chars():
    cfg = ScanConfig()
    issues = validate_rel_path("bad:name.txt", config=cfg)
    codes = {c for c,_ in issues}
    assert "FORBIDDEN_CHARS" in codes

def test_trailing_space_period():
    cfg = ScanConfig()
    issues = validate_rel_path("foo./bar ", config=cfg)
    codes = {c for c,_ in issues}
    assert "TRAILING_SPACE_PERIOD" in codes

def test_windows_checkout_breaking_trailing_period_directory():
    cfg = ScanConfig()
    issues = validate_rel_path("Promts/Acerca de.../About Juan y Washington.txt", config=cfg)
    codes = {c for c,_ in issues}
    assert "TRAILING_SPACE_PERIOD" in codes

def test_auto_fix_trims_directory_that_ends_with_periods():
    cfg = ScanConfig()
    opts = generate_fix_options("Promts/Acerca de.../About Juan y Washington.txt", config=cfg)
    auto = [o for o in opts if o[0] == "auto"][0]
    assert auto[2] == "Promts/Acerca de/About Juan y Washington.txt"

def test_reserved_device():
    cfg = ScanConfig()
    issues = validate_rel_path("CON.txt", config=cfg)
    codes = {c for c,_ in issues}
    assert "RESERVED_DEVICE" in codes

def test_fix_options_auto():
    cfg = ScanConfig()
    opts = generate_fix_options("bad:name?.txt", config=cfg)
    keys = [o[0] for o in opts]
    assert "auto" in keys
    auto = [o for o in opts if o[0] == "auto"][0]
    assert ":" not in auto[2]
    assert "?" not in auto[2]

def test_casefold_collision_key():
    assert windows_casefold_path("README.md") == windows_casefold_path("readme.MD")

def test_nfc_path():
    s1 = "e\u0301"  # e + combining accent
    s2 = "é"
    p1 = f"{s1}.txt"
    p2 = f"{s2}.txt"
    assert nfc_path(p1) == nfc_path(p2)

def test_disambiguate_targets():
    targets = ["A.txt", "a.TXT", "b.txt"]
    m = disambiguate_targets(targets)
    assert m["A.txt"] != m["a.TXT"]

def test_shorten_path():
    long = "a/" + ("verylongsegmentname" * 20) + "/b.txt"
    short = shorten_path(long, 120)
    assert len(short) <= 120

def test_long_segment_detected():
    cfg = ScanConfig(max_segment=20)
    issues = validate_rel_path("folder/" + ("a" * 30) + ".txt", config=cfg)
    codes = {c for c,_ in issues}
    assert "SEGMENT_TOO_LONG" in codes

def test_long_segment_auto_fix_keeps_extension():
    cfg = ScanConfig(max_segment=24)
    opts = generate_fix_options(("a" * 40) + ".txt", config=cfg)
    auto = [o for o in opts if o[0] == "auto"][0]
    assert len(auto[2]) <= 24
    assert auto[2].endswith(".txt")

def test_shorten_segment():
    short = shorten_segment(("segment" * 20) + ".md", 32)
    assert len(short) <= 32
    assert short.endswith(".md")

def test_windows_checkout_path_builder():
    path = build_windows_checkout_path(
        "deep/folder/file.txt",
        repo_name="AI-dev",
        checkout_root=r"C:\Users\Juan\Documents",
    )
    assert path == r"C:\Users\Juan\Documents\AI-dev\deep\folder\file.txt"

def test_windows_checkout_length_estimator():
    length = estimate_windows_checkout_length(
        "deep/folder/file.txt",
        repo_name="AI-dev",
        checkout_root=r"C:\Users\Juan\Documents",
    )
    assert length == len(r"C:\Users\Juan\Documents\AI-dev\deep\folder\file.txt")

def test_build_scan_detects_estimated_windows_checkout_path_too_long(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init"], cwd=repo, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    long_rel = "/".join(["nested-folder"] * 12) + "/file.txt"
    file_path = repo / long_rel
    file_path.parent.mkdir(parents=True)
    file_path.write_text("x", encoding="utf-8")

    cfg = ScanConfig(max_path=120, windows_checkout_root=r"C:\Users\Juan\Documents\Projects")
    items, _meta = build_scan(repo, config=cfg)
    target = next(item for item in items if item.rel_path == long_rel)
    codes = {issue.code for issue in target.issues}
    assert "CHECKOUT_PATH_TOO_LONG" in codes
