# macOS GUI Packaging

This guide is for maintainers who want to build a local `PhotoDateRescue.app`.

## Build

Use a Python build environment with a modern Tk runtime. On macOS, avoid the
system Python 3.9 / Tcl-Tk 8.5 combination for GUI packaging: it can build an
app that launches but renders a blank window.

Recommended Homebrew setup:

```bash
brew install python@3.12 python-tk@3.12
```

Recommended one-command build:

```bash
cd /path/to/PhotoDateRescue
scripts/build-macos-app.sh
```

Manual build:

```bash
cd /path/to/PhotoDateRescue
/opt/homebrew/bin/python3.12 -m venv .venv-gui
source .venv-gui/bin/activate
python -m pip install --upgrade pip
python -m pip install -e '.[dev]' pyinstaller
python -m PyInstaller --windowed --name PhotoDateRescue src/photodaterescue/gui_launcher.py
```

Output:

```text
dist/PhotoDateRescue.app
```

The launcher uses an absolute package import so it can run both as an installed script and as a PyInstaller script target.

## Validation

After building, open the app and confirm the main window renders the folder
selectors, dependency status, scan button, and output panel:

```bash
open dist/PhotoDateRescue.app
```

If the app opens as a blank window, rebuild with the Homebrew Python +
`python-tk@3.12` environment above.

## Notes

- The first local build is unsigned and not notarized.
- macOS may warn that the app cannot be opened because it is from an unidentified developer.
- The beginner GUI focuses on ordinary photo/video timeline repair.
- Advanced Motion Photo / Live Photo workflows remain CLI-first.
- ExifTool is required for reliable metadata reading.
- FFmpeg is recommended for video handling.
- Beginner usage instructions are in `docs/manual/macos-gui-beginner-guide.md`.
