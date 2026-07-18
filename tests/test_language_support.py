from pathlib import Path

import src.commands.prompt_composer as prompt_module
from src.commands.prompt_composer import PromptComposer
from src.engine.game_instance import GameInstance
from src.engine.language import gm_language_instruction, normalize_language


def test_language_normalization_accepts_english_aliases():
    assert normalize_language("en-US") == "en"
    assert normalize_language("english") == "en"
    assert normalize_language("zh_CN") == "zh-CN"
    assert normalize_language("unknown") == "zh-CN"


def test_game_instance_persists_language_roundtrip():
    inst = GameInstance(game_key=("web", "english_room", "bot"), language="en")

    data = inst.to_dict()
    restored = GameInstance.from_dict(data)

    assert data["language"] == "en"
    assert restored.language == "en"
    assert restored.to_llm_view()["language"] == "en"


def test_gm_prompt_appends_english_language_instruction(tmp_path: Path, monkeypatch):
    prompts = tmp_path / "prompts"
    rules = tmp_path / "rules"
    prompts.mkdir()
    rules.mkdir()
    (prompts / "gm_system_zh.md").write_text("BASE GM PROMPT", encoding="utf-8")
    inst = GameInstance(game_key=("web", "english_room", "bot"), language="en")
    monkeypatch.setattr(prompt_module, "_GM_PROMPT_CACHE", None)

    prompt = PromptComposer(prompts, rules).compose_gm_prompt(inst)

    assert "BASE GM PROMPT" in prompt
    assert "Player-facing GM narration" in prompt
    assert "QUICK_ACTIONS" in prompt


def test_language_instruction_keeps_protocol_tags_in_english_mode():
    instruction = gm_language_instruction("en")

    assert "HP" in instruction
    assert "GOLD" in instruction
    assert "LOOT" in instruction
    assert "SCENE" in instruction
