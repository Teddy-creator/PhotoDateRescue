# Windows EXE Alpha Packaging

This guide is for maintainers who want to build the experimental Windows GUI executable.

If you are a normal user, prefer downloading the latest Windows alpha zip from the repository Releases page. This page explains how maintainers build that package.

## Status

The Windows `.exe` is alpha. It is a convenience package for ordinary photo / video timeline repair, not a signed installer.

Important boundaries:

- ExifTool is required at runtime and is not bundled.
- FFmpeg / FFprobe are recommended for video handling and are not bundled.
- adb is optional and not bundled.
- Windows Live Photo generation is not supported.
- The executable is unsigned and may trigger SmartScreen or antivirus warnings.

## GitHub Actions Build

The recommended alpha build path is GitHub Actions:

1. Open the repository on GitHub.
2. Go to `Actions`.
3. Run `Windows EXE Alpha`.
4. Download the `PhotoDateRescue-windows-exe-alpha` artifact.

The workflow also runs automatically for tags matching `v0.3.*`.
For tag builds, the workflow also attaches the Windows alpha zip to the matching GitHub Release.

## Local Windows Build

On Windows with Python 3.12:

```powershell
scripts\build-windows-exe.ps1
```

Output:

```text
dist\PhotoDateRescue\PhotoDateRescue.exe
```

Before sharing the output, test it on a Windows machine with ExifTool installed and available in `PATH`.
