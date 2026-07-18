"""骰子系统测试。"""

import pytest
from src.engine.dice import (
    DiceResult,
    check_coc,
    check_d100,
    check_d100_bonus,
    check_d20,
    check_d20_advantage,
    coc_success_level,
    parse_player_roll,
    roll,
)


class TestRoll:
    def test_d20(self):
        for _ in range(100):
            r = roll("d20")
            assert 1 <= r.total <= 20
            assert r.modifier == 0

    def test_d20_plus_mod(self):
        r = roll("d20+5")
        assert 6 <= r.total <= 25
        assert r.modifier == 5

    def test_2d6(self):
        for _ in range(100):
            r = roll("2d6")
            assert 2 <= r.total <= 12

    def test_d100(self):
        for _ in range(100):
            r = roll("d100")
            assert 1 <= r.total <= 100

    def test_invalid_formula(self):
        with pytest.raises(ValueError):
            roll("invalid")


class TestCheckD20:
    def test_critical_success(self, monkeypatch):
        monkeypatch.setattr("random.randint", lambda a, b: 20)
        result, verdict = check_d20(modifier=0, dc=15)
        assert verdict == "大成功"
        assert result.is_critical

    def test_fumble(self, monkeypatch):
        monkeypatch.setattr("random.randint", lambda a, b: 1)
        result, verdict = check_d20(modifier=5, dc=10)
        assert verdict == "大失败"
        assert result.is_fumble

    def test_success(self, monkeypatch):
        monkeypatch.setattr("random.randint", lambda a, b: 15)
        result, verdict = check_d20(modifier=2, dc=15)
        assert verdict == "成功"

    def test_failure(self, monkeypatch):
        monkeypatch.setattr("random.randint", lambda a, b: 8)
        result, verdict = check_d20(modifier=2, dc=15)
        assert verdict == "失败"

    def test_advantage_uses_higher_d20(self, monkeypatch):
        rolls = iter([7, 18])
        monkeypatch.setattr("random.randint", lambda a, b: next(rolls))

        result, verdict = check_d20_advantage(modifier=2, dc=15, advantage=True)

        assert result.rolls == [7, 18]
        assert result.natural == 18
        assert result.total == 20
        assert verdict == "成功"

    def test_disadvantage_uses_lower_d20(self, monkeypatch):
        rolls = iter([7, 18])
        monkeypatch.setattr("random.randint", lambda a, b: next(rolls))

        result, verdict = check_d20_advantage(modifier=2, dc=15, disadvantage=True)

        assert result.rolls == [7, 18]
        assert result.natural == 7
        assert result.total == 9
        assert verdict == "失败"

    def test_advantage_and_disadvantage_cancel(self, monkeypatch):
        monkeypatch.setattr("random.randint", lambda a, b: 12)

        result, verdict = check_d20_advantage(modifier=3, dc=15, advantage=True, disadvantage=True)

        assert result.rolls == [12]
        assert result.natural == 12
        assert result.total == 15
        assert verdict == "成功"


class TestCheckD100:
    def test_below_threshold(self, monkeypatch):
        monkeypatch.setattr("random.randint", lambda a, b: 45)
        _, verdict = check_d100(threshold=50)
        assert verdict == "成功"

    def test_above_threshold(self, monkeypatch):
        monkeypatch.setattr("random.randint", lambda a, b: 70)
        _, verdict = check_d100(threshold=50)
        assert verdict == "失败"

    def test_critical_success(self, monkeypatch):
        monkeypatch.setattr("random.randint", lambda a, b: 5)
        result, verdict = check_d100(threshold=50)
        assert verdict == "大成功"
        assert result.natural == 5

    def test_fumble(self, monkeypatch):
        monkeypatch.setattr("random.randint", lambda a, b: 96)
        result, verdict = check_d100(threshold=80)
        assert verdict == "大失败"
        assert result.natural == 96


class TestCheckD100Bonus:
    def test_bonus_dice_uses_best_tens(self, monkeypatch):
        rolls = iter([4, 8, 2])
        monkeypatch.setattr("random.randint", lambda a, b: next(rolls))
        result, verdict = check_d100_bonus(threshold=30, bonus_dice=1)
        assert result.total == 24
        assert verdict == "成功"

    def test_penalty_dice_uses_worst_tens(self, monkeypatch):
        rolls = iter([4, 2, 8])
        monkeypatch.setattr("random.randint", lambda a, b: next(rolls))
        result, verdict = check_d100_bonus(threshold=50, penalty_dice=1)
        assert result.total == 84
        assert verdict == "失败"

    def test_zero_zero_is_one_hundred(self, monkeypatch):
        rolls = iter([0, 0])
        monkeypatch.setattr("random.randint", lambda a, b: next(rolls))
        result, verdict = check_d100_bonus(threshold=99)
        assert result.total == 100
        assert verdict == "大失败"


class TestCheckCoc:
    def test_success_levels(self):
        assert coc_success_level(1, 60) == "大成功"
        assert coc_success_level(10, 60) == "极难成功"
        assert coc_success_level(30, 60) == "困难成功"
        assert coc_success_level(55, 60) == "普通成功"
        assert coc_success_level(70, 60) == "失败"
        assert coc_success_level(96, 40) == "大失败"

    def test_check_coc_uses_levels(self, monkeypatch):
        monkeypatch.setattr("random.randint", lambda a, b: 24)
        result, verdict = check_coc(60)
        assert result.natural == 24
        assert verdict == "困难成功"


class TestParsePlayerRoll:
    def test_parse_d20(self):
        r = parse_player_roll("掷骰 d20")
        assert r is not None

    def test_parse_2d6(self):
        r = parse_player_roll("/掷骰 2d6+1")
        assert r is not None
        assert "2d6" in r.formula

    def test_no_roll(self):
        assert parse_player_roll("我要攻击") is None
