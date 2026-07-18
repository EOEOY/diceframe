from __future__ import annotations

import os
import time

from src.bots.qq.card_renderer import cleanup_card_cache


def test_cleanup_card_cache_deletes_old_and_excess_files(tmp_path):
    card_dir = tmp_path / "cards"
    card_dir.mkdir()
    old = card_dir / "card_old.png"
    keep = card_dir / "card_keep.png"
    extra = card_dir / "card_extra.png"
    other = card_dir / "avatar.png"
    for path in (old, keep, extra, other):
        path.write_bytes(b"png")
    now = time.time()
    os.utime(old, (now - 48 * 3600, now - 48 * 3600))
    os.utime(keep, (now, now))
    os.utime(extra, (now - 60, now - 60))

    result = cleanup_card_cache(card_dir, max_age_hours=24, max_files=1)

    assert result["deleted"] == 2
    assert not old.exists()
    assert keep.exists()
    assert not extra.exists()
    assert other.exists()


def test_cleanup_card_cache_delete_all_only_removes_generated_cards(tmp_path):
    card_dir = tmp_path / "cards"
    card_dir.mkdir()
    generated = card_dir / "card_abc.png"
    unrelated = card_dir / "manual.png"
    generated.write_bytes(b"png")
    unrelated.write_bytes(b"do not touch")

    result = cleanup_card_cache(card_dir, delete_all=True)

    assert result["deleted"] == 1
    assert not generated.exists()
    assert unrelated.exists()
