from src.webui.sse_ticket import SseTicketStore


def test_sse_ticket_is_bound_to_game_and_single_use():
    store = SseTicketStore(ttl_seconds=30)
    token, expires_in = store.issue("web|room|bot", "player-1")

    assert expires_in == 30
    assert store.consume(token, "other-game") is None
    assert store.consume(token, "web|room|bot") is None

    token, _ = store.issue("web|room|bot", "player-1")
    ticket = store.consume(token, "web|room|bot")
    assert ticket is not None
    assert ticket.user_id == "player-1"
    assert store.consume(token, "web|room|bot") is None


def test_sse_ticket_rejects_unknown_value():
    store = SseTicketStore()
    assert store.consume("not-a-ticket", "game") is None
