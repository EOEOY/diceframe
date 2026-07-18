"""回合状态变动播报测试。"""

from __future__ import annotations

from src.commands.game_handler import (
    _build_state_change_messages,
    _snapshot_public_player_state,
)
from src.engine.game_instance import GameInstance


def test_state_change_messages_include_hp_loot_and_quests():
    instance = GameInstance(("web", "group", "bot"))
    instance.players["web_user"] = {
        "character_name": "艾琳",
        "character_sheet": {
            "hp": 46,
            "max_hp": 46,
            "gold": 30,
            "inventory": [],
            "equipment": [],
            "key_items": [],
        },
    }
    before = _snapshot_public_player_state(instance)

    cs = instance.players["web_user"]["character_sheet"]
    cs["hp"] = 44
    cs["inventory"].append({"name": "老格雷的细磨刀石", "qty": 1})

    data = {
        "state_update": {
            "players": {"web_user": {"hp_change": -2}},
            "loot": [{"player": "web_user", "item": "老格雷的细磨刀石"}],
        },
        "plot_update": {
            "quests": [
                {"title": "完成训练场等级评价", "status": "completed"},
                {"title": "选择第一个冒险任务", "status": "active"},
            ],
        },
    }

    messages = _build_state_change_messages(instance, before, data)

    assert "【状态变动】艾琳：HP 46 → 44（-2）；获得 老格雷的细磨刀石 x1" in messages
    assert "【任务更新】完成训练场等级评价：已完成" in messages
    assert "【任务更新】选择第一个冒险任务：进行中" in messages
