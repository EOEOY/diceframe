"""Build a Windows portable DiceFrame package with bundled Python runtime."""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
import urllib.request
import zipfile
from pathlib import Path

import build_launcher
import build_release


ROOT = Path(__file__).resolve().parents[1]
DIST_DIR = ROOT / "dist"
BUILD_ROOT = DIST_DIR / "_portable_build"
CACHE_DIR = DIST_DIR / "_portable_cache"
DEFAULT_PYTHON_VERSION = "3.11.9"
GET_PIP_URL = "https://bootstrap.pypa.io/get-pip.py"

FORBIDDEN_PATTERNS = [
    re.compile(r"(^|/)data/"),
    re.compile(r"(^|/)\.env$"),
    re.compile(r"(^|/)\.env\.(?!example$)"),
    re.compile(r"(^|/)\.git/"),
    re.compile(r"(^|/)\.codex/"),
    re.compile(r"(^|/)\.claude/"),
    re.compile(r"(^|/)node_modules/"),
    re.compile(r"(^|/)tests/"),
    re.compile(r"(^|/)frontend-v2/tests/"),
    re.compile(r"(^|/)frontend-v2/e2e/"),
    re.compile(r"(^|/)test-results/"),
    re.compile(r"(^|/)playwright-report/"),
    re.compile(r"\.(?:log|pyc|pyo|sqlite|db)$"),
]


def download(url: str, target: Path) -> Path:
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists() and target.stat().st_size > 0:
        return target
    print(f"Downloading {url}", flush=True)
    urllib.request.urlretrieve(url, target)
    return target


def run(cmd: list[str], cwd: Path) -> None:
    print("> " + " ".join(str(part) for part in cmd), flush=True)
    subprocess.run(cmd, cwd=str(cwd), check=True)


def python_embed_url(version: str) -> str:
    return f"https://www.python.org/ftp/python/{version}/python-{version}-embed-amd64.zip"


def install_python_runtime(runtime_dir: Path, version: str, python_url: str) -> None:
    if runtime_dir.exists():
        shutil.rmtree(runtime_dir)
    runtime_dir.mkdir(parents=True)
    archive = download(python_url, CACHE_DIR / Path(python_url).name)
    with zipfile.ZipFile(archive) as zf:
        zf.extractall(runtime_dir)
    patch_pth(runtime_dir)
    get_pip = download(GET_PIP_URL, CACHE_DIR / "get-pip.py")
    python_exe = runtime_dir / "python.exe"
    run([str(python_exe), str(get_pip), "--no-warn-script-location"], runtime_dir)
    run(
        [
            str(python_exe),
            "-m",
            "pip",
            "install",
            "--no-cache-dir",
            "--no-warn-script-location",
            "-r",
            str(ROOT / "requirements.txt"),
        ],
        runtime_dir,
    )
    cleanup_runtime(runtime_dir)


def patch_pth(runtime_dir: Path) -> None:
    pth_files = sorted(runtime_dir.glob("python*._pth"))
    if not pth_files:
        raise RuntimeError("Cannot find embedded Python ._pth file")
    pth = pth_files[0]
    lines = pth.read_text(encoding="utf-8").splitlines()
    out: list[str] = []
    has_site_packages = False
    has_import_site = False
    for line in lines:
        stripped = line.strip()
        if stripped == "Lib/site-packages":
            has_site_packages = True
        if stripped == "#import site":
            out.append("import site")
            has_import_site = True
            continue
        if stripped == "import site":
            has_import_site = True
        out.append(line)
    if not has_site_packages:
        out.insert(max(len(out) - 1, 0), "Lib/site-packages")
    if not has_import_site:
        out.append("import site")
    pth.write_text("\n".join(out) + "\n", encoding="utf-8")


def cleanup_runtime(runtime_dir: Path) -> None:
    for pattern in ("**/__pycache__", "**/*.pyc", "**/*.pyo"):
        for path in runtime_dir.glob(pattern):
            if path.is_dir():
                shutil.rmtree(path, ignore_errors=True)
            else:
                path.unlink(missing_ok=True)
    site_packages = runtime_dir / "Lib" / "site-packages"
    if site_packages.exists():
        removable_patterns = (
            "*/tests",
            "*/test",
            "pip",
            "pip-*.dist-info",
            "setuptools",
            "setuptools-*.dist-info",
            "wheel",
            "wheel-*.dist-info",
            "packaging",
            "packaging-*.dist-info",
        )
        for pattern in removable_patterns:
            for path in site_packages.glob(pattern):
                if path.is_dir():
                    shutil.rmtree(path, ignore_errors=True)
                else:
                    path.unlink(missing_ok=True)
    scripts_dir = runtime_dir / "Scripts"
    if scripts_dir.exists():
        shutil.rmtree(scripts_dir, ignore_errors=True)


def build_windows_launcher(package_dir: Path) -> None:
    build_launcher.build_launcher(
        package_dir / "DiceFrame.exe",
        BUILD_ROOT / "DiceFrame.ico",
    )


def validate_zip(output_zip: Path) -> None:
    with zipfile.ZipFile(output_zip) as zf:
        names = zf.namelist()
    bad = [name for name in names if any(pattern.search(name.replace("\\", "/")) for pattern in FORBIDDEN_PATTERNS)]
    if bad:
        raise RuntimeError("Portable zip contains forbidden paths:\n" + "\n".join(bad[:20]))
    required = [
        "/DiceFrame.exe",
        "/python/python.exe",
        "/app/web_server.py",
        "/app/static-v2/index.html",
    ]
    for suffix in required:
        if not any(name.endswith(suffix) for name in names):
            raise RuntimeError(f"Portable zip is missing {suffix}")
    if any(name.endswith("/Start DiceFrame.bat") for name in names):
        raise RuntimeError("Portable zip should not contain Start DiceFrame.bat")
    if any(name.lower().endswith(".bat") for name in names):
        raise RuntimeError("Portable zip should not contain batch launchers")
    if not any("/app/static-v2/assets/" in name and name.endswith(".js") for name in names):
        raise RuntimeError("Portable zip is missing built frontend assets")
    if not any("/python/Lib/site-packages/aiohttp/" in name for name in names):
        raise RuntimeError("Portable zip is missing aiohttp")
    if not any("/python/Lib/site-packages/PIL/" in name for name in names):
        raise RuntimeError("Portable zip is missing Pillow")


def make_zip(package_dir: Path, output_zip: Path) -> Path:
    output_zip.parent.mkdir(parents=True, exist_ok=True)
    if output_zip.exists():
        try:
            output_zip.unlink()
        except PermissionError:
            output_zip = build_release.available_zip_name(output_zip)
    shutil.make_archive(str(output_zip.with_suffix("")), "zip", root_dir=package_dir.parent, base_dir=package_dir.name)
    validate_zip(output_zip)
    return output_zip


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a Windows portable DiceFrame package.")
    parser.add_argument("--version", default=build_release.app_version(), help="Release version, default: src/version.py")
    parser.add_argument("--output-dir", type=Path, default=DIST_DIR, help="Directory for generated zip")
    parser.add_argument("--python-version", default=DEFAULT_PYTHON_VERSION, help="Embedded Python version")
    parser.add_argument("--python-url", default="", help="Override embedded Python zip URL")
    parser.add_argument("--allow-dirty", action="store_true", help="Allow packaging with uncommitted git changes")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if build_release.git_dirty() and not args.allow_dirty:
        print(
            "Working tree has uncommitted changes. Commit first, or rerun with --allow-dirty for a local test package.",
            file=sys.stderr,
        )
        return 2

    version = args.version.lstrip("v")
    package_name = f"DiceFrame-v{version}-windows-portable"
    package_dir = BUILD_ROOT / package_name
    app_dir = package_dir / "app"
    runtime_dir = package_dir / "python"
    output_zip = args.output_dir.resolve() / f"{package_name}.zip"

    if BUILD_ROOT.exists():
        shutil.rmtree(BUILD_ROOT)
    build_release.prepare_package_tree(app_dir)
    (app_dir / "web_ui.bat").unlink(missing_ok=True)
    build_release.build_frontend(app_dir)
    install_python_runtime(runtime_dir, args.python_version, args.python_url or python_embed_url(args.python_version))
    build_windows_launcher(package_dir)
    output_zip = make_zip(package_dir, output_zip)
    print(f"\nPortable package created: {output_zip}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except subprocess.CalledProcessError as exc:
        raise SystemExit(exc.returncode)
