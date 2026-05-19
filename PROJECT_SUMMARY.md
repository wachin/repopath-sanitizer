# RepoPath Sanitizer - Project Summary

## Overview

RepoPath Sanitizer is a PyQt6 desktop application that scans Git repositories and detects paths that would fail to checkout on Windows. It helps developers fix repository paths on Linux so they can be cloned and checked out on Windows without errors.

## Project Structure

```
repopath-sanitizer/
├── debian/                          # Debian packaging files
│   ├── changelog                    # Package changelog
│   ├── control                      # Package metadata
│   ├── rules                        # Build rules
│   ├── repopath-sanitizer.install   # Installation instructions
│   ├── copyright                    # Copyright information
│   └── repopath-sanitizer.desktop   # Desktop entry file
├── data/                            # Application data
│   └── icons/                       # Application icons
│       └── repopath-sanitizer.svg   # Main application icon
├── src/repopath_sanitizer/          # Maintained Python package
│   ├── __init__.py                  # Package initialization
│   ├── __main__.py                  # Entry point for the application
│   ├── ui_main.py                   # Main GUI window
│   ├── engine.py                    # Scan and rename planning logic
│   ├── pathrules.py                 # Windows compatibility rules
│   ├── gitutils.py                  # Git operations
│   ├── worker.py                    # Background tasks
│   ├── report.py                    # JSON/text reports
│   ├── state.py                     # Undo state
│   └── cli.py                       # CLI mode
├── repopath_sanitizer/              # Development shim for repo-root execution
├── usr/                             # Installation paths
│   └── bin/
│       └── repopath-sanitizer       # Launcher script
├── requirements.txt                 # Python dependencies
├── pyproject.toml                   # Project configuration
├── README.md                        # Project documentation
├── DEVELOPMENT.md                   # Development documentation
├── USER_GUIDE.md                    # User guide
└── PROJECT_SUMMARY.md               # This file
```

## Key Components

### 1. Path Rules (pathrules.py)

The path rules module is responsible for detecting Windows-incompatible paths. It checks for:

- Forbidden characters in path segments
- Trailing spaces and periods
- Reserved device names
- Path length issues
- Case-insensitive collisions
- Unicode normalization pitfalls

It also provides fix strategies for each type of issue.

### 2. Scan Engine (engine.py)

The scan engine handles scanning Git repositories for Windows-incompatible paths. It:

- Uses `git ls-files` to get all tracked files
- Validates each path using the path rules
- Provides progress updates during scanning
- Supports cancellation of ongoing scans
- Runs in a separate thread to avoid freezing the UI

### 3. Report Generator (report.py)

The report generator creates reports from scan results in multiple formats:

- JSON format for programmatic consumption
- Plain text format for human reading
- Commit messages for Git commits

### 4. Main Window (ui_main.py)

The main window provides the GUI for the application. It includes:

- Repository selection (folder picker)
- Scan button with progress indicator and cancel
- Results table with columns for Type, Current Path, Issue(s), Proposed Fix, and Status
- Details panel showing detected issues, fix options, and previews
- Export functionality for reports

### 5. Entry Point (__main__.py)

The entry point handles both GUI and CLI modes. It:

- Parses command line arguments
- Launches the GUI in normal mode
- Runs the scanner and outputs reports in CLI mode

## Windows Compatibility Rules

The application checks for the following Windows compatibility issues:

### A. Forbidden Characters

Windows forbids the following characters in file and folder names:
- `< > : " / \ | ? *`
- NUL and control characters (0-31)

### B. Trailing Spaces and Periods

Windows forbids trailing spaces and periods in file and folder names.

### C. Reserved Device Names

Windows reserves the following device names (case-insensitive, with or without extension):
- CON, PRN, AUX, NUL
- COM1..COM9
- LPT1..LPT9

### D. Path Length

Windows has a maximum path length of 260 characters (by default). The application warns if paths exceed this limit.

### E. Case-Insensitive Collisions

Windows is case-insensitive, so files with names that differ only by case (e.g., README.md vs readme.md) will collide.

### F. Unicode Normalization

Different operating systems may use different Unicode normalization forms (NFC vs NFD), which can cause issues when cloning repositories across platforms.

## Fix Strategies

The application suggests multiple fix strategies for different issues:

### Forbidden Characters

1. **Replace with safe alternatives**: Replaces forbidden characters with safe alternatives.
2. **Replace all with underscore**: Replaces all forbidden characters with underscore.
3. **Remove all forbidden characters**: Removes all forbidden characters from the name.

### Trailing Spaces and Periods

1. **Trim trailing spaces/periods**: Removes trailing spaces or periods from the name.

### Reserved Names

1. **Add prefix**: Adds a prefix to the name (e.g., "repo_").
2. **Add suffix**: Adds a suffix to the name (e.g., "_repo").
3. **Replace with underscore**: Replaces the name with an underscore.

## Running the Application

### From Source

1. Clone the repository:
```bash
git clone https://github.com/yourusername/repopath-sanitizer.git
cd repopath-sanitizer
```

2. Create a virtual environment:
```bash
python3 -m venv .venv --system-site-packages
source .venv/bin/activate
```

3. Install the project in editable mode:
```bash
pip install -e .[dev] --no-deps
```

4. Run the application:
```bash
repopath-sanitizer
```

### CLI Mode

To run the application in CLI mode (without GUI):

```bash
repopath-sanitizer --cli --repo /path/to/repository
```

With output options:

```bash
repopath-sanitizer --cli --repo /path/to/repository --json report.json --text report.txt
```

## Debian Packaging

### Prerequisites

Install the required packages for building Debian packages:

```bash
sudo apt-get install debhelper dh-python python3-all python3-pyqt6
```

### Building the Package

1. Navigate to the project root directory:
```bash
cd repopath-sanitizer
```

2. Build the package:
```bash
dpkg-buildpackage -us -uc
```

The `-us` flag skips signing the source package, and `-uc` skips signing the .changes file. These are useful for development and testing.

3. The resulting .deb file will be in the parent directory:
```bash
ls -l ../*.deb
```

### Installing the Package

```bash
sudo dpkg -i ../repopath-sanitizer_1.0.0-1_all.deb
```

If there are dependency issues, run:
```bash
sudo apt-get install -f
```

### Running the Installed Package

After installation, you can run the application from the menu or from the command line:

```bash
repopath-sanitizer
```

## Internationalization

The application is designed to support multiple languages through Qt's internationalization system:

1. Translation files (.ts) can be created using Qt Linguist.
2. Compiled translation files (.qm) are loaded at runtime.
3. The `i18n/` directory contains placeholder files for translations.

To add translations:

1. Use Qt Linguist to create .ts files for each language.
2. Edit the .ts files in Qt Linguist to add translations.
3. Compile the .ts files to .qm files using lrelease.
4. Load the appropriate translation in the application.

## Testing

The application includes unit tests for the path validator and fix generator. To run the tests:

```bash
pytest
```

With coverage:

```bash
pytest --cov=repopath_sanitizer
```

## Future Enhancements

Potential future enhancements include:

1. Automatic fixing of issues (with user confirmation).
2. Integration with Git for automatic committing of fixes.
3. Support for additional version control systems (e.g., Mercurial).
4. Plugin system for custom validation rules.
5. Cloud storage for reports.

## Contributing

Contributions are welcome! Please follow these guidelines:

1. Fork the repository.
2.18. Create a new branch for your feature or bugfix.
3. Make your changes and test them thoroughly.
4. Submit a pull request with a clear description of your changes.

## License

This project is licensed under the GPL-3.0-or-later license. See the LICENSE file for details.
