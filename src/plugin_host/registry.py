"""Plugin contribution registry for static DiceFrame plugin resources."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


_CONTENT_CONTRIBUTIONS = {
    "rules": "rule",
    "world_templates": "world_template",
    "character_templates": "character_template",
    "characters": "character_template",
    "npcs": "npc",
    "npc": "npc",
    "items": "item",
    "spells": "spell",
    "classes": "class",
}
_THEME_CONTRIBUTIONS = {
    "theme": "theme",
    "themes": "theme",
}
_MAP_CONTRIBUTIONS = {
    "locations": "map_location",
    "icons": "map_icon",
    "scenes": "map_scene",
    "grids": "map_grid",
}
_CONTRIBUTION_TYPES = {
    "content-pack": _CONTENT_CONTRIBUTIONS,
    "theme": _THEME_CONTRIBUTIONS,
    "map-pack": _MAP_CONTRIBUTIONS,
}


@dataclass(frozen=True)
class PluginContribution:
    plugin_id: str
    plugin_name: str
    plugin_type: str
    kind: str
    key: str
    path: Path
    relative_path: str
    title: str = ""
    description: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "plugin_id": self.plugin_id,
            "plugin_name": self.plugin_name,
            "plugin_type": self.plugin_type,
            "kind": self.kind,
            "key": self.key,
            "path": self.relative_path,
            "title": self.title,
            "description": self.description,
        }


class ContributionRegistry:
    def __init__(self) -> None:
        self._items: list[PluginContribution] = []
        self._by_kind_key: dict[tuple[str, str], PluginContribution] = {}

    def clear(self) -> None:
        self._items.clear()
        self._by_kind_key.clear()

    def clear_plugin(self, plugin_id: str) -> None:
        kept = [item for item in self._items if item.plugin_id != plugin_id]
        self._items = []
        self._by_kind_key = {}
        for item in kept:
            self._add(item)

    def register_static_plugin(self, manifest: dict[str, Any], plugin_dir: Path) -> list[PluginContribution]:
        plugin_type = str(manifest.get("plugin_type") or "")
        mapping = _CONTRIBUTION_TYPES.get(plugin_type)
        if not mapping:
            return []
        contributes = manifest.get("contributes")
        if contributes is None:
            return []
        if not isinstance(contributes, dict):
            raise ValueError("contributes 必须是对象")

        plugin_id = str(manifest.get("id") or "")
        self.clear_plugin(plugin_id)
        registered: list[PluginContribution] = []
        for field, value in contributes.items():
            kind = mapping.get(str(field))
            if not kind:
                raise ValueError(f"{plugin_type} 不支持 contributes.{field}")
            for path in _expand_contribution_paths(plugin_dir, value):
                item = _contribution_from_path(manifest, plugin_dir, kind, path)
                self._add(item)
                registered.append(item)
        return registered

    def list(self, kind: str = "") -> list[PluginContribution]:
        if not kind:
            return list(self._items)
        return [item for item in self._items if item.kind == kind]

    def find(self, kind: str, key: str) -> PluginContribution | None:
        return self._by_kind_key.get((kind, key))

    def _add(self, item: PluginContribution) -> None:
        existing = self._by_kind_key.get((item.kind, item.key))
        if existing and existing.plugin_id != item.plugin_id:
            raise ValueError(
                f"插件资源冲突：{item.kind} {item.key} 已由 {existing.plugin_id} 提供"
            )
        self._items.append(item)
        self._by_kind_key[(item.kind, item.key)] = item


def validate_contributes(manifest: dict[str, Any], plugin_dir: Path) -> None:
    registry = ContributionRegistry()
    registry.register_static_plugin(manifest, plugin_dir)


def _expand_contribution_paths(plugin_dir: Path, value: Any) -> list[Path]:
    patterns = value if isinstance(value, list) else [value]
    if not all(isinstance(pattern, str) and pattern.strip() for pattern in patterns):
        raise ValueError("contributes 路径必须是非空字符串或字符串数组")
    paths: list[Path] = []
    for pattern in patterns:
        normalized = pattern.strip().replace("\\", "/")
        _validate_pattern(normalized)
        matches = sorted(plugin_dir.glob(normalized))
        for match in matches:
            resolved = match.resolve()
            _ensure_inside(plugin_dir, resolved)
            if resolved.is_file() and not resolved.is_symlink():
                paths.append(resolved)
    return paths


def _validate_pattern(pattern: str) -> None:
    candidate = Path(pattern)
    if candidate.is_absolute() or any(part in ("..", "") for part in candidate.parts):
        raise ValueError("contributes 路径不能是绝对路径或包含 ..")


def _contribution_from_path(
    manifest: dict[str, Any],
    plugin_dir: Path,
    kind: str,
    path: Path,
) -> PluginContribution:
    key = path.stem
    title = path.stem
    description = ""
    if path.suffix.lower() == ".json":
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError(f"插件资源 JSON 无效：{path.relative_to(plugin_dir)}") from exc
        if not isinstance(data, dict):
            raise ValueError(f"插件资源必须是 JSON 对象：{path.relative_to(plugin_dir)}")
        if kind == "rule":
            key = str(data.get("rule_id") or path.stem)
            title = str(data.get("rule_name") or key)
        elif kind == "world_template":
            key = str(data.get("world_id") or path.stem)
            title = str(data.get("world_name") or key)
        elif kind == "theme":
            key = str(data.get("id") or manifest.get("id") or path.stem)
            title = str(data.get("name") or manifest.get("name") or key)
        elif kind == "character_template":
            key = str(data.get("id") or data.get("card_id") or path.stem)
            title = str(data.get("character_name") or data.get("name") or key)
        else:
            key = str(data.get("id") or path.stem)
            title = str(data.get("name") or key)
        description = str(data.get("description") or "")
    if not key.strip():
        raise ValueError(f"插件资源 ID 不能为空：{path.relative_to(plugin_dir)}")
    return PluginContribution(
        plugin_id=str(manifest.get("id") or ""),
        plugin_name=str(manifest.get("name") or manifest.get("id") or ""),
        plugin_type=str(manifest.get("plugin_type") or ""),
        kind=kind,
        key=key.strip(),
        path=path,
        relative_path=path.relative_to(plugin_dir).as_posix(),
        title=title.strip(),
        description=description.strip(),
    )


def _ensure_inside(root: Path, target: Path) -> None:
    root = root.resolve()
    target = target.resolve()
    if target != root and root not in target.parents:
        raise ValueError("contributes 路径越界")
