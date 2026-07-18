import json

import pytest

from src.plugin_host.marketplace import PluginMarketplace, _normalize_market_item
from src.plugin_host.mirrors import FetchResult, MirrorManager


class FakeMirrors:
    def __init__(self, payload: bytes, manifest: dict | None = None):
        self.payload = payload
        self.manifest = manifest or {
            "schema_version": 1,
            "id": "demo-pack",
            "name": "Demo",
            "version": "1.2.0",
            "description": "demo",
            "plugin_type": "content-pack",
            "permissions": ["content.read"],
        }
        self.max_bytes = None
        self.download_url = ""

    async def fetch_github_api(self, api_path, **_kwargs):
        if api_path.endswith("/releases/latest"):
            data = {"tag_name": "v1.2.0", "html_url": "https://github.com/example/demo/releases/tag/v1.2.0"}
        else:
            data = {"sha": "a" * 40}
        return FetchResult(ok=True, data=json.dumps(data), status=200)

    async def fetch_raw(self, *_args, **_kwargs):
        return FetchResult(ok=True, data=json.dumps(self.manifest), status=200)

    async def fetch_github_url(self, url, *, binary=False, max_bytes=None):
        self.max_bytes = max_bytes
        self.download_url = url
        return FetchResult(ok=True, data=self.payload, url=url, status=200)


def _market_item(**changes):
    item = {
        "id": "demo-pack",
        "repository_url": "https://github.com/example/demo",
        "distribution": "repository",
        "risk_level": "declarative",
        "update_policy": "automatic",
        "approved_permissions": ["content.read"],
        "manifest": {
            "id": "demo-pack",
            "name": "Demo",
            "version": "1.1.0",
            "description": "demo",
            "plugin_type": "content-pack",
            "permissions": ["content.read"],
        },
    }
    item.update(changes)
    return _normalize_market_item(item)


def test_marketplace_repository_item_does_not_require_author_zip_or_sha256():
    item = _market_item()

    assert item["installable"] is True
    assert "sha256" not in item
    assert item["distribution"] == "repository"


def test_bundled_plugin_is_visible_but_not_installable():
    item = _market_item(distribution="bundled", trust_level="official")

    assert item["installable"] is False
    assert "随 DiceFrame" in item["verification_error"]


def test_reserved_plugin_type_is_visible_but_not_installable():
    item = _market_item(manifest={
        "id": "demo-pack",
        "name": "Demo",
        "version": "1.0.0",
        "plugin_type": "provider",
    })

    assert item["support"]["level"] == "reserved"
    assert item["installable"] is False


@pytest.mark.asyncio
async def test_marketplace_downloads_latest_release_at_resolved_commit():
    payload = b"repository snapshot"
    mirrors = FakeMirrors(payload)
    marketplace = PluginMarketplace(mirrors)
    item = _market_item()

    async def listing():
        return {"ok": True, "plugins": [item]}

    marketplace.list_plugins = listing
    result = await marketplace.package_for_plugin("demo-pack")

    assert result["ok"] is True
    assert result["payload"] == payload
    assert result["plugin"]["commit_sha"] == "a" * 40
    assert mirrors.download_url.endswith(f"/{'a' * 40}.zip")
    assert mirrors.max_bytes is not None


@pytest.mark.asyncio
async def test_marketplace_blocks_permission_expansion():
    mirrors = FakeMirrors(b"snapshot", manifest={
        "schema_version": 1,
        "id": "demo-pack",
        "name": "Demo",
        "version": "1.2.0",
        "description": "demo",
        "plugin_type": "content-pack",
        "permissions": ["content.read", "network.client"],
    })
    marketplace = PluginMarketplace(mirrors)

    with pytest.raises(ValueError, match="重新审核"):
        await marketplace.resolve_release(_market_item())


def test_official_github_source_is_attempted_before_proxies(tmp_path):
    manager = MirrorManager(tmp_path / "mirrors.json")

    assert manager.enabled()[0]["id"] == "github"
