# Global Git Hooks For Windows-Safe Paths

This folder contains a reusable Git `pre-commit` hook that you can enable for **all** repositories on your Linux system.

The main script is:

- `global-hooks/pre-commit-windows-paths`

It blocks a commit when staged paths would likely cause problems on Windows, including:

- forbidden characters
- trailing spaces or trailing periods
- reserved names such as `CON`, `AUX`, `COM1`, `LPT1`
- file or folder names that are too long
- repository-relative paths that are too long
- estimated final Windows checkout paths that are too long after adding the clone base folder

## Install Globally

Create a directory for global Git hooks and copy or symlink this script into it as `pre-commit`:

```bash
mkdir -p ~/.config/git/hooks
ln -sf /home/wachin/Dev/AI-dev/repopath-sanitizer/global-hooks/pre-commit-windows-paths ~/.config/git/hooks/pre-commit
chmod +x /home/wachin/Dev/AI-dev/repopath-sanitizer/global-hooks/pre-commit-windows-paths
chmod +x ~/.config/git/hooks/pre-commit
git config --global core.hooksPath ~/.config/git/hooks
```

After that, every `git commit` in every repository that uses your global Git configuration will run this hook first.

## Optional Tuning

You can tune the limits and the estimated Windows clone destination with environment variables:

```bash
export REPOPATH_SANITIZER_MAX_PATH=260
export REPOPATH_SANITIZER_MAX_SEGMENT=255
export REPOPATH_SANITIZER_CHECKOUT_ROOT='C:\Users\Juan\Documents\Projects'
```

If you want these settings always active, place them in your shell startup file such as `~/.bashrc`.

## How It Behaves

When a staged path is problematic, the hook blocks the commit and prints:

- the staged path
- the problem code
- a human-readable explanation

Example categories you may see:

- `TRAILING_SPACE_PERIOD`
- `RESERVED_DEVICE`
- `SEGMENT_TOO_LONG`
- `PATH_TOO_LONG`
- `CHECKOUT_PATH_TOO_LONG`

## Notes

- The hook checks only **staged** paths, because those are the ones about to enter history.
- It works independently of the GUI application.
- If a specific repository defines its own `core.hooksPath`, that repository setting overrides the global one.
