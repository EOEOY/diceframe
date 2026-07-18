"""上下文拼接器测试。"""

import pytest
from src.llm.context_builder import (
    _detect_max_chars, _estimate_tokens, _truncate, _format_history, build_context,
)


class TestDetectMaxChars:
    def test_deepseek(self):
        assert _detect_max_chars("deepseek") == 48640

    def test_qwen(self):
        assert _detect_max_chars("qwen") == 48640

    def test_gpt35(self):
        assert _detect_max_chars("gpt-3.5") == 16320

    def test_gpt4(self):
        assert _detect_max_chars("gpt-4") == 32640

    def test_claude(self):
        assert _detect_max_chars("claude") == 65536

    def test_unknown_model(self):
        assert _detect_max_chars("unknown-model") == 48000


class TestEstimateTokens:
    def test_empty(self):
        assert _estimate_tokens("") == 1

    def test_chinese(self):
        assert _estimate_tokens("你好世界") == 4

    def test_long_text(self):
        assert _estimate_tokens("a" * 1000) == 250


class TestTruncate:
    def test_no_truncation(self):
        assert _truncate("short", 100) == "short"

    def test_truncation(self):
        result = _truncate("very long text that exceeds limits", 15)
        assert len(result) <= 15
        assert result.endswith("...")


class TestFormatHistory:
    def test_empty(self):
        assert _format_history([], 1000) == ""

    def test_single_entry(self):
        log = [{
            "round": 1,
            "actions": [{"text": "攻击哥布林"}],
            "gm_response": "你击中了哥布林！",
        }]
        result = _format_history(log, 1000)
        assert "攻击哥布林" in result
        assert "你击中了哥布林" in result
        assert "Round 1" in result

    def test_truncation_by_budget(self):
        log = [
            {
                "round": i,
                "actions": [{"text": f"行动内容{i}" * 20}],
                "gm_response": f"GM回答{i}" * 20,
            }
            for i in range(1, 6)
        ]
        result = _format_history(log, 500)
        # 应该只包含后面的几轮
        assert "Round 1" not in result or "Round 5" in result


class DummyInstance:
    game_key = ("web", "dummy", "bot")
    summary = {}
    key_facts = []
    confirmed_items = []
    log = []

    def to_llm_view(self):
        return {
            "world_name": "测试世界",
            "round_number": 1,
            "scene": "测试场景",
            "players": {},
        }


@pytest.mark.asyncio
async def test_build_context_does_not_duplicate_system_prompt():
    context = await build_context(
        DummyInstance(),
        gm_prompt_filled="GM_SYSTEM_SENTINEL：你是测试 GM。",
        lorebook_entries=[{"type": "location", "name": "青石镇", "content": "镇外有一座旧祠。"}],
        player_message="我去旧祠看看。",
        provider_name="deepseek",
    )
    assert "GM_SYSTEM_SENTINEL" not in context
    assert "【游戏状态】" in context
    assert "【世界观知识】" in context
    assert "【玩家发言】" in context
