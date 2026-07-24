from pathlib import Path

import pytest

from src.bots.bridge_core.client import DiceFrameClient, build_join_link
from src.bots.bridge_core.service import BridgeServiceConfig, DiceFrameBridgeService
from src.bots.bridge_core.store import JsonBridgeStore


def test_build_join_link_uses_hash_router_and_keeps_reverse_proxy_path():
    assert build_join_link("https://table.example/trpg", "web|game|bot") == (
        "https://table.example/trpg/#/join?game=web%7Cgame%7Cbot&share=1"
    )


@pytest.mark.asyncio
async def test_client_prefers_diceframe_public_address(monkeypatch):
    client = DiceFrameClient("http://diceframe:18000", "token")

    async def public_config():
        return {"public_base_url": "https://table.example/trpg"}

    monkeypatch.setattr(client, "public_config", public_config)
    assert await client.build_join_link("web|game|bot") == (
        "https://table.example/trpg/#/join?game=web%7Cgame%7Cbot&share=1"
    )


@pytest.mark.asyncio
async def test_bridge_explicit_public_address_overrides_server_setting(tmp_path: Path):
    class Client:
        base_url = "http://diceframe:18000"

        async def build_join_link(self, game_key: str, user: str = "") -> str:
            return build_join_link("https://server-setting.example", game_key, user)

    service = DiceFrameBridgeService(
        Client(),  # type: ignore[arg-type]
        JsonBridgeStore(tmp_path / "bridge.json"),
        BridgeServiceConfig(public_base_url="https://plugin-override.example"),
    )
    assert await service._join_link("web|game|bot", "player-1") == (
        "https://plugin-override.example/#/join?game=web%7Cgame%7Cbot&share=1&user=player-1"
    )
