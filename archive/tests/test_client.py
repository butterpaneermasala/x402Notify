import pytest
from unittest.mock import patch, MagicMock

from x402_notify.client import NotifyClient
from x402_notify.async_client import AsyncNotifyClient


class DummyResponse:
    def __init__(self, status_code=200, json_data=None, text=""):
        self.status_code = status_code
        self._json = json_data or {}
        self.text = text

    def json(self):
        return self._json


@patch("x402_notify.client.requests.post")
def test_notify_flow_sync(mock_post):
    # First call returns 402 with x402 instructions
    mock_post.side_effect = [
        DummyResponse(status_code=402, json_data={"x402": {"accepts": [{"payTo": "0xAAA", "maxAmountRequired": "0.0001"}]}}),
        DummyResponse(status_code=200, json_data={"ok": True}),
    ]

    # Use a valid 32-byte hex private key for eth-account parsing
    valid_key = "0x" + "1" * 64
    client = NotifyClient(wallet_key=valid_key,
                          gateway_url="http://localhost:3000")

    # Patch _send_payment to avoid real web3 calls
    with patch.object(NotifyClient, "_send_payment", return_value="0xFAKE_TX"):
        res = client.notify("chatid", "hello")

    assert res == {"ok": True}


@patch("x402_notify.client.requests.post")
def test_notify_flow_async(mock_post):
    mock_post.side_effect = [
        DummyResponse(status_code=402, json_data={"x402": {"accepts": [{"payTo": "0xAAA", "maxAmountRequired": "0.0001"}]}}),
        DummyResponse(status_code=200, json_data={"ok": True}),
    ]

    valid_key = "0x" + "1" * 64
    async_client = AsyncNotifyClient(wallet_key=valid_key, gateway_url="http://localhost:3000")

    # patch underlying sync client's _send_payment
    with patch.object(NotifyClient, "_send_payment", return_value="0xFAKE_TX"):
        res = __import__('asyncio').run(async_client.notify("chatid", "hello"))

    assert res == {"ok": True}
