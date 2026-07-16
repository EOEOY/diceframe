"""Manifest 插件查询、配置和生命周期。"""
from __future__ import annotations
from pathlib import Path
from typing import TYPE_CHECKING, Any

from src.bots.qq.card_renderer import cleanup_card_cache

if TYPE_CHECKING:
    from src.webui.api import WebAPI

def list_plugins(api: "WebAPI") -> dict[str, Any]:
    return {"ok": True, "plugins": api._plugins.list_public() if api._plugins else []}

def plugin_detail(api: "WebAPI", plugin_id: str) -> dict[str, Any]:
    if not api._plugins: return {"ok": False, "error": "插件宿主未启用"}
    return {"ok": True, **api._plugins.public_detail(plugin_id)}

async def update_plugin_config(api: "WebAPI", plugin_id: str, changes: dict[str, Any]) -> dict[str, Any]:
    if not api._plugins: return {"ok": False, "error": "插件宿主未启用"}
    return {"ok": True, **await api._plugins.update_config(plugin_id, changes)}

async def control_plugin(api: "WebAPI", plugin_id: str, action: str) -> dict[str, Any]:
    if not api._plugins: return {"ok": False, "error": "插件宿主未启用"}
    method = {"start": api._plugins.start, "stop": api._plugins.stop, "restart": api._plugins.restart}.get(action)
    if not method: return {"ok": False, "error": "插件操作无效"}
    await method(plugin_id)
    return {"ok": True, **api._plugins.public_detail(plugin_id)}

async def install_plugin(api: "WebAPI", payload: bytes, overwrite: bool = False) -> dict[str, Any]:
    if not api._plugins:
        return {"ok": False, "error": "插件宿主未启用"}
    return {"ok": True, **await api._plugins.install_from_zip(payload, overwrite=overwrite)}

async def list_plugin_marketplace(api: "WebAPI") -> dict[str, Any]:
    if not api._plugins:
        return {"ok": False, "error": "插件宿主未启用", "plugins": []}
    return await api._plugins.marketplace_plugins()

async def install_marketplace_plugin(api: "WebAPI", plugin_id: str, overwrite: bool = False) -> dict[str, Any]:
    if not api._plugins:
        return {"ok": False, "error": "插件宿主未启用"}
    return {"ok": True, **await api._plugins.install_from_marketplace(plugin_id, overwrite=overwrite)}

async def update_marketplace_plugin(api: "WebAPI", plugin_id: str) -> dict[str, Any]:
    if not api._plugins:
        return {"ok": False, "error": "插件宿主未启用"}
    return {"ok": True, **await api._plugins.update_from_marketplace(plugin_id)}

async def uninstall_plugin(api: "WebAPI", plugin_id: str, delete_data: bool = False) -> dict[str, Any]:
    if not api._plugins:
        return {"ok": False, "error": "插件宿主未启用"}
    return {"ok": True, **await api._plugins.uninstall(plugin_id, delete_data=delete_data)}

def list_plugin_mirrors(api: "WebAPI") -> dict[str, Any]:
    if not api._plugins:
        return {"ok": False, "error": "插件宿主未启用", "mirrors": []}
    return {"ok": True, **api._plugins.list_mirrors()}

def add_plugin_mirror(api: "WebAPI", data: dict[str, Any]) -> dict[str, Any]:
    if not api._plugins:
        return {"ok": False, "error": "插件宿主未启用"}
    return {"ok": True, "mirror": api._plugins.add_mirror(data)}

def update_plugin_mirror(api: "WebAPI", mirror_id: str, data: dict[str, Any]) -> dict[str, Any]:
    if not api._plugins:
        return {"ok": False, "error": "插件宿主未启用"}
    return {"ok": True, "mirror": api._plugins.update_mirror(mirror_id, data)}

def delete_plugin_mirror(api: "WebAPI", mirror_id: str) -> dict[str, Any]:
    if not api._plugins:
        return {"ok": False, "error": "插件宿主未启用"}
    return {"ok": True, **api._plugins.delete_mirror(mirror_id)}

async def test_plugin_mirror(api: "WebAPI", mirror_id: str = "") -> dict[str, Any]:
    if not api._plugins:
        return {"ok": False, "error": "插件宿主未启用"}
    return await api._plugins.test_mirror(mirror_id)

def clear_plugin_card_cache(api: "WebAPI", plugin_id: str) -> dict[str, Any]:
    if not api._plugins:
        return {"ok": False, "error": "插件宿主未启用"}
    if plugin_id != "qq-napcat":
        return {"ok": False, "error": "该插件没有可清理的卡片缓存"}
    api._plugins.public_detail(plugin_id)  # 触发 KeyError，保持和其他插件接口一致
    data_dir = Path(api._plugins.data_dir).resolve()
    card_dir = (data_dir / "bot" / "cards").resolve()
    if data_dir not in card_dir.parents:
        return {"ok": False, "error": "卡片缓存路径非法"}
    result = cleanup_card_cache(card_dir, delete_all=True)
    return {"ok": True, "path": str(card_dir), **result}
