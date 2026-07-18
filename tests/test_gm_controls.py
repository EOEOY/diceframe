import pytest

from src.engine.game_instance import GameInstance, GameRegistry, GameState
from src.webui.routes.games import _should_rebind_player_session
from src.webui.services import characters, games
from src.webui.services._common import _GAME_KEY_SEP


class DummyAPI:
    def __init__(self, registry, cards_path=None):
        self._reg = registry
        self._character_cards_path = cards_path
        self._rules_dir = None

    def _parse_key(self, game_key: str) -> tuple:
        return tuple(game_key.split(_GAME_KEY_SEP))

    def _load_rule_for_game(self, inst):
        return None

    def save_character_card(self, character):
        from src.webui.services.character_cards import save_character_card

        return save_character_card(self, character)


@pytest.mark.asyncio
async def test_set_solo_mode_marks_pending_round_ready(tmp_path):
    registry = GameRegistry(tmp_path)
    key = ("web", "game", "bot")
    inst = GameInstance(game_key=key, state=GameState.ACTIVE_ACTION)
    inst.players["gm"] = {"character_name": "GM", "character_sheet": {"deceased": False}}
    inst.players["p1"] = {"character_name": "玩家", "character_sheet": {"deceased": False}}
    inst.action_queue.append({"user_id": "gm", "text": "继续"})
    registry.register(inst)

    result = await games.set_solo_mode(DummyAPI(registry), _GAME_KEY_SEP.join(key), True)

    assert result["ok"]
    assert inst.solo_mode is True
    assert inst.ready_players == {"gm", "p1"}


@pytest.mark.asyncio
async def test_gm_private_message_appends_private_log(tmp_path):
    registry = GameRegistry(tmp_path)
    key = ("web", "game", "bot")
    inst = GameInstance(game_key=key, state=GameState.ACTIVE_ACTION, round_number=3)
    inst.players["p1"] = {"character_name": "艾伦", "character_sheet": {"deceased": False}}
    registry.register(inst)

    result = await games.gm_private_message(
        DummyAPI(registry), _GAME_KEY_SEP.join(key), "p1", "你注意到门后有冷风。"
    )
    log = games.private_log(DummyAPI(registry), _GAME_KEY_SEP.join(key))

    assert result["ok"]
    assert inst.private_log["p1"][0]["source"] == "gm"
    assert log["messages"][0]["character_name"] == "艾伦"
    assert "冷风" in log["messages"][0]["text"]


def test_private_log_for_user_only_returns_own_messages(tmp_path):
    registry = GameRegistry(tmp_path)
    key = ("web", "game", "bot")
    inst = GameInstance(game_key=key, state=GameState.ACTIVE_ACTION, round_number=3)
    inst.players["p1"] = {"character_name": "艾伦", "character_sheet": {"deceased": False}}
    inst.players["p2"] = {"character_name": "贝拉", "character_sheet": {"deceased": False}}
    inst.private_log["p1"] = [{"round": 1, "text": "你听到门后有冷风。", "source": "gm"}]
    inst.private_log["p2"] = [{"round": 1, "text": "你发现窗边有脚印。", "source": "gm"}]
    registry.register(inst)

    log = games.private_log_for_user(DummyAPI(registry), _GAME_KEY_SEP.join(key), "p1")

    assert log["ok"] is True
    assert len(log["messages"]) == 1
    assert log["messages"][0]["user_id"] == "p1"
    assert "窗边" not in log["messages"][0]["text"]


def test_gm_session_does_not_rebind_when_opening_player_link():
    assert _should_rebind_player_session(
        "gm_uid",
        "gm_uid",
        "player_1",
        {"ok": True, "user_id": "player_1"},
        False,
    ) is False
    assert _should_rebind_player_session(
        "web_user",
        "gm_uid",
        "player_1",
        {"ok": True, "user_id": "player_1"},
        False,
    ) is True


@pytest.mark.asyncio
async def test_delete_character_cleans_player_runtime_state(tmp_path):
    registry = GameRegistry(tmp_path / "saves")
    key = ("web", "game", "bot")
    inst = GameInstance(game_key=key, state=GameState.ACTIVE_ACTION)
    inst.players["gm"] = {"character_name": "GM", "character_sheet": {"deceased": False}}
    inst.players["p1"] = {"character_name": "Player", "character_sheet": {"deceased": False}}
    inst.ready_players.add("p1")
    inst.action_queue.append({"user_id": "p1", "text": "act"})
    inst.pending_actions.append({"user_id": "p1", "text": "next"})
    inst.pending_payments.append({"id": "pay1", "uid": "p1", "status": "pending"})
    inst.private_log["p1"] = [{"text": "secret"}]
    registry.register(inst)

    result = await characters.delete_character(DummyAPI(registry), _GAME_KEY_SEP.join(key), "p1")

    assert result["ok"] is True
    assert "p1" not in inst.players
    assert "p1" not in inst.ready_players
    assert not inst.action_queue
    assert not inst.pending_actions
    assert not inst.pending_payments
    assert "p1" not in inst.private_log
