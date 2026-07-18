"""LLM 输出解析器测试。"""

from src.llm.parser import ParsedResult, make_retry_message, parse_llm_response, sanitize_narration


class TestParseLLMResponse:
    def test_valid_json(self):
        raw = '铁门被你一脚踹开。\n\n```json\n{"state_update":{"players":{"123":{"hp_change":-5}}}}\n```'
        result = parse_llm_response(raw)
        assert not result.is_narration_only
        assert "铁门" in result.narration
        assert result.state_update == {"players": {"123": {"hp_change": -5}}}

    def test_no_json_block(self):
        raw = "只有叙事文本，没有 JSON。"
        result = parse_llm_response(raw)
        assert result.is_narration_only
        assert result.narration == raw

    def test_empty_input(self):
        result = parse_llm_response("")
        assert result.is_narration_only

    def test_narration_only_fallback(self):
        result = parse_llm_response("一些文字")
        assert result.is_narration_only
        assert result.narration == "一些文字"

    def test_full_output_structure(self):
        raw = '''GM叙述...
```json
{
  "state_update": {"players": {"a": {"hp_change": -5}}},
  "memory_delta": {"add": [{"entity": "铁牙组", "relation": "状态变更", "value": "总部被炸"}], "update": [], "forget": []},
  "info_asymmetry": {"user_b": "你看到暗门"}
}
```'''
        result = parse_llm_response(raw)
        assert not result.is_narration_only
        assert result.state_update is not None
        assert result.memory_delta is not None
        assert result.info_asymmetry == {"user_b": "你看到暗门"}

    def test_sanitize_narration_removes_internal_context_blocks(self):
        raw = "店小二压低声音。\n\n【局势分析（内部参考）】\n{\"risk\":\"leak\"}\n【玩家发言】\n向店小二询问后门"

        cleaned = sanitize_narration(raw)

        assert "店小二压低声音" in cleaned
        assert "局势分析" not in cleaned
        assert "玩家发言" not in cleaned


class TestMakeRetryMessage:
    def test_retry_format(self):
        msg = make_retry_message("原始提示词...", "JSON 格式错误")
        assert len(msg) > 0
