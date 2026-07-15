"""System metadata routes."""

from __future__ import annotations

from aiohttp import web

from src.webui.routes._common import _get_api


async def api_update_check(request: web.Request) -> web.Response:
    include_prerelease = request.query.get("prerelease", "").lower() in {"1", "true", "yes"}
    return web.json_response(await _get_api(request).check_updates(include_prerelease))


def register_system(app: web.Application) -> None:
    app.router.add_get("/api/system/update-check", api_update_check)
