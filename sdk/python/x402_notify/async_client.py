"""Async wrapper for NotifyClient.

This provides an asyncio-friendly API by delegating work to a threadpool via
`asyncio.to_thread`. It lets async applications `await` notify calls while reusing
the existing synchronous `NotifyClient` implementation.
"""
import asyncio
from typing import Optional

from .client import NotifyClient


class AsyncNotifyClient:
    """Async wrapper around `NotifyClient`.

    Note: This wrapper currently delegates to the synchronous client using
    threads (`asyncio.to_thread`). It provides an async API without requiring
    a full rewrite to `web3.AsyncWeb3`.
    """

    def __init__(
        self,
        wallet_key: str,
        gateway_url: str = "http://localhost:3000",
        rpc_url: str = "https://sepolia.base.org",
        chain_id: int = 84532,
        **kwargs,
    ):
        self._client = NotifyClient(
            wallet_key=wallet_key,
            gateway_url=gateway_url,
            rpc_url=rpc_url,
            chain_id=chain_id,
            **kwargs,
        )

    async def notify(self, chat_id: str, message: str, agent_tx: Optional[str] = None, background: bool = False):
        """Async notify — delegates to `NotifyClient.notify` in a thread."""
        return await asyncio.to_thread(self._client.notify, chat_id, message, agent_tx, background)

    async def close(self, wait: bool = True):
        return await asyncio.to_thread(self._client.close, wait)

    async def get_stats(self):
        return await asyncio.to_thread(self._client.get_stats)

    # Context manager helpers for async with
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.close(wait=True)
