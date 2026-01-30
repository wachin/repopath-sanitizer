# RepoPath Sanitizer

A PyQt6 desktop app (Linux-first) that scans a local Git working tree and finds file/folder paths
that would fail to check out on Windows. It proposes safe fixes and can apply them using **git-aware renames**
(`git mv`) to preserve history.


## Features

- Detects Windows-incompatible paths in Git repositories
- Git-aware renames (`git mv`) to preserve history
- Collision detection (case-insensitive + Unicode NFC)
- Long path detection and shortening strategies
- GUI + CLI modes
- Safe undo system

---

## Screenshots

### Main Window (Light Theme)

![Main window light theme](docs/screenshots/main-window-light-theme.png)

### Main Window (Dark Theme)

![Main window dark theme](docs/screenshots/main-window-dark-theme.png)

## Why `pyproject.toml`?
This project uses a modern `pyproject.toml` (PEP 621) because it:
- keeps metadata and dependencies in one standard place
- works well with Debian packaging (dh-python / pybuild) and with pip
- avoids legacy `setup.py` boilerplate

## PyQt6 on Debian (VERY IMPORTANT)

On Debian (including **Debian 12**, where this program was tested), installing **PyQt6 via pip** may fail because it tries to build from source and requires a full Qt development environment.

For this reason, on Debian it is recommended to use **the system PyQt6 package (APT)** together with a virtual environment that can access system packages.

### ✔ Recommended method on Debian

```bash
sudo apt update
sudo apt install python3-pyqt6

python3 -m venv .venv --system-site-packages
source .venv/bin/activate

pip install -U pip
pip install -e .[dev] --no-deps

repopath-sanitizer
```

🔹 `--system-site-packages` allows the virtual environment to use PyQt6 installed via APT.
🔹 `--no-deps` prevents pip from trying to reinstall PyQt6 from PyPI.

CLI mode:

```bash
repopath-sanitizer --cli --repo /path/to/repo --json out.json --text out.txt
```

## Debian packaging (template)

See `debian/` and the packaging notes in the end of this README, or run:

```bash
sudo apt build-dep .
dpkg-buildpackage -us -uc
```

(You will need the standard Debian Python packaging toolchain.)

---

## Translations (Qt Linguist / Qt Creator)

The application is prepared for internationalization.

### Requirements

Install Qt Linguist (included with Qt Creator):

```bash
sudo apt install qtcreator qttools5-dev-tools qt6-tools-dev-tools
```

### Workflow to add a language (example: Spanish)

1. Create a translation file:

```bash
pylupdate6 src -ts translations/repopath_sanitizer_es.ts
```

2. Open it in Qt Linguist:

```bash
linguist translations/repopath_sanitizer_es.ts
```

3. Translate all texts.

4. Compile to `.qm`:

```bash
lrelease translations/repopath_sanitizer_es.ts
```

5. The resulting `.qm` file will be installed to:

```
/usr/share/repopath-sanitizer/translations/
```

---


