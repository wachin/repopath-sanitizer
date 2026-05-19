# RepoPath Sanitizer - Complete Project Structure

## Overview

This document provides a complete overview of the RepoPath Sanitizer project structure, including all files and their purposes.

## Directory Structure

```
repopath-sanitizer/
├── debian/                              # Debian packaging files
│   ├── changelog                        # Package changelog
│   ├── control                          # Package metadata
│   ├── rules                            # Build rules
│   ├── repopath-sanitizer.install       # Installation instructions
│   ├── copyright                        # Copyright information
│   └── repopath-sanitizer.desktop       # Desktop entry file
├── data/                                # Application data
│   └── icons/                           # Application icons
│       └── repopath-sanitizer.svg       # Main application icon
├── src/repopath_sanitizer/              # Maintained Python package
│   ├── __init__.py                      # Package initialization
│   ├── __main__.py                      # Entry point for the application
│   ├── cli.py                           # CLI mode
│   ├── constants.py                     # Application constants
│   ├── engine.py                        # Scan and rename planning logic
│   ├── gitutils.py                      # Git operations
│   ├── models.py                        # Data models
│   ├── pathrules.py                     # Windows compatibility rules
│   ├── report.py                        # Report generation
│   ├── state.py                         # Undo state
│   ├── ui_main.py                       # Main GUI window
│   └── worker.py                        # Background workers
├── repopath_sanitizer/                  # Development shim for repo-root execution
├── usr/                                 # Installation paths
│   └── bin/
│       └── repopath-sanitizer           # Launcher script
├── requirements.txt                     # Python dependencies
├── pyproject.toml                       # Project configuration
├── setup.sh                             # Setup script
├── README.md                            # Project documentation
├── DEVELOPMENT.md                       # Development documentation
├── USER_GUIDE.md                        # User guide
├── PROJECT_SUMMARY.md                   # Project summary
├── QUICKSTART.md                        # Quick start guide
└── PROJECT_STRUCTURE.md                 # This file
```

## File Descriptions

### Core Application Files

#### src/repopath_sanitizer/__init__.py
Package initialization file with version information.

#### src/repopath_sanitizer/__main__.py
Entry point for the application. Handles both GUI and CLI modes.

#### src/repopath_sanitizer/ui_main.py
Main GUI window implementation with all UI components and event handling.

#### src/repopath_sanitizer/pathrules.py
Core logic for validating paths against Windows compatibility rules.

#### src/repopath_sanitizer/engine.py
Git repository scanner that detects Windows-incompatible paths.

#### src/repopath_sanitizer/report.py
Report generation in multiple formats (JSON, plain text, commit messages).

### Debian Packaging Files

#### debian/changelog
Package changelog following Debian format.

#### debian/control
Package metadata including dependencies and description.

#### debian/rules
Build rules for creating the Debian package.

#### debian/repopath-sanitizer.install
Installation instructions for the package.

#### debian/copyright
Copyright information and license details.

#### debian/repopath-sanitizer.desktop
Desktop entry file for the application menu.

### Data Files

#### data/icons/repopath-sanitizer.svg
Application icon in SVG format.

### Installation Files

#### usr/bin/repopath-sanitizer
Launcher script for the application.

### Configuration Files

#### requirements.txt
Python dependencies for the project.

#### pyproject.toml
Project configuration using modern Python packaging standards.

#### setup.sh
Setup script for easy installation and configuration.

### Documentation Files

#### README.md
Main project documentation with overview and installation instructions.

#### DEVELOPMENT.md
Development documentation with build instructions and contribution guidelines.

#### USER_GUIDE.md
Comprehensive user guide with detailed usage instructions.

#### PROJECT_SUMMARY.md
Project summary with overview of components and features.

#### QUICKSTART.md
Quick start guide for getting started quickly.

#### PROJECT_STRUCTURE.md
This file - complete project structure documentation.

## Key Components

### 1. Path Validator

The path validator is responsible for detecting Windows-incompatible paths. It checks for:

- Forbidden characters in path segments
- Trailing spaces and periods
- Reserved device names
- Path length issues
- Case-insensitive collisions
- Unicode normalization pitfalls

### 2. Git Scanner

The Git scanner handles scanning Git repositories for Windows-incompatible paths. It:

- Uses `git ls-files` to get all tracked files
- Validates each path using the path validator
- Provides progress updates during scanning
- Supports cancellation of ongoing scans
- Runs in a separate thread to avoid freezing the UI

### 3. Report Generator

The report generator creates reports from scan results in multiple formats:

- JSON format for programmatic consumption
- Plain text format for human reading
- Commit messages for Git commits

### 4. Main Window

The main window provides the GUI for the application. It includes:

- Repository selection (folder picker)
- Scan button with progress indicator and cancel
- Results table with columns for Type, Current Path, Issue(s), Proposed Fix, and Status
- Details panel showing detected issues, fix options, and previews
- Export functionality for reports

### 5. Entry Point

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
2. **Add suffix**: Adds a suffix to the the name (e.g., "_repo").
3. **Replace with underscore**: Replaces the name with an underscore.

## Running the Application

### From Source

1. Clone the repository:
```bash
git clone https://github.com/yourusername/repopath-sanitizer.git
cd repopath-sanitizer
```

2. Run the setup script:
```bash
chmod +x setup.sh
./setup.sh
```

3. Activate the virtual environment:
```bash
source .venv/bin/activate
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

### Building the Package

1. Navigate to the project root directory:
```bash
cd repopath-sanitizer
```

2. Install build dependencies:
```bash
sudo apt-get install debhelper dh-python python3-all python3-pyqt6
```

3. Build the package:
```bash
dpkg-buildpackage -us -uc
```

4. The resulting .deb file will be in the parent directory:
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

## Contributing

Contributions are welcome! Please follow these guidelines:

1. Fork the repository.
2. Create a new branch for your feature or bugfix.
3. Make your changes and test them thoroughly.
4. Submit a pull request with a clear description of your changes.

## License

This project is licensed under the GPL-3.0-or-later license. See the LICENSE file for details.
