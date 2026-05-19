from repopath_sanitizer.engine import plan_renames
from repopath_sanitizer.models import FixOption, Issue, ItemType, ScanItem
from repopath_sanitizer.pathrules import ScanConfig


def _item(rel_path, proposed_fix, item_type=ItemType.FILE):
    return ScanItem(
        item_type=item_type,
        rel_path=rel_path,
        abs_path=f"/repo/{rel_path}",
        issues=[Issue(code="FORBIDDEN_CHARS", message="bad")],
        proposed_fix=proposed_fix,
        fix_options=[FixOption(key="auto", label="Auto", preview_path=proposed_fix)],
        selected=True,
    )


def test_plan_renames_skips_folder_items():
    items = [
        _item("bad:name", "bad -name", ItemType.FOLDER),
        _item("bad:name/file.txt", "bad -name/file.txt", ItemType.FILE),
    ]

    ops, warnings = plan_renames(items, config=ScanConfig())

    assert ops == [("bad:name/file.txt", "bad -name/file.txt")]
    assert any("Folder-only" in warning for warning in warnings)


def test_plan_renames_disambiguates_duplicate_targets():
    items = [
        _item("a?.txt", "a.txt"),
        _item("a*.txt", "a.txt"),
    ]

    ops, warnings = plan_renames(items, config=ScanConfig())

    assert ops == [("a*.txt", "a.txt"), ("a?.txt", "a_1.txt")]
    assert any("adjusted" in warning for warning in warnings)


def test_plan_renames_refuses_existing_target():
    items = [_item("bad:name.txt", "bad -name.txt")]

    ops, warnings = plan_renames(items, config=ScanConfig(), existing_paths=["bad -name.txt"])

    assert ops == []
    assert any("already exists" in warning for warning in warnings)
