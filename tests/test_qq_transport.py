import pytest

from src.bots.qq.transport import NapCatTransport


def test_napcat_transport_raises_on_failed_action_response():
    with pytest.raises(RuntimeError, match="发送失败"):
        NapCatTransport._raise_if_failed(
            "send_private_msg",
            {
                "status": "failed",
                "retcode": 1200,
                "message": "发送失败，请先添加对方为好友",
            },
        )


def test_napcat_transport_accepts_success_action_response():
    NapCatTransport._raise_if_failed(
        "send_private_msg",
        {"status": "ok", "retcode": 0, "data": {"message_id": 1}},
    )
