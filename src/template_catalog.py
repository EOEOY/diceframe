"""Persistent runtime catalog for bundled and user-created templates."""

from __future__ import annotations

import json
import logging
import shutil
from pathlib import Path
from typing import Literal

logger = logging.getLogger("trpg")

TemplateKind = Literal["rules", "worlds"]


def is_user_template_file(path: Path, kind: TemplateKind) -> bool:
    """Return whether a template belongs to the user rather than the bundle."""
    stem = path.stem.lower()
    if kind == "rules" and stem.startswith(("custom_", "ai_rule_")):
        return True
    if kind == "worlds" and stem.startswith(("custom_", "ai_")):
        return True
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return False
    return isinstance(data, dict) and bool(data.get("custom"))


def _copy_atomic(source: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(target.suffix + ".tmp")
    shutil.copyfile(source, temporary)
    temporary.replace(target)


def sync_template_catalog(
    bundled_dir: Path,
    runtime_dir: Path,
    kind: TemplateKind,
) -> dict[str, int]:
    """Refresh bundled templates and migrate legacy user templates into data/."""
    stats = {"copied": 0, "updated": 0, "migrated": 0, "preserved": 0, "failed": 0}
    runtime_dir.mkdir(parents=True, exist_ok=True)
    if not bundled_dir.is_dir():
        logger.warning("内置模板目录不存在: %s", bundled_dir)
        return stats

    for source in sorted(bundled_dir.glob("*.json")):
        target = runtime_dir / source.name
        source_is_user = is_user_template_file(source, kind)
        target_is_user = target.exists() and is_user_template_file(target, kind)
        try:
            if source_is_user:
                if target.exists():
                    stats["preserved"] += 1
                else:
                    _copy_atomic(source, target)
                    stats["migrated"] += 1
                continue
            if target_is_user:
                logger.warning("用户模板与内置模板同名，保留用户版本: %s", target)
                stats["preserved"] += 1
                continue
            if target.exists() and source.read_bytes() == target.read_bytes():
                continue
            existed = target.exists()
            _copy_atomic(source, target)
            stats["updated" if existed else "copied"] += 1
        except OSError:
            stats["failed"] += 1
            logger.exception("模板同步失败: %s -> %s", source, target)
    return stats
