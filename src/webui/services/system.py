"""System metadata and update checks."""

from __future__ import annotations

import logging
import os
import re
from typing import TYPE_CHECKING, Any

import aiohttp

from src.version import DEFAULT_UPDATE_REPOSITORY, __version__

if TYPE_CHECKING:
    from src.webui.api import WebAPI

logger = logging.getLogger("trpg")

GITHUB_API = "https://api.github.com"
_VERSION_RE = re.compile(r"^\s*v?(\d+)(?:\.(\d+))?(?:\.(\d+))?(?:[-+].*)?\s*$", re.IGNORECASE)


class NoReleaseError(RuntimeError):
    """Raised when the repository exists but has no public releases yet."""


def _version_tuple(value: str) -> tuple[int, int, int] | None:
    match = _VERSION_RE.match(value or "")
    if not match:
        return None
    major, minor, patch = match.groups()
    return int(major), int(minor or 0), int(patch or 0)


def is_newer_version(latest: str, current: str) -> bool:
    latest_tuple = _version_tuple(latest)
    current_tuple = _version_tuple(current)
    if latest_tuple is None or current_tuple is None:
        return False
    return latest_tuple > current_tuple


async def check_updates(api: "WebAPI", include_prerelease: bool = False) -> dict[str, Any]:
    repo = str(os.getenv("TRPG_UPDATE_REPOSITORY") or DEFAULT_UPDATE_REPOSITORY).strip()
    if not repo or "/" not in repo:
        return {
            "ok": False,
            "error": "更新仓库配置无效",
            "current_version": __version__,
            "repository": repo,
            "update_available": False,
        }

    check_source: dict[str, Any] = {"mode": "github-api", "mirror_name": "GitHub API"}
    try:
        proxy_url = str(getattr(getattr(api, "_llm_client", None), "proxy_url", "") or "")
        release, check_source = await _fetch_release_for_api(api, repo, include_prerelease, proxy_url)
    except NoReleaseError as exc:
        return {
            "ok": True,
            "message": str(exc),
            "current_version": __version__,
            "repository": repo,
            "update_available": False,
            "no_release": True,
            "releases_url": f"https://github.com/{repo}/releases",
            "source_url": f"https://github.com/{repo}",
            "install_hint": _install_hint(repo),
            "check_source": check_source,
        }
    except Exception as exc:
        logger.warning("检查更新失败: %s", exc)
        return {
            "ok": False,
            "error": str(exc),
            "current_version": __version__,
            "repository": repo,
            "update_available": False,
        }

    latest_version = str(release.get("tag_name") or "").lstrip("vV")
    latest = {
        "version": latest_version,
        "tag_name": release.get("tag_name", ""),
        "name": release.get("name", ""),
        "body": release.get("body", ""),
        "html_url": release.get("html_url", f"https://github.com/{repo}/releases"),
        "published_at": release.get("published_at", ""),
        "prerelease": bool(release.get("prerelease")),
        "assets": [
            {
                "name": asset.get("name", ""),
                "download_url": asset.get("browser_download_url", ""),
                "size": asset.get("size", 0),
            }
            for asset in release.get("assets", [])
            if isinstance(asset, dict)
        ],
    }
    return {
        "ok": True,
        "current_version": __version__,
        "repository": repo,
        "update_available": is_newer_version(latest_version, __version__),
        "no_release": False,
        "latest": latest,
        "release_url": latest["html_url"],
        "releases_url": f"https://github.com/{repo}/releases",
        "source_url": f"https://github.com/{repo}",
        "install_hint": _install_hint(repo),
        "check_source": check_source,
    }


async def _fetch_release(repo: str, include_prerelease: bool, proxy_url: str = "") -> dict[str, Any]:
    endpoint = f"{GITHUB_API}/repos/{repo}/releases"
    if not include_prerelease:
        endpoint += "/latest"

    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "DiceFrame update checker",
    }
    timeout = aiohttp.ClientTimeout(total=12)
    async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
        request_kwargs = {"proxy": proxy_url} if proxy_url else {}
        async with session.get(endpoint, **request_kwargs) as resp:
            data = await resp.json(content_type=None)
            if resp.status == 404:
                raise NoReleaseError("暂无公开 Release")
            if resp.status >= 400:
                message = data.get("message") if isinstance(data, dict) else await resp.text()
                raise RuntimeError(f"GitHub 返回 HTTP {resp.status}: {message}")
            if not include_prerelease:
                return data
            if not isinstance(data, list):
                raise RuntimeError("GitHub Release 返回格式异常")
            for release in data:
                if isinstance(release, dict) and not release.get("draft"):
                    return release
    raise RuntimeError("没有可用的 Release")


async def _fetch_release_for_api(
    api: "WebAPI",
    repo: str,
    include_prerelease: bool,
    proxy_url: str = "",
) -> tuple[dict[str, Any], dict[str, Any]]:
    plugin_host = getattr(api, "_plugins", None)
    mirrors = getattr(plugin_host, "mirrors", None)
    api_path = f"/repos/{repo}/releases"
    if not include_prerelease:
        api_path += "/latest"
    if mirrors is not None:
        result = await mirrors.fetch_github_api(api_path, official_first=True)
        if result.ok and isinstance(result.data, str):
            try:
                data = await _parse_release_payload(result.data, include_prerelease)
                source = result.to_dict()
                source.pop("data", None)
                return data, {"mode": "mirror", **source}
            except Exception as exc:
                logger.warning("镜像源返回的 Release 数据无法解析，回退 GitHub API：%s", exc)
        logger.warning("通过镜像源检查更新失败，回退 GitHub API：%s", result.error)
    release = await _fetch_release(repo, include_prerelease, proxy_url)
    return release, {"mode": "github-api", "mirror_name": "GitHub API"}


async def _parse_release_payload(payload: str, include_prerelease: bool) -> dict[str, Any]:
    import json

    data = json.loads(payload)
    if isinstance(data, dict) and data.get("message") == "Not Found":
        raise NoReleaseError("暂无公开 Release")
    if not include_prerelease:
        if not isinstance(data, dict):
            raise RuntimeError("GitHub Release 返回格式异常")
        return data
    if not isinstance(data, list):
        raise RuntimeError("GitHub Release 返回格式异常")
    for release in data:
        if isinstance(release, dict) and not release.get("draft"):
            return release
    raise RuntimeError("没有可用的 Release")


def _install_hint(repo: str) -> dict[str, str]:
    return {
        "windows": "下载新版源码包或 Release 附件，保留 data/ 目录后替换程序文件，再重新运行 web_ui.bat。",
        "docker": "如果使用镜像部署，拉取新版镜像后重新 docker compose up -d；如果是源码构建镜像，用新版源码重新 build。",
        "source": f"源码用户可从 https://github.com/{repo}/releases 下载新版，升级前先备份 data/。",
    }
