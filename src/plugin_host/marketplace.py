"""DiceFrame plugin marketplace index and installation helpers."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from .mirrors import (
    DEFAULT_MARKETPLACE_BRANCH,
    DEFAULT_MARKETPLACE_FILE,
    DEFAULT_MARKETPLACE_OWNER,
    DEFAULT_MARKETPLACE_REPO,
    MirrorManager,
    github_archive_url,
    validate_public_http_url,
)


@dataclass(frozen=True)
class MarketplaceSource:
    owner: str = DEFAULT_MARKETPLACE_OWNER
    repo: str = DEFAULT_MARKETPLACE_REPO
    branch: str = DEFAULT_MARKETPLACE_BRANCH
    file_path: str = DEFAULT_MARKETPLACE_FILE


class PluginMarketplace:
    def __init__(self, mirrors: MirrorManager, source: MarketplaceSource | None = None) -> None:
        self.mirrors = mirrors
        self.source = source or MarketplaceSource()

    async def list_plugins(self) -> dict[str, Any]:
        fetched = await self.mirrors.fetch_raw(
            self.source.owner,
            self.source.repo,
            self.source.branch,
            self.source.file_path,
        )
        if not fetched.ok or not isinstance(fetched.data, str):
            return {"ok": False, "error": fetched.error or "插件市场读取失败", "plugins": [], "source": fetched.to_dict()}
        try:
            raw_items = json.loads(fetched.data)
        except json.JSONDecodeError as exc:
            return {"ok": False, "error": f"插件市场 JSON 无效：{exc}", "plugins": [], "source": fetched.to_dict()}
        if not isinstance(raw_items, list):
            return {"ok": False, "error": "插件市场 JSON 必须是数组", "plugins": [], "source": fetched.to_dict()}
        plugins = [item for item in (_normalize_market_item(item) for item in raw_items) if item is not None]
        source = fetched.to_dict()
        source.pop("data", None)
        return {"ok": True, "plugins": plugins, "total": len(plugins), "source": source}

    async def package_for_plugin(self, plugin_id: str) -> dict[str, Any]:
        listing = await self.list_plugins()
        if not listing.get("ok"):
            return listing
        normalized_id = plugin_id.strip()
        for item in listing["plugins"]:
            if item["id"] == normalized_id:
                package_url = str(item.get("package_url") or "")
                if not package_url:
                    package_url = github_archive_url(str(item.get("repository_url") or ""), str(item.get("branch") or "main"))
                validate_public_http_url(package_url)
                fetched = await self.mirrors.fetch_github_url(package_url, binary=True)
                if not fetched.ok or not isinstance(fetched.data, bytes):
                    return {"ok": False, "error": fetched.error or "插件包下载失败", "plugin": item, "source": fetched.to_dict()}
                source = fetched.to_dict()
                source.pop("data", None)
                return {"ok": True, "plugin": item, "payload": fetched.data, "source": source}
        return {"ok": False, "error": f"插件市场中找不到：{plugin_id}"}


def _normalize_market_item(item: Any) -> dict[str, Any] | None:
    if not isinstance(item, dict):
        return None
    manifest = item.get("manifest") if isinstance(item.get("manifest"), dict) else {}
    plugin_id = str(manifest.get("id") or item.get("id") or "").strip()
    if not plugin_id:
        return None
    repository_url = str(item.get("repository_url") or item.get("repositoryUrl") or manifest.get("repository_url") or "")
    urls = manifest.get("urls") if isinstance(manifest.get("urls"), dict) else {}
    if not repository_url:
        repository_url = str(urls.get("repository") or "")
    name = str(manifest.get("name") or item.get("name") or plugin_id)
    description = str(manifest.get("description") or item.get("description") or "")
    version = str(manifest.get("version") or item.get("version") or "")
    return {
        "id": plugin_id,
        "name": name,
        "version": version,
        "description": description,
        "plugin_type": str(manifest.get("plugin_type") or item.get("plugin_type") or item.get("pluginType") or ""),
        "repository_url": repository_url,
        "package_url": str(item.get("package_url") or item.get("packageUrl") or ""),
        "branch": str(item.get("branch") or "main"),
        "author": item.get("author") or manifest.get("author") or "",
        "license": item.get("license") or manifest.get("license") or "",
        "tags": item.get("tags") if isinstance(item.get("tags"), list) else [],
        "capabilities": manifest.get("capabilities") if isinstance(manifest.get("capabilities"), list) else item.get("capabilities") or [],
        "permissions": manifest.get("permissions") if isinstance(manifest.get("permissions"), list) else item.get("permissions") or [],
        "docs": str(manifest.get("docs") or item.get("docs") or urls.get("documentation") or ""),
        "homepage": str(item.get("homepage") or urls.get("homepage") or repository_url),
        "manifest": manifest,
    }
