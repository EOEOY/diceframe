"""Test: KEY_ITEM person-like name logs warning, still writes to loot."""

from __future__ import annotations

import logging

from src.commands.tag_parser import parse_tag_state


def test_person_key_item_still_goes_to_loot(caplog):
    text = (
        '---\n'
        'KEY_ITEM:alan:上个月前来调查的圆框眼镜年轻人\n'
        'KEY_ITEM:alan:切尔西提供的借阅登记条\n'
    )
    with caplog.at_level(logging.WARNING, logger="trpg"):
        data = parse_tag_state(text)

    loot = data["state_update"]["loot"]
    assert len(loot) == 2
    assert all(l["category"] == "key_item" for l in loot)

    person_item = next(l for l in loot if "年轻人" in l["item"])
    assert person_item["player"] == "alan"

    assert any("KEY_ITEM" in r.getMessage() for r in caplog.records)


def test_normal_key_item_no_warning(caplog):
    text = '---\nKEY_ITEM:user:年轻人的日记\n'
    with caplog.at_level(logging.WARNING, logger="trpg"):
        data = parse_tag_state(text)
    loot = data["state_update"]["loot"]
    assert len(loot) == 1
    assert not caplog.records


def test_loot_tag_never_warns(caplog):
    text = '---\nLOOT:user:可疑的陌生男子\n'
    with caplog.at_level(logging.WARNING, logger="trpg"):
        data = parse_tag_state(text)
    loot = data["state_update"]["loot"]
    assert len(loot) == 1
    assert loot[0].get("category") is None
    assert not caplog.records
