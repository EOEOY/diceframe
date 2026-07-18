from src.webui.routes.sse import _event_cursor, _parse_event_cursor


def test_play_event_cursor_round_trip():
    event_id = _event_cursor(12, 4, '["action"]')
    assert event_id.startswith("r12.p4.a")
    assert _parse_event_cursor(event_id) == (12, 4)


def test_invalid_play_event_cursor_starts_from_zero():
    assert _parse_event_cursor("invalid") == (0, 0)
