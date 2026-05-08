# Project Overview

PhotoDateRescue is a macOS-first tool for repairing photo and video timeline metadata after Android-to-iPhone / Apple Photos migrations.

The project must stay conservative with user data. It should generate safe copies and reports, never mutate source media, never auto-import into Apple Photos / iCloud, and never delete originals.

# Repository Map

- `src/photodaterescue/`: CLI, GUI, metadata, repair, Android export, Motion Photo / Live Photo workflow code.
- `tests/`: pytest coverage for CLI, metadata handling, repair, GUI controller, wizard, Android export, and Live Photo helper flows.
- `docs/`: public user, packaging, privacy, release, and validation documentation.
- `scripts/`: maintainer scripts such as macOS app packaging.
- `README.md`: public-facing project overview and setup guide. Keep it accurate for non-expert users.

# Core Commands

Use the project virtual environment unless there is a clear reason not to.

```bash
source .venv/bin/activate
python -m pip install -e .[dev]
.venv/bin/python -m pytest -q
photodaterescue doctor
photodaterescue wizard
photodaterescue-gui
scripts/build-macos-app.sh
```

Run `scripts/build-macos-app.sh` after GUI launcher, packaging, Tk, PyInstaller, or macOS app behavior changes.

# Safety Rules

- Do not modify source photos or videos in place.
- Do not auto-import into Apple Photos, iCloud, Photos Library bundles, or any cloud service.
- Do not delete or deduplicate user media automatically.
- Do not commit real photos, videos, `.photoslibrary` bundles, reports with private paths, raw Android exports, or generated repair outputs.
- Keep `docs/privacy-and-data-safety.md` and `docs/release-checklist.md` aligned with new user-visible workflows.
- Treat generated reports as privacy-sensitive because they may contain filenames and absolute paths.

# Feature Boundaries

- The GUI currently focuses on ordinary photo and video timeline repair.
- Motion Photo / Live Photo recovery is CLI-first and must be described as advanced or experimental unless real import validation supports stronger claims.
- Windows supports core scan/report/ordinary photo/video repair and Android export flows.
- Windows does not promise Apple Photos-recognized Live Photo generation.
- Do not broaden support claims just because tests pass on synthetic samples; documentation claims need real sample or import evidence.

# Git Workflow

This is a public personal project. Keep the workflow lightweight, but keep `main` clean.

- Start new feature or polish work from `main` on a `feature/...` branch.
- Make small commits while developing if helpful.
- Before landing on `main`, run the relevant verification commands.
- Squash feature work back into `main` as one clear commit when practical.
- Do not force-push `main` after public releases unless the user explicitly accepts the history rewrite risk.
- Use tags like `v0.1.0`, `v0.1.1`, and `v0.2.0` only for versions intended as public release points.
- Do not push local backup branches such as `backup/pre-squash-*` to GitHub.

# Verification

Before claiming work is complete, run fresh checks that match the change:

- Code changes: `.venv/bin/python -m pytest -q`
- CLI behavior changes: relevant `photodaterescue ... --help` or command smoke checks
- GUI or packaging changes: `scripts/build-macos-app.sh`
- Release preparation: privacy scans from `docs/release-checklist.md`

If a check cannot run, report exactly which check was skipped and why.

# Release Rules

Before creating a GitHub Release:

- Confirm `main` is clean and pushed.
- Confirm the intended tag does not already exist.
- Run tests and any relevant build command.
- Build the macOS app from a known-good environment.
- Zip the `.app` as a release artifact and record its SHA256.
- Use `docs/release-notes-v0.1.0.md` as the style reference for release notes.

# Retrospective Rule

After non-obvious bugs, packaging failures, platform-specific path issues, metadata edge cases, or workaround-heavy fixes, consider preserving the lesson with `$codexception` or durable docs.

Good candidates include Tk / PyInstaller packaging pitfalls, Finder-launched app PATH issues, Apple Photos import behavior, and real Android Motion Photo format discoveries.
