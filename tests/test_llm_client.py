from __future__ import annotations

import pytest

from src.llm.client import LLMClient, ProviderConfig


class _FakeResponse:
    status = 200
    headers = {}
    request_info = None
    history = ()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def json(self):
        return {
            "content": [{"type": "text", "text": "OK"}],
            "usage": {"input_tokens": 3, "output_tokens": 2},
        }

    async def text(self):
        return ""


class _FakeSession:
    def __init__(self):
        self.calls = []

    def post(self, url, **kwargs):
        self.calls.append({"url": url, **kwargs})
        return _FakeResponse()


@pytest.mark.asyncio
async def test_anthropic_provider_uses_messages_api(monkeypatch):
    session = _FakeSession()
    client = LLMClient(
        providers=[
            ProviderConfig(
                provider_name="claude",
                base_url="https://api.anthropic.com",
                api_key="test-key",
                model_name="claude-test",
                api_format="anthropic",
            )
        ],
        default="claude",
    )

    async def fake_get_session():
        return session

    monkeypatch.setattr(client, "_get_session", fake_get_session)

    response = await client.call("system prompt", "hello", max_tokens=12, json_mode=True)

    assert response.content == "OK"
    assert response.total_tokens == 5
    call = session.calls[0]
    assert call["url"] == "https://api.anthropic.com/v1/messages"
    assert call["headers"]["x-api-key"] == "test-key"
    assert call["headers"]["anthropic-version"] == "2023-06-01"
    assert call["json"]["model"] == "claude-test"
    assert call["json"]["messages"] == [{"role": "user", "content": "hello"}]
    assert "temperature" not in call["json"]
    assert "system prompt" in call["json"]["system"]
    assert "Return only valid JSON" in call["json"]["system"]
