#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="${PHOTODATERESCUE_GUI_PYTHON:-/opt/homebrew/bin/python3.12}"
VENV_DIR="${PHOTODATERESCUE_GUI_VENV:-.venv-gui}"
APP_NAME="${PHOTODATERESCUE_APP_NAME:-PhotoDateRescue}"

cd "$ROOT_DIR"

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "error: macOS app packaging must run on macOS." >&2
  exit 1
fi

if [[ ! -x "$PYTHON_BIN" ]]; then
  cat >&2 <<EOF
error: cannot find Python at $PYTHON_BIN

Recommended setup:
  brew install python@3.12 python-tk@3.12

Or pass a custom Python:
  PHOTODATERESCUE_GUI_PYTHON=/path/to/python3 scripts/build-macos-app.sh
EOF
  exit 1
fi

"$PYTHON_BIN" - <<'PY'
import tkinter as tk

root = tk.Tk()
patchlevel = root.tk.call("info", "patchlevel")
root.destroy()

major = int(str(patchlevel).split(".", 1)[0])
if major < 9:
    raise SystemExit(
        "error: Python can import tkinter, but Tk is too old ({0}). "
        "Use Homebrew python@3.12 + python-tk@3.12 to avoid blank app windows.".format(patchlevel)
    )
print("Using Tk {0}".format(patchlevel))
PY

echo "Creating build environment: $VENV_DIR"
"$PYTHON_BIN" -m venv "$VENV_DIR"
"$VENV_DIR/bin/python" -m pip install --upgrade pip
"$VENV_DIR/bin/python" -m pip install -e '.[dev]' pyinstaller

echo "Cleaning old build artifacts"
rm -rf build dist "$APP_NAME.spec"

echo "Building $APP_NAME.app"
"$VENV_DIR/bin/python" -m PyInstaller \
  --windowed \
  --name "$APP_NAME" \
  src/photodaterescue/gui_launcher.py

echo
echo "Built: $ROOT_DIR/dist/$APP_NAME.app"
echo "Open it with:"
echo "  open \"$ROOT_DIR/dist/$APP_NAME.app\""
