"""Validate and package a DiceFrame plugin directory as a zip file."""

from __future__ import annotations

import argparse
import json
import sys
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
DEFAULT_OUTPUT_DIR = ROOT / "dist" / "plugins"
EXCLUDED_NAMES = {
    ".git",
    ".pytest_cache",
    "__pycache__",
    "node_modules",
    "dist",
}
EXCLUDED_SUFFIXES = {
    ".log",
    ".pyc",
    ".pyo",
    ".sqlite",
    ".db",
    ".tmp",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate and package a DiceFrame plugin.")
    parser.add_argument("plugin_dir", type=Path, help="Path to a plugin directory containing plugin.json.")
    parser.add_argument(
        "-o",
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Directory for the generated zip. Defaults to dist/plugins.",
    )
    parser.add_argument("--overwrite", action="store_true", help="Overwrite an existing zip file.")
    return parser.parse_args()


def load_manifest(plugin_dir: Path) -> dict:
    manifest_path = plugin_dir / "plugin.json"
    if not manifest_path.exists():
        raise SystemExit(f"Missing plugin.json: {manifest_path}")
    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"plugin.json is not valid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise SystemExit("plugin.json must contain a JSON object")
    return data


def validate_with_host(plugin_dir: Path) -> tuple[str, str]:
    from src.plugin_host import PluginHost

    manifest = load_manifest(plugin_dir)
    plugin_id = str(manifest.get("id") or "").strip()
    if not plugin_id:
        raise SystemExit("plugin.json must declare id")
    if plugin_dir.name != plugin_id:
        raise SystemExit(f"Plugin directory name must match id: expected {plugin_id}, got {plugin_dir.name}")
    host = PluginHost(plugin_dir.parent, ROOT / "data" / "_package_plugin_validation")
    try:
        host._load_runtime(plugin_dir)  # Reuse the same manifest/schema/contributes validation as WebUI install.
    except Exception as exc:
        raise SystemExit(f"Plugin validation failed: {exc}") from exc
    version = str(manifest.get("version") or "0.0.0").strip() or "0.0.0"
    return plugin_id, version


def should_skip(path: Path) -> bool:
    if any(part in EXCLUDED_NAMES for part in path.parts):
        return True
    return path.suffix.lower() in EXCLUDED_SUFFIXES


def safe_archive_name(plugin_dir: Path, path: Path) -> str:
    relative = path.relative_to(plugin_dir.parent).as_posix()
    if relative.startswith("../") or relative.startswith("/") or "/../" in relative:
        raise SystemExit(f"Unsafe path in plugin package: {path}")
    return relative


def make_zip(plugin_dir: Path, output_zip: Path, *, overwrite: bool) -> Path:
    if output_zip.exists() and not overwrite:
        raise SystemExit(f"Output already exists: {output_zip}. Use --overwrite to replace it.")
    output_zip.parent.mkdir(parents=True, exist_ok=True)
    temp_zip = output_zip.with_suffix(output_zip.suffix + ".tmp")
    if temp_zip.exists():
        temp_zip.unlink()
    with zipfile.ZipFile(temp_zip, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(plugin_dir.rglob("*")):
            if path.is_dir() or should_skip(path.relative_to(plugin_dir)):
                continue
            if path.is_symlink():
                raise SystemExit(f"Plugin package cannot contain symlinks: {path}")
            archive.write(path, safe_archive_name(plugin_dir, path))
    temp_zip.replace(output_zip)
    return output_zip


def smoke_test_zip(output_zip: Path) -> None:
    with zipfile.ZipFile(output_zip) as archive:
        names = archive.namelist()
        plugin_jsons = [name for name in names if name.endswith("/plugin.json")]
        if len(plugin_jsons) != 1:
            raise SystemExit("Package must contain exactly one plugin.json")
        if any(name.startswith("/") or ".." in Path(name).parts for name in names):
            raise SystemExit("Package contains an unsafe path")


def main() -> int:
    args = parse_args()
    plugin_dir = args.plugin_dir.resolve()
    if not plugin_dir.is_dir():
        raise SystemExit(f"Plugin directory does not exist: {plugin_dir}")
    plugin_id, version = validate_with_host(plugin_dir)
    output_zip = args.output_dir.resolve() / f"{plugin_id}-{version}.zip"
    make_zip(plugin_dir, output_zip, overwrite=bool(args.overwrite))
    smoke_test_zip(output_zip)
    print(f"Plugin package created: {output_zip}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
