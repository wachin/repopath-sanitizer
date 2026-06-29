# RepoPath Sanitizer - User Guide

## Overview

RepoPath Sanitizer is a PyQt6 desktop application that scans Git repositories and detects paths that would fail to checkout on Windows. It helps you fix repository paths on Linux so they can be cloned and checked out on Windows without errors.

## Getting Started

### Launching the Application

You can launch RepoPath Sanitizer from your application menu or from the command line:

```bash
repopath-sanitizer
```

### Selecting a Repository

1. Click the "Browse..." button to select a Git repository.
2. Navigate to the repository directory and select it.
3. The application will verify that it's a valid Git repository.
4. Once a valid repository is selected, the "Scan Repository" button will be enabled.

## Scanning a Repository

### Starting a Scan

1. Select a Git repository (see above).
2. Click the "Scan Repository" button.
3. The application will scan tracked files and normal untracked files in the repository.
4. A progress bar will show the scan progress.

If you want more realistic Windows length warnings, open **Settings** and adjust the estimated Windows checkout root. This lets the tool calculate the final checkout path using the folder where the repository would actually be cloned on Windows.

### Cancelling a Scan

To cancel an ongoing scan, click the "Cancel" button.

## Understanding the Results

### Results Table

The results table shows all files and folders with Windows-incompatible paths:

- **Type**: Indicates whether the item is a file or folder.
- **Current Path**: The current path of the file or folder.
- **Issue(s)**: A summary of the issues detected.
- **Proposed Fix**: A suggested fix for the issues.
- **Status**: The current status of the fix (pending, fixed, skipped).

For path-length issues, the table now distinguishes three different cases:

- **Relative path too long**: the repository-relative path is already too long.
- **File/folder name too long**: one individual segment exceeds the configured per-name limit.
- **Estimated Windows checkout path too long**: the final path would become too long only after adding the Windows clone base folder and repository name.

### Details Panel

When you select an item in the results table, the details panel on the right shows:

1. **Detected Issues**: A detailed description of each issue.
2. **Fix Options**: Multiple fix strategies you can choose from.
3. **Preview**: A preview of what the path would look like after applying the fix.
4. **Warnings**: Any warnings about collisions, reserved names, or path length.

For the three path-length cases above, the details panel also explains why each one matters, so you can tell whether the problem is the whole relative path, a single long segment, or the final Windows checkout destination.

## Fixing Issues

### Applying Fixes

1. Select an item in the results table.
2. In the details panel, choose a fix strategy from the dropdown.
3. Review the preview of the proposed fix.
4. Click the "Apply Fix" button to apply the fix.
5. The status will update to "fixed".

### Manual Fixes

Some issues may require manual intervention:

1. **Case-Insensitive Collisions**: These require you to manually rename files to avoid conflicts.
2. **Unicode Normalization Collisions**: These may require you to normalize filenames to NFC.

### Fixing Multiple Issues

You can fix issues one by one or select multiple items and apply fixes to all of them at once.

## Exporting Reports

### JSON Report

To export a JSON report:

1. Click the "Export JSON Report" button.
2. Choose a location to save the report.
3. The report will include all issues, proposed fixes, and warnings.

### Text Report

To export a plain text report:

1. Click the "Export Text Report" button.
2. Choose a location to save the report.
3. The report will include a summary and detailed information about all issues.

### Commit Message

To copy a commit message summarizing the fixes:

1. Click the "Copy Commit Message" button.
2. The commit message will be copied to your clipboard.
3. You can paste it into your Git commit message.

## Using the File Manager

To open a file or folder in your file manager:

1. Right-click on an item in the results table.
2. Select "Open in File Manager" from the context menu.
3. The app will try the system file manager first, including `exo-open --launch FileManager` on Xfce-based systems, then fall back to the desktop default opener.

To copy a problematic path:

1. Right-click on an item in the results table.
2. Select "Copy Path" to copy the absolute path.
3. Select "Copy Relative Path" to copy the repository-relative path.

## Untracked and Ignored Files

Normal untracked files are reported because they often reveal problems before you commit them. Ignored files are skipped unless you enable "Include ignored files".

Automatic fixes use `git mv`, so untracked files are reported but not renamed automatically. Add them to Git or rename them manually first.

## Uncommitted Changes

If the repository has uncommitted changes, the application will warn you before scanning:

1. You can choose to continue anyway.
2. You can abort the scan.
3. You can choose to stash the changes automatically.

## Git Pre-Commit Hook

If you want to stop bad paths before they even enter the history, this repository includes a shared hook at `.githooks/pre-commit`.

Enable it with:

```bash
git config core.hooksPath .githooks
chmod +x .githooks/pre-commit
```

The hook checks staged paths before each commit and blocks the commit if it finds:

- forbidden Windows characters
- trailing spaces or periods
- reserved device names
- file or folder names that are too long
- repository-relative paths that are too long
- estimated final Windows checkout paths that are too long

You can tune the limits with environment variables:

```bash
export REPOPATH_SANITIZER_MAX_PATH=260
export REPOPATH_SANITIZER_MAX_SEGMENT=255
export REPOPATH_SANITIZER_CHECKOUT_ROOT='C:\Users\Juan\Documents\Projects'
```

## Next Steps After Fixing

After applying fixes to your repository:

1. Review the changes to ensure they're correct.
2. Run your tests to make sure nothing is broken.
3. Commit the changes with the suggested commit message.
4. Push the changes to your remote repository.

## Windows Compatibility Rules

The application checks for the following Windows compatibility issues:

### Forbidden Characters

Windows forbids the following characters in file and folder names:
- `< > : " / \ | ? *`
- NUL and control characters (0-31)

### Trailing Spaces and Periods

Windows forbids trailing spaces and periods in file and folder names.

Real example already covered by the tool:

- `Promts/Acerca de.../About Juan y Washington.txt`

In that path, the failure is caused by the folder `Acerca de...`. Even though Linux accepts that name, Windows rejects it because the segment ends with periods. In Git for Windows this usually appears as an `invalid path` error during clone or checkout.

### Reserved Device Names

Windows reserves the following device names (case-insensitive, with or without extension):
- CON, PRN, AUX, NUL
- COM1..COM9
- LPT1..LPT9

### Path and Name Length

Windows has a maximum path length of 260 characters by default. Individual file or folder names are commonly limited to 255 characters. The application reports both total path length issues and individual name segments that exceed the configured limit.

The tool now also estimates the final Windows checkout path, not just the repository-relative path. That means it can warn about repositories that become too long only after adding:

- the Windows destination folder
- the repository name
- many nested folders
- long file names

### Case-Insensitive Collisions

Windows is case-insensitive, so files with names that differ only by case (e.g., README.md vs readme.md) will collide.

### Unicode Normalization

Different operating systems may use different Unicode normalization forms (NFC vs NFD), which can cause issues when cloning repositories across platforms.

## Fix Strategies

The application suggests multiple fix strategies for different issues:

### Forbidden Characters

1. **Replace with safe alternatives**: Replaces forbidden characters with safe alternatives.
2. **Replace all with underscore**: Replaces all forbidden characters with underscore.
3. **Remove all forbidden characters**: Removes all forbidden characters from the name.

### Trailing Spaces and Periods

1. **Trim trailing spaces/periods**: Removes trailing spaces or periods from the name.

For the previous example, the recommended sanitized result is:

- Original: `Promts/Acerca de.../About Juan y Washington.txt`
- Fixed: `Promts/Acerca de/About Juan y Washington.txt`

### Reserved Names

1. **Add prefix**: Adds a prefix to the name (e.g., "repo_").
2. **Add suffix**: Adds a suffix to the name (e.g., "_repo").
3. **Replace with underscore**: Replaces the name with an underscore.

## CLI Mode

For automated scanning, you can use the CLI mode:

```bash
repopath-sanitizer --cli --repo /path/to/repository
```

With output options:

```bash
repopath-sanitizer --cli --repo /path/to/repository --json report.json --text report.txt
```

To estimate Windows checkout failures more accurately for deep folders and long names, you can also set the expected Windows clone base folder:

```bash
repopath-sanitizer --cli --repo /path/to/repository --checkout-root "C:\Users\Juan\Documents\Projects"
```

## Troubleshooting

### Scan Fails

If the scan fails:

1. Verify that the selected directory is a valid Git repository.
2. Ensure you have read permissions for all files in the repository.
3. Check that Git is installed and accessible.

### Fixes Not Applied

If fixes are not applied:

1. Verify that you have write permissions for the files.
2. Check if the files are locked by another application.
3. Ensure there are no uncommitted changes that might conflict.

### Application Won't Start

If the application won't start:

1. Verify that PyQt6 is installed correctly.
2. Check that all dependencies are installed.
3. Try running from the command line to see error messages.

## Support

For issues, questions, or contributions, please visit the project repository:
https://github.com/yourusername/repopath-sanitizer
