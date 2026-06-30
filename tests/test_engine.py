import subprocess

from repopath_sanitizer.engine import build_scan, plan_renames
from repopath_sanitizer.gitutils import git_mv
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


def test_build_scan_reports_untracked_trailing_space_file(tmp_path):
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    bad_path = tmp_path / "bad-name "
    bad_path.write_text("content", encoding="utf-8")

    items, meta = build_scan(tmp_path, config=ScanConfig())

    assert "bad-name " in meta["untracked_files"]
    assert any(item.rel_path == "bad-name " for item in items)
    assert any(
        issue.code == "TRAILING_SPACE_PERIOD"
        for item in items
        if item.rel_path == "bad-name "
        for issue in item.issues
    )


def test_plan_renames_skips_untracked_files_when_tracked_paths_given():
    items = [_item("bad-name ", "bad-name")]

    ops, warnings = plan_renames(items, config=ScanConfig(), tracked_paths=[])

    assert ops == []
    assert any("Untracked files" in warning for warning in warnings)


def test_build_scan_reports_long_folder_and_file_names(tmp_path):
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    long_folder = "folder-" + ("a" * 30)
    long_file = "file-" + ("b" * 30) + ".txt"
    nested = tmp_path / long_folder
    nested.mkdir()
    (nested / long_file).write_text("content", encoding="utf-8")

    items, meta = build_scan(tmp_path, config=ScanConfig(max_segment=20))

    assert f"{long_folder}/{long_file}" in meta["untracked_files"]
    assert any(
        item.rel_path == long_folder and any(issue.code == "SEGMENT_TOO_LONG" for issue in item.issues)
        for item in items
    )
    file_item = next(item for item in items if item.rel_path == f"{long_folder}/{long_file}")
    assert any(issue.code == "SEGMENT_TOO_LONG" for issue in file_item.issues)
    assert all(len(segment) <= 20 for segment in file_item.proposed_fix.split("/"))


def test_build_scan_marks_tracked_symlinks_without_statting_directories(tmp_path):
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    target = tmp_path / "target.txt"
    target.write_text("content", encoding="utf-8")
    link = tmp_path / "link.txt"
    link.symlink_to(target.name)
    subprocess.run(["git", "add", "target.txt", "link.txt"], cwd=tmp_path, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    items, meta = build_scan(tmp_path, config=ScanConfig())

    assert "link.txt" in meta["tracked_files"]
    assert any(item.rel_path == "link.txt" and item.item_type == ItemType.SYMLINK for item in items)


def test_git_mv_creates_missing_target_dirs_and_prunes_empty_source_dirs(tmp_path):
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    source_dir = tmp_path / "Promts" / "Acerca de..."
    source_dir.mkdir(parents=True)
    source_file = source_dir / "About.txt"
    source_file.write_text("content", encoding="utf-8")
    subprocess.run(["git", "add", "Promts/Acerca de.../About.txt"], cwd=tmp_path, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    ok, message = git_mv(tmp_path, "Promts/Acerca de.../About.txt", "Promts/Acerca de/About.txt", dry_run=False)

    assert ok, message
    assert not source_file.exists()
    assert not source_dir.exists()
    assert (tmp_path / "Promts" / "Acerca de" / "About.txt").exists()
