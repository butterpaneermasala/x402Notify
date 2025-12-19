"""Pure async Notify client using web3.AsyncWeb3 and httpx.

This implements the same x402 flow as `NotifyClient` but uses async primitives
so it can be integrated natively into async frameworks (FastAPI, etc.).
"""
from typing import Optional, Any
import asyncio
import json

import httpx
from web3 import AsyncWeb3
from web3.providers.async_rpc import AsyncHTTPProvider
from eth_account import Account


class AsyncNotifyClient:
    def __init__(
        self,
        wallet_key: str,
        gateway_url: str = "http://localhost:3000",
        rpc_url: str = "https://sepolia.base.org",
        chain_id: int = 84532,
        *,
        max_priority_gwei: int = 2,
        max_fee_multiplier: float = 2.0,
        gas_buffer_multiplier: float = 1.1,
        rpc_retries: int = 3,
        rpc_retry_delay: float = 1.0,
    ):
        self.gateway_url = gateway_url.rstrip("/")
        self.rpc_url = rpc_url
        self.chain_id = chain_id
        self.wallet_key = wallet_key

        # Fee / retry configuration
        self.max_priority_gwei = max_priority_gwei
        self.max_fee_multiplier = max_fee_multiplier
        self.gas_buffer_multiplier = gas_buffer_multiplier
        self.rpc_retries = rpc_retries
        self.rpc_retry_delay = rpc_retry_delay

        # Async Web3
        self.w3 = AsyncWeb3(AsyncHTTPProvider(rpc_url))
        self.account = Account.from_key(wallet_key)
        self.wallet_address = self.account.address

        # httpx client used for gateway interactions
        self._http_client: Optional[httpx.AsyncClient] = None

    async def _get_http(self) -> httpx.AsyncClient:
        if not self._http_client:
            self._http_client = httpx.AsyncClient()
        return self._http_client

    async def notify(self, chat_id: str, message: str, agent_tx: Optional[str] = None) -> Any:
        client = await self._get_http()
        endpoint = f"{self.gateway_url}/notify"
        payload = {"chat_id": chat_id, "message": message}

        if agent_tx:
            headers = {"x-agent-payment-tx": agent_tx}
            resp = await client.post(endpoint, json=payload, headers=headers, timeout=30)
            if resp.status_code == 200:
                return resp.json()
            raise Exception(f"Delivery failed using agent_tx: {resp.status_code} - {resp.text}")

        # Step 1: request without payment
        resp = await client.post(endpoint, json=payload, timeout=30)
        if resp.status_code == 200:
            return resp.json()
        if resp.status_code != 402:
            raise Exception(f"Unexpected response: {resp.status_code} - {resp.text}")

        data = resp.json()
        x402 = data.get("x402", {})
        accepts = x402.get("accepts", [])
        if not accepts:
            raise Exception("No payment methods in 402 response")

        payment_info = accepts[0]
        pay_to = payment_info["payTo"]
        amount_eth = payment_info["maxAmountRequired"]

        tx_hash = await self._send_payment_async(pay_to, amount_eth)

        headers = {"x-agent-payment-tx": tx_hash}
        res_retry = await client.post(endpoint, json=payload, headers=headers, timeout=30)
        if res_retry.status_code == 200:
            return res_retry.json()
        raise Exception(f"Delivery failed after payment: {res_retry.status_code} - {res_retry.text}")

    async def _rpc_with_retries(self, fn, *args, **kwargs):
        last_exc = None
        for _ in range(max(1, self.rpc_retries)):
            try:
                return await fn(*args, **kwargs)
            except Exception as e:
                last_exc = e
                await asyncio.sleep(self.rpc_retry_delay)
        # final attempt
        return await fn(*args, **kwargs)

    async def _send_payment_async(self, to_address: str, amount_eth: str) -> str:
        # nonce
        nonce = await self._rpc_with_retries(self.w3.eth.get_transaction_count, self.wallet_address)

        # Convert amount to wei (accepts numeric or string)
        value = AsyncWeb3.to_wei(amount_eth, "ether")

        # estimate gas
        gas_limit = 21000
        try:
            gas_est = await self._rpc_with_retries(self.w3.eth.estimate_gas, {"to": to_address, "from": self.wallet_address, "value": value})
            gas_limit = int(gas_est * self.gas_buffer_multiplier)
        except Exception:
            gas_limit = 21000

        tx = {
            "to": to_address,
            "value": value,
            "gas": gas_limit,
            "nonce": nonce,
            "chainId": self.chain_id,
        }

        try:
            block = await self._rpc_with_retries(self.w3.eth.get_block, "pending")
            base_fee = block.get("baseFeePerGas", None)
        except Exception:
            base_fee = None

        if base_fee:
            max_priority = AsyncWeb3.to_wei(self.max_priority_gwei, "gwei")
            max_fee = int(base_fee * self.max_fee_multiplier + max_priority)
            tx.update({
                "type": 2,
                "maxPriorityFeePerGas": max_priority,
                "maxFeePerGas": max_fee,
            })
        else:
            try:
                gas_price = await self._rpc_with_retries(self.w3.eth.gas_price)
            except Exception:
                gas_price = AsyncWeb3.to_wei("1", "gwei")
            tx.update({"gasPrice": gas_price})

        # sign (eth-account is synchronous)
        signed = Account.sign_transaction(tx, self.wallet_key)

        tx_hash_bytes = await self._rpc_with_retries(self.w3.eth.send_raw_transaction, signed.rawTransaction)
        tx_hash = self.w3.to_hex(tx_hash_bytes)

        receipt = await self._rpc_with_retries(self.w3.eth.wait_for_transaction_receipt, tx_hash_bytes, timeout=120)
        if receipt.status != 1:
            raise Exception("Payment transaction failed on-chain")
        return tx_hash

    async def get_stats(self) -> Any:
        client = await self._get_http()
        res = await client.get(f"{self.gateway_url}/stats/{self.wallet_address}")
        return res.json()

    async def close(self):
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None
        # Close web3 provider session if present
        provider = getattr(self.w3, "provider", None)
        sess = getattr(provider, "session", None)
        if sess is not None:
            try:
                await sess.close()
            except Exception:
                pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.close()
