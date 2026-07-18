"""谜题系统测试。"""

import pytest
from src.engine.puzzle import (
    PuzzleInstance, PuzzleManager, PuzzleType, PuzzleState,
    create_puzzle_from_lorebook,
)


class TestPuzzleInstance:
    def test_create_riddle(self):
        p = PuzzleInstance(
            puzzle_id="test_1", name="谜题1",
            puzzle_type=PuzzleType.RIDDLE, solution="月光",
            description="什么东西夜里发光？",
            success_narration="答对了！",
            failure_narration="错了...",
        )
        assert p.state == PuzzleState.DORMANT
        assert p.can_attempt() is False

    def test_discover_and_activate(self):
        p = PuzzleInstance(puzzle_id="test_2", puzzle_type=PuzzleType.MECHANISM)
        p.discover()
        assert p.state == PuzzleState.DISCOVERED
        p.activate()
        assert p.state == PuzzleState.ACTIVE
        assert p.can_attempt() is True

    def test_attempts_exhausted(self):
        p = PuzzleInstance(puzzle_id="test_3", puzzle_type=PuzzleType.MECHANISM, max_attempts=2)
        p.activate()
        assert p.attempt() is True
        assert p.attempt() is False  # 用完
        assert p.state == PuzzleState.FAILED

    def test_solve(self):
        p = PuzzleInstance(puzzle_id="test_4", puzzle_type=PuzzleType.RIDDLE)
        p.activate()
        p.solve()
        assert p.state == PuzzleState.SOLVED
        assert p.is_solved() is True

    def test_to_dict(self):
        p = PuzzleInstance(
            puzzle_id="test_5", name="机关门",
            puzzle_type=PuzzleType.MECHANISM, required_skill="str", required_dc=15,
        )
        p.activate()
        d = p.to_dict()
        assert d["puzzle_id"] == "test_5"
        assert d["puzzle_type"] == "mechanism"
        assert d["state"] == "active"
        assert d["required_dc"] == 15


class TestPuzzleManager:
    def test_add_and_get(self):
        mgr = PuzzleManager()
        p = PuzzleInstance(puzzle_id="a", puzzle_type=PuzzleType.MECHANISM)
        mgr.add_puzzle(p)
        assert mgr.get_puzzle("a") is p

    def test_get_active(self):
        mgr = PuzzleManager()
        p1 = PuzzleInstance(puzzle_id="a", puzzle_type=PuzzleType.MECHANISM)
        p2 = PuzzleInstance(puzzle_id="b", puzzle_type=PuzzleType.RIDDLE)
        p1.activate()
        p2.discover()
        mgr.add_puzzle(p1)
        mgr.add_puzzle(p2)
        active = mgr.get_active_puzzles()
        assert len(active) == 1
        assert active[0].puzzle_id == "a"

    def test_riddle_answer(self):
        mgr = PuzzleManager()
        p = PuzzleInstance(
            puzzle_id="rid", puzzle_type=PuzzleType.RIDDLE,
            solution="月光", success_narration="正确！",
            failure_narration="错误。",
        )
        mgr.add_puzzle(p)
        p.activate()

        ok, msg = mgr.check_riddle_answer("rid", "答案是月光")
        assert ok is True
        assert "正确" in msg
        assert p.state == PuzzleState.SOLVED

    def test_riddle_wrong_answer(self):
        mgr = PuzzleManager()
        p = PuzzleInstance(
            puzzle_id="rid2", puzzle_type=PuzzleType.RIDDLE,
            solution="月光", max_attempts=5,
        )
        mgr.add_puzzle(p)
        p.activate()

        ok, msg = mgr.check_riddle_answer("rid2", "太阳")
        assert ok is False
        assert p.attempts == 1

    def test_skill_check_success(self):
        mgr = PuzzleManager()
        p = PuzzleInstance(
            puzzle_id="sk", puzzle_type=PuzzleType.MECHANISM,
            required_skill="str", required_dc=15,
            success_narration="推开了！",
        )
        mgr.add_puzzle(p)
        p.activate()

        ok, msg = mgr.check_skill_check(p, "str", 18)
        assert ok is True
        assert "推开" in msg

    def test_skill_check_failure(self):
        mgr = PuzzleManager()
        p = PuzzleInstance(
            puzzle_id="sk2", puzzle_type=PuzzleType.MECHANISM,
            required_skill="dex", required_dc=20, max_attempts=3,
        )
        mgr.add_puzzle(p)
        p.activate()

        ok, msg = mgr.check_skill_check(p, "dex", 10)
        assert ok is False
        assert p.attempts == 1

    def test_serialization_roundtrip(self):
        mgr = PuzzleManager()
        p1 = PuzzleInstance(
            puzzle_id="a", name="谜题A", puzzle_type=PuzzleType.RIDDLE,
            solution="答案", success_narration="对", failure_narration="错",
            required_dc=15, max_attempts=3,
        )
        p1.activate()
        mgr.add_puzzle(p1)

        data = mgr.to_dict()
        restored = PuzzleManager.from_dict(data)
        assert restored.get_puzzle("a").puzzle_id == "a"
        assert restored.get_puzzle("a").state == PuzzleState.ACTIVE
        assert restored.get_puzzle("a").solution == "答案"


class TestCreatePuzzleFromLorebook:
    def test_valid_puzzle_entry(self):
        entry = {
            "id": "puz_1", "name": "石门谜题", "type": "puzzle",
            "content": "一扇沉重的石门挡住了去路",
            "puzzle_type": "mechanism", "required_skill": "str",
            "required_dc": 18, "max_attempts": 3,
            "success_narration": "石门缓缓打开...",
            "failure_narration": "石门纹丝不动...",
        }
        p = create_puzzle_from_lorebook(entry)
        assert p is not None
        assert p.puzzle_id == "puz_1"
        assert p.puzzle_type == PuzzleType.MECHANISM
        assert p.required_dc == 18

    def test_non_puzzle_entry(self):
        entry = {"id": "npc_1", "name": "NPC", "type": "npc"}
        p = create_puzzle_from_lorebook(entry)
        assert p is None
