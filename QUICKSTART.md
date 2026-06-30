# RepoPath Sanitizer - Quick Start Guide

## Overview

RepoPath Sanitizer is a PyQt6 desktop application that scans Git repositories and detects paths that would fail to checkout on Windows. This guide will help you get started quickly.

## Quick Installation

### Option 1: From Source (Recommended for Development)

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

### Option 2: Manual Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/repopath-sanitizer.git
cd repopath-sanitizer
```

2. Install system dependencies and create a virtual environment:
```bash
sudo apt install python3 python3-venv python3-pyqt6 git
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

### Option 3: From Debian Package

1. Build the package:
```bash
dpkg-buildpackage -us -uc
```

2. Install the package:
```bash
sudo dpkg -i ../repopath-sanitizer_1.0.0-1_all.deb
```

3. Run the application:
```bash
repopath-sanitizer
```

## Basic Usage

### Scanning a Repository

1. Launch the application.
2. Click "Browse..." to select a Git repository.
3. Click "Scan" to start scanning.
4. Review the results in the table.
5. Select items to see details and fix options.
6. Apply fixes as needed.
7. Export reports if desired.

If your main concern is Windows clone failures caused by deep folder nesting or long names, open **Settings** first and set the expected Windows checkout root. That improves detection of final checkout paths that become too long only after cloning into a real Windows folder.

### CLI Mode

For automated scanning without the GUI:

```bash
repopath-sanitizer --cli --repo /path/to/repository
```

With output options:

```bash
repopath-sanitizer --cli --repo /path/to/repository --json report.json --text report.txt
```

To estimate the final Windows clone path more accurately:

```bash
repopath-sanitizer --cli --repo /path/to/repository --checkout-root "C:\Users\Juan\Documents\Projects"
```

## Next Steps

- Read the [User Guide](USER_GUIDE.md) for detailed usage instructions.
- Check the [Development Documentation](DEVELOPMENT.md) for building and packaging.
- Review the [Project Summary](PROJECT_SUMMARY.md) for an overview of the project structure.

## Troubleshooting

### Application Won't Start

1. Verify that PyQt6 is installed:
```bash
python3 -c "import PyQt6; print(PyQt6.__version__)"
```

2. Check if all dependencies are installed:
```bash
pip list
```

3. Show CLI help:
```bash
repopath-sanitizer --help
```

### File Dialogs Are Slow on Linux

If `Browse...`, `Save Log`, or export dialogs are very slow on Linux, the problem may come from the Qt platform theme backend.

This project had that problem when Qt was started with:

```bash
QT_QPA_PLATFORMTHEME=qt5ct
```

RepoPath Sanitizer already applies the fix automatically in its own code before creating `QApplication`, so in this project you can still launch it normally with:

```bash
python3 -m repopath_sanitizer
```

The integrated logic sets `QT_QPA_PLATFORMTHEME=gtk3` on Linux when the current value is empty or `qt5ct`.

This matters because in this environment the GTK3 file dialog worked better than the Qt-side dialog backend:

- search worked correctly
- bookmarks/places worked correctly
- dialogs opened without the long delays seen before

If you want to reuse the same workaround in another PyQt6 program that does not include the fix in its code, run it manually with:

```bash
QT_QPA_PLATFORMTHEME=gtk3 python3 -m your_program
```

### Build Issues

If you encounter build issues, ensure you have all the required dependencies:

```bash
sudo apt-get install debhelper dh-python python3-all python3-pyqt6 python3-setuptools
```

## Support

For issues, questions, or contributions, please visit the project repository:
https://github.com/yourusername/repopath-sanitizer
