# Release and Packaging

[中文](RELEASE_CN.md) | English

This document describes how maintainers build GitHub Release attachments.

## Building Windows Packages Locally

Confirm the version in `src/version.py`, then run from a clean public working tree:

```powershell
python scripts\build_release.py
```

Output:

```text
dist/DiceFrame-vVERSION-windows.zip
```

For the self-contained Windows package:

```powershell
python scripts\build_portable.py
```

Output:

```text
dist/DiceFrame-vVERSION-windows-portable.zip
```

The standard zip contains backend and Vue source, built `static-v2/`, `web_ui.bat`, Docker files, bundled templates/plugins, and user documentation. The portable package additionally contains `DiceFrame.exe`, embedded Windows Python, and installed runtime dependencies. Portable users do not need Python or Node.js.

The portable build verifies SHA-256 for embedded Python and the bootstrap pip wheel, then installs only the fixed-version, hash-pinned Windows wheels in `requirements-portable.lock`. The bootstrap does not install unpinned setuptools or wheel packages. A mismatch stops the build. Dependency or Python upgrades must update reviewed URLs, versions, and hashes instead of disabling validation.

Packages exclude:

- `data/`
- `.env`
- Logs and databases
- Test directories
- `node_modules`
- Local IDE and assistant configuration

The release builder also excludes legacy custom worlds and rules found under bundled `templates/`. User content belongs in `data/templates/` and must never enter a public package.

For a local-only package from a dirty worktree:

```powershell
python scripts\build_release.py --allow-dirty
```

Do not use `--allow-dirty` for an official release.

## GitHub Automation

`.github/workflows/release.yml` runs for `v*` tags:

1. Set up Python and Node.js.
2. Build the frontend.
3. Create `DiceFrame-vVERSION-windows.zip`.
4. Attach it to the GitHub Release.
5. Build and attach the portable package on a Windows runner.

Workflow Actions are pinned to full commit SHAs. When upgrading an Action, verify the commit referenced by the official version tag and review the SHA change.

```powershell
git tag v0.1.0
git push origin v0.1.0
```

The GitHub Release body is also the source of the application's release notes. Complete it after publishing.
