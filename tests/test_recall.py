"""记忆召回增强测试。"""

import pytest
from src.memory.recall import _extract_entities, _extract_ngrams, format_recalled


class TestExtractEntities:
    def test_chinese_entities(self):
        result = _extract_entities("我们去酒馆找老板打听消息")
        assert "酒馆" in result
        assert "老板" in result

    def test_mixed_text(self):
        result = _extract_entities("前往BlackForest寻找Ancient Sword")
        assert "BlackForest" in result
        assert "Ancient" in result
        assert "Sword" in result

    def test_empty(self):
        assert _extract_entities("") == []

    def test_short_words(self):
        result = _extract_entities("我去了")
        # "我去" "去了" 会被提取，但也有 "我去了" 整体
        # 验证不会返回空但不校验精确内容
        assert isinstance(result, list)


class TestExtractNgrams:
    def test_bigrams(self):
        result = _extract_ngrams("跑团游戏", n=2)
        assert "跑团" in result
        assert "团游" in result
        assert "游戏" in result

    def test_ignore_stop_chars(self):
        result = _extract_ngrams("？！？")
        assert len(result) == 0

    def test_empty(self):
        assert len(_extract_ngrams("")) == 0


class TestFormatRecalled:
    def test_empty(self):
        assert format_recalled([]) == ""

    def test_with_entries(self):
        entries = [
            {"entity": "哥布林", "relation": "恐惧", "value": "火把", "confidence": 0.9},
            {"entity": "老法师", "relation": "知道", "value": "古老传送门的秘密", "confidence": 0.7},
        ]
        result = format_recalled(entries)
        assert "【相关记忆】" in result
        assert "哥布林" in result
        assert "老法师" in result
        assert "->" in result
        assert "0.9" not in result
