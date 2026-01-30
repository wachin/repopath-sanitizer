import unicodedata
import pytest

from repopath_sanitizer.pathrules import ScanConfig, validate_rel_path, generate_fix_options, windows_casefold_path, nfc_path, disambiguate_targets, shorten_path

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
