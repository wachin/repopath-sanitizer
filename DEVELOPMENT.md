# RepoPath Sanitizer - Development Documentation

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
│   ├── __main__.py                  # Entry point for the application
│   ├── cli.py                       # CLI mode
│   ├── engine.py                    # Scan and rename planning logic
│   ├── gitutils.py                  # Git operations
│   ├── pathrules.py                 # Windows compatibility rules
│   ├── report.py                    # Report generation
│   ├── state.py                     # Undo state
│   ├── ui_main.py                   # Main GUI window
│   └── worker.py                    # Background workers
├── repopath_sanitizer/              # Development shim for repo-root execution
├── usr/                             # Installation paths
│   └── bin/
│       └── repopath-sanitizer       # Launcher script
├── requirements.txt                 # Python dependencies
├── pyproject.toml                   # Project configuration
└── README.md                        # Project documentation
```

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

3. Install dependencies:
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

### Package Structure After Installation

The package will install files in the following locations:

```
/usr/lib/python3/dist-packages/repopath_sanitizer/  # Python package
/usr/bin/repopath-sanitizer                         # Launcher script
/usr/share/applications/repopath-sanitizer.desktop  # Desktop entry
/usr/share/icons/hicolor/scalable/apps/repopath-sanitizer.svg  # Icon
```

## Adding Translations

To add translations for the application:

1. Use Qt Linguist to create .ts files for each language:
```bash
pylupdate6 src -ts translations/repopath_sanitizer_fr.ts
```

2. Edit the .ts files in Qt Linguist to add translations.

3. Compile the .ts files to .qm files:
```bash
lrelease translations/repopath_sanitizer_fr.ts
```

4. Load the appropriate translation in the application (see `i18n/__init__.py` for example).

## Testing

Run the unit tests:

```bash
pytest
```

With coverage:

```bash
pytest --cov=repopath_sanitizer
```

## Troubleshooting

### Build Issues

If you encounter build issues, ensure you have all the required dependencies installed:

```bash
sudo apt-get install debhelper dh-python python3-all python3-pyqt6 python3-setuptools
```

### Runtime Issues

If the application doesn't start after installation:

1. Check if PyQt6 is installed:
```bash
python3 -c "import PyQt6; print(PyQt6.__version__)"
```

2. Check if the launcher script is executable:
```bash
ls -l /usr/bin/repopath-sanitizer
```

3. Run the application with verbose output:
```bash
python3 /usr/bin/repopath-sanitizer
```

## Contributing

Contributions are welcome! Please follow these guidelines:

1. Fork the repository.
2. Create a new branch for your feature or bugfix.
3. Make your changes and test them thoroughly.
4. Submit a pull request with a clear description of your changes.

## License

This project is licensed under the GPL-3.0-or-later license. See the LICENSE file for details.
