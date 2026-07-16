"""Manifest-driven child-process plugin host."""

from __future__ import annotations

import asyncio
import io
import json
import logging
import os
import re
import secrets
import shutil
import subprocess
import sys
import tempfile
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .marketplace import PluginMarketplace
from .mirrors import MirrorManager

_ID_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_ALLOWED_CONTROLS = {"switch", "text", "secret", "number", "select", "string-list"}


@dataclass
class PluginRuntime:
    manifest: dict[str, Any]
    schema: dict[str, Any]
    directory: Path
    config: dict[str, Any] = field(default_factory=dict)
    secrets: dict[str, str] = field(default_factory=dict)
    process: asyncio.subprocess.Process | None = None
    monitor_task: asyncio.Task | None = None
    status: str = "disabled"
    error: str = ""


class PluginHost:
    def __init__(self, plugins_dir: Path, data_dir: Path, *, base_env: dict[str, str] | None = None) -> None:
        self.plugins_dir = plugins_dir
        self.data_dir = data_dir
        self.base_env = base_env or {}
        self.plugins: dict[str, PluginRuntime] = {}
        self.logger = logging.getLogger("trpg.plugins")
        self.mirrors = MirrorManager(self.data_dir / "_marketplace" / "mirrors.json")
        self.marketplace = PluginMarketplace(self.mirrors)

    def discover(self) -> list[dict[str, Any]]:
        self.plugins.clear()
        if not self.plugins_dir.exists():
            return []
        for manifest_path in sorted(self.plugins_dir.glob("*/plugin.json")):
            try:
                plugin_id, runtime = self._load_runtime(manifest_path.parent)
                runtime.config, runtime.secrets = self._load_config(plugin_id, runtime.schema)
                runtime.status = "disabled" if not runtime.config.get("enabled") else "stopped"
                self.plugins[plugin_id] = runtime
            except Exception as exc:
                self.logger.exception("插件加载失败: %s", manifest_path)
                fallback_id = manifest_path.parent.name
                self.plugins[fallback_id] = PluginRuntime(
                    {"id": fallback_id, "name": fallback_id, "version": "?", "description": "插件清单无效"},
                    {"type": "object", "properties": {}}, manifest_path.parent,
                    status="failed", error=str(exc),
                )
        return self.list_public()

    def list_public(self) -> list[dict[str, Any]]:
        return [self.public_detail(plugin_id) for plugin_id in self.plugins]

    def public_detail(self, plugin_id: str) -> dict[str, Any]:
        runtime = self._require(plugin_id)
        if runtime.process and runtime.process.returncode is not None and runtime.status == "running":
            runtime.status = "failed"
            runtime.error = f"插件进程已退出，code={runtime.process.returncode}"
        public_config = dict(runtime.config)
        for key, field_schema in runtime.schema.get("properties", {}).items():
            if self._sensitive(field_schema):
                value = runtime.secrets.get(key, "")
                public_config[key] = {"configured": bool(value), "masked": f"***{value[-4:]}" if value else ""}
        return {
            "id": plugin_id,
            "name": runtime.manifest.get("name", plugin_id),
            "version": runtime.manifest.get("version", ""),
            "description": runtime.manifest.get("description", ""),
            "enabled": bool(runtime.config.get("enabled")),
            "running": bool(runtime.process and runtime.process.returncode is None),
            "status": runtime.status,
            "error": runtime.error,
            "schema": runtime.schema,
            "config": public_config,
            "capabilities": runtime.manifest.get("capabilities", []),
            "docs": runtime.manifest.get("docs", ""),
        }

    async def install_from_zip(self, payload: bytes, *, overwrite: bool = False, allow_any_root: bool = False) -> dict[str, Any]:
        if not payload:
            raise ValueError("插件包为空")
        self.plugins_dir.mkdir(parents=True, exist_ok=True)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="plugin-install-", dir=str(self.data_dir)) as temp_name:
            temp_dir = Path(temp_name)
            self._extract_zip(payload, temp_dir)
            source_dir = self._find_install_root(temp_dir)
            plugin_id, _runtime = self._load_runtime(source_dir, require_directory_match=False)
            if not allow_any_root and source_dir != temp_dir and source_dir.name != plugin_id:
                raise ValueError("插件包顶层目录名必须与插件 ID 一致")
            target_dir = (self.plugins_dir / plugin_id).resolve()
            self._ensure_inside(self.plugins_dir, target_dir)
            if target_dir.exists() and not overwrite:
                raise ValueError(f"插件 {plugin_id} 已存在；如需更新请启用覆盖安装")

            staging_dir = (self.plugins_dir / f".{plugin_id}.installing-{secrets.token_hex(6)}").resolve()
            backup_dir = (self.plugins_dir / f".{plugin_id}.backup-{secrets.token_hex(6)}").resolve()
            self._ensure_inside(self.plugins_dir, staging_dir)
            self._ensure_inside(self.plugins_dir, backup_dir)
            shutil.copytree(source_dir, staging_dir)
            try:
                if target_dir.exists():
                    if plugin_id in self.plugins:
                        await self.stop(plugin_id)
                    target_dir.rename(backup_dir)
                staging_dir.rename(target_dir)
                if backup_dir.exists():
                    shutil.rmtree(backup_dir)
            except Exception:
                if target_dir.exists() and not (target_dir / "plugin.json").exists():
                    shutil.rmtree(target_dir, ignore_errors=True)
                if backup_dir.exists() and not target_dir.exists():
                    backup_dir.rename(target_dir)
                if staging_dir.exists():
                    shutil.rmtree(staging_dir, ignore_errors=True)
                raise

        self.discover()
        return self.public_detail(plugin_id)

    async def marketplace_plugins(self) -> dict[str, Any]:
        listing = await self.marketplace.list_plugins()
        if listing.get("ok"):
            installed = set(self.plugins)
            for item in listing.get("plugins", []):
                item["installed"] = item.get("id") in installed
                if item["installed"]:
                    current = self.plugins[item["id"]].manifest
                    item["installed_version"] = current.get("version", "")
        return listing

    async def install_from_marketplace(self, plugin_id: str, *, overwrite: bool = False) -> dict[str, Any]:
        package = await self.marketplace.package_for_plugin(plugin_id)
        if not package.get("ok"):
            raise ValueError(str(package.get("error") or "插件市场安装失败"))
        detail = await self.install_from_zip(package["payload"], overwrite=overwrite, allow_any_root=True)
        return {"source": package.get("source", {}), "marketplace": package.get("plugin", {}), **detail}

    async def update_from_marketplace(self, plugin_id: str) -> dict[str, Any]:
        if plugin_id not in self.plugins:
            raise KeyError(f"插件不存在：{plugin_id}")
        return await self.install_from_marketplace(plugin_id, overwrite=True)

    def list_mirrors(self) -> dict[str, Any]:
        return {"mirrors": self.mirrors.list()}

    def add_mirror(self, data: dict[str, Any]) -> dict[str, Any]:
        return self.mirrors.add(data)

    def update_mirror(self, mirror_id: str, patch: dict[str, Any]) -> dict[str, Any]:
        return self.mirrors.update(mirror_id, patch)

    def delete_mirror(self, mirror_id: str) -> dict[str, Any]:
        return self.mirrors.delete(mirror_id)

    async def test_mirror(self, mirror_id: str = "") -> dict[str, Any]:
        return await self.mirrors.test(mirror_id)

    async def uninstall(self, plugin_id: str, *, delete_data: bool = False) -> dict[str, Any]:
        runtime = self._require(plugin_id)
        await self.stop(plugin_id)
        plugin_dir = runtime.directory.resolve()
        self._ensure_inside(self.plugins_dir, plugin_dir)
        if plugin_dir.exists():
            shutil.rmtree(plugin_dir)
        if delete_data:
            data_dir = (self.data_dir / plugin_id).resolve()
            self._ensure_inside(self.data_dir, data_dir)
            if data_dir.exists():
                shutil.rmtree(data_dir)
        self.plugins.pop(plugin_id, None)
        return {"id": plugin_id, "uninstalled": True, "data_deleted": bool(delete_data)}

    async def start_enabled(self) -> None:
        for plugin_id, runtime in self.plugins.items():
            if runtime.config.get("enabled") and runtime.status != "failed":
                await self.start(plugin_id)

    async def update_config(self, plugin_id: str, changes: dict[str, Any]) -> dict[str, Any]:
        runtime = self._require(plugin_id)
        properties = runtime.schema.get("properties", {})
        new_config = dict(runtime.config)
        new_secrets = dict(runtime.secrets)
        for key, value in changes.items():
            if key not in properties:
                continue
            if self._sensitive(properties[key]):
                if isinstance(value, dict):
                    # Public plugin details expose secrets as
                    # {"configured": true, "masked": "***xxxx"}.  If the UI
                    # saves an unchanged form, do not persist that mask object
                    # as the real secret.
                    continue
                normalized = self._normalize_value(properties[key], value)
                if normalized:
                    new_secrets[key] = normalized
            else:
                normalized = self._normalize_value(properties[key], value)
                new_config[key] = normalized
        self._validate_required(runtime.schema, new_config, new_secrets)
        runtime.config, runtime.secrets = new_config, new_secrets
        self._save_config(plugin_id, runtime)
        await self.restart(plugin_id)
        return self.public_detail(plugin_id)

    async def start(self, plugin_id: str) -> None:
        runtime = self._require(plugin_id)
        if not runtime.config.get("enabled"):
            runtime.status = "disabled"
            return
        if runtime.process and runtime.process.returncode is None:
            runtime.status = "running"
            return
        runtime.status, runtime.error = "starting", ""
        generated = False
        for key, field_schema in runtime.schema.get("properties", {}).items():
            if self._sensitive(field_schema) and (field_schema.get("ui") or {}).get("generate") and not runtime.secrets.get(key):
                runtime.secrets[key] = secrets.token_urlsafe(24)
                generated = True
        if generated:
            self._save_config(plugin_id, runtime)
        env = os.environ.copy()
        env.update(self.base_env)
        env["TRPG_PARENT_PID"] = str(os.getpid())
        for key, field_schema in runtime.schema.get("properties", {}).items():
            env_name = str((field_schema.get("ui") or {}).get("env") or "")
            if not env_name:
                continue
            value = runtime.secrets.get(key, "") if self._sensitive(field_schema) else runtime.config.get(key, field_schema.get("default"))
            env[env_name] = json.dumps(value, ensure_ascii=False) if isinstance(value, list) else str(value).lower() if isinstance(value, bool) else str(value or "")
        command = runtime.manifest.get("entrypoint")
        if not isinstance(command, list) or not command or not all(isinstance(item, str) for item in command):
            runtime.status, runtime.error = "failed", "entrypoint 必须是非空字符串数组"
            return
        executable = sys.executable if command[0] == "{python}" else command[0]
        args = command[1:] if command[0] == "{python}" else command[1:]
        kwargs: dict[str, Any] = {}
        if os.name == "nt":
            kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
        try:
            runtime.process = await asyncio.create_subprocess_exec(executable, *args, cwd=str(runtime.directory.parent.parent), env=env, **kwargs)
            runtime.status = "running"
            self.logger.info("插件 %s 已启动，PID=%s", plugin_id, runtime.process.pid)
            runtime.monitor_task = asyncio.create_task(self._monitor_process(plugin_id, runtime.process))
        except Exception as exc:
            runtime.status, runtime.error = "failed", str(exc)
            self.logger.exception("插件 %s 启动失败", plugin_id)

    async def stop(self, plugin_id: str) -> None:
        runtime = self._require(plugin_id)
        monitor = runtime.monitor_task
        runtime.monitor_task = None
        if monitor and not monitor.done():
            monitor.cancel()
        process = runtime.process
        if process and process.returncode is None:
            runtime.status = "stopping"
            process.terminate()
            try:
                await asyncio.wait_for(process.wait(), timeout=5)
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
        runtime.process = None
        runtime.status = "disabled" if not runtime.config.get("enabled") else "stopped"

    async def restart(self, plugin_id: str) -> None:
        await self.stop(plugin_id)
        await self.start(plugin_id)

    async def cleanup(self) -> None:
        for plugin_id in list(self.plugins):
            await self.stop(plugin_id)

    async def _monitor_process(self, plugin_id: str, process: asyncio.subprocess.Process) -> None:
        try:
            code = await process.wait()
        except asyncio.CancelledError:
            raise
        except Exception:
            self.logger.exception("插件 %s 进程监控失败", plugin_id)
            return
        runtime = self.plugins.get(plugin_id)
        if not runtime or runtime.process is not process:
            return
        if runtime.status == "stopping" or not runtime.config.get("enabled"):
            return
        runtime.status = "failed"
        runtime.error = f"插件进程已退出，code={code}"
        runtime.process = None
        self.logger.warning("插件 %s 意外退出，3 秒后尝试自动重启，code=%s", plugin_id, code)
        await asyncio.sleep(3)
        if self.plugins.get(plugin_id) is runtime and runtime.config.get("enabled") and runtime.status == "failed":
            await self.start(plugin_id)

    def migrate_config(self, plugin_id: str, legacy: dict[str, Any]) -> None:
        runtime = self._require(plugin_id)
        marker = self.data_dir / plugin_id / ".migrated-v1"
        if marker.exists():
            return
        for key, value in legacy.items():
            field_schema = runtime.schema.get("properties", {}).get(key)
            if not field_schema or value in (None, ""):
                continue
            if self._sensitive(field_schema):
                runtime.secrets[key] = str(value)
            else:
                runtime.config[key] = self._normalize_value(field_schema, value)
        self._save_config(plugin_id, runtime)
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.write_text("1\n", encoding="ascii")

    def _load_config(self, plugin_id: str, schema: dict[str, Any]) -> tuple[dict[str, Any], dict[str, str]]:
        folder = self.data_dir / plugin_id
        config = {key: field.get("default") for key, field in schema.get("properties", {}).items() if "default" in field and not self._sensitive(field)}
        secrets_data: dict[str, str] = {}
        for filename, target in (("config.json", config), ("secrets.json", secrets_data)):
            path = folder / filename
            if path.exists():
                loaded = json.loads(path.read_text(encoding="utf-8"))
                if isinstance(loaded, dict):
                    target.update(loaded)
        return config, secrets_data

    def _save_config(self, plugin_id: str, runtime: PluginRuntime) -> None:
        folder = self.data_dir / plugin_id
        folder.mkdir(parents=True, exist_ok=True)
        self._atomic_json(folder / "config.json", runtime.config)
        self._atomic_json(folder / "secrets.json", runtime.secrets)

    def _load_runtime(self, plugin_dir: Path, *, require_directory_match: bool = True) -> tuple[str, PluginRuntime]:
        plugin_dir = plugin_dir.resolve()
        manifest_path = plugin_dir / "plugin.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        plugin_id = str(manifest.get("id") or "")
        if not _ID_RE.fullmatch(plugin_id):
            raise ValueError("插件 ID 非法")
        if require_directory_match and plugin_dir.name != plugin_id:
            raise ValueError("插件 ID 与目录名不一致")
        if int(manifest.get("schema_version", 0)) != 1:
            raise ValueError("不支持的 manifest schema_version")
        schema_path = (plugin_dir / str(manifest.get("config_schema") or "config.schema.json")).resolve()
        self._ensure_inside(plugin_dir, schema_path)
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        self._validate_schema(schema)
        self._validate_entrypoint(manifest)
        return plugin_id, PluginRuntime(manifest, schema, plugin_dir)

    @staticmethod
    def _extract_zip(payload: bytes, target_dir: Path) -> None:
        try:
            archive = zipfile.ZipFile(io.BytesIO(payload))
        except zipfile.BadZipFile as exc:
            raise ValueError("插件包不是有效 zip 文件") from exc
        with archive:
            for info in archive.infolist():
                name = info.filename
                parts = Path(name).parts
                if not name or Path(name).is_absolute() or any(part == ".." for part in parts):
                    raise ValueError("插件包包含非法路径")
                file_type = (info.external_attr >> 16) & 0o170000
                if file_type == 0o120000:
                    raise ValueError("插件包不能包含符号链接")
                resolved = (target_dir / name).resolve()
                PluginHost._ensure_inside(target_dir, resolved)
            archive.extractall(target_dir)

    @staticmethod
    def _find_install_root(temp_dir: Path) -> Path:
        if (temp_dir / "plugin.json").exists():
            return temp_dir
        candidates = [path.parent for path in temp_dir.glob("*/plugin.json")]
        if not candidates:
            raise ValueError("插件包缺少 plugin.json")
        if len(candidates) > 1:
            raise ValueError("插件包包含多个 plugin.json，请只打包一个插件")
        return candidates[0]

    @staticmethod
    def _ensure_inside(root: Path, target: Path) -> None:
        root = root.resolve()
        target = target.resolve()
        if target != root and root not in target.parents:
            raise ValueError("路径越界")

    @staticmethod
    def _atomic_json(path: Path, value: dict[str, Any]) -> None:
        temp = path.with_suffix(path.suffix + ".tmp")
        temp.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
        temp.replace(path)

    @staticmethod
    def _validate_schema(schema: dict[str, Any]) -> None:
        if schema.get("type") != "object" or not isinstance(schema.get("properties"), dict):
            raise ValueError("配置 Schema 必须是 object")
        for key, field_schema in schema["properties"].items():
            control = (field_schema.get("ui") or {}).get("control")
            if control and control not in _ALLOWED_CONTROLS:
                raise ValueError(f"字段 {key} 使用不支持的控件 {control}")

    @staticmethod
    def _validate_entrypoint(manifest: dict[str, Any]) -> None:
        command = manifest.get("entrypoint")
        if not isinstance(command, list) or not command or not all(isinstance(item, str) for item in command):
            raise ValueError("entrypoint 必须是非空字符串数组")

    @staticmethod
    def _sensitive(field_schema: dict[str, Any]) -> bool:
        ui = field_schema.get("ui") or {}
        return bool(ui.get("sensitive") or ui.get("control") == "secret")

    @staticmethod
    def _normalize_value(field_schema: dict[str, Any], value: Any) -> Any:
        field_type = field_schema.get("type")
        if field_type == "boolean": return bool(value)
        if field_type == "number":
            number = float(value)
            if "exclusiveMinimum" in field_schema and number <= float(field_schema["exclusiveMinimum"]): raise ValueError("数值必须大于最小值")
            return number
        if field_type == "integer": return int(value)
        if field_type == "array": return list(dict.fromkeys(str(item).strip() for item in (value if isinstance(value, list) else []) if str(item).strip()))
        text = str(value or "").strip()
        if field_schema.get("enum") and text not in field_schema["enum"]: raise ValueError("选项无效")
        return text

    @staticmethod
    def _validate_required(schema: dict[str, Any], config: dict[str, Any], secrets_data: dict[str, str]) -> None:
        for key in schema.get("required", []):
            if not config.get(key) and not secrets_data.get(key):
                raise ValueError(f"缺少必填配置：{key}")

    def _require(self, plugin_id: str) -> PluginRuntime:
        if plugin_id not in self.plugins:
            raise KeyError(f"插件不存在：{plugin_id}")
        return self.plugins[plugin_id]
