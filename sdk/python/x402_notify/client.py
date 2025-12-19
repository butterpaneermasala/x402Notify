"""
x402 Notify Client
Handles the 402 payment flow automatically.
"""

import requests
from web3 import Web3
from eth_account import Account
from concurrent.futures import ThreadPoolExecutor, Future
from typing import Optional
import time
import atexit


class NotifyClient:
    """
    Client for sending Telegram notifications via x402 protocol.
    
    Usage:
        client = NotifyClient(wallet_key="0x...")
        client.notify("chat_id_123", "Hello from my agent!")
    """

    def __init__(
        self,
        wallet_key: str,
        gateway_url: str = "http://localhost:3000",
        rpc_url: str = "https://sepolia.base.org",
        chain_id: int = 84532,
        *,
        executor_workers: int = 2,
        max_priority_gwei: int = 2,
        max_fee_multiplier: float = 2.0,
        gas_buffer_multiplier: float = 1.1,
        rpc_retries: int = 3,
        rpc_retry_delay: float = 1.0,
    ):
        """
        Initialize the NotifyClient.
        
        Args:
            wallet_key: Private key of the wallet that will pay for notifications
            gateway_url: URL of the x402-Notify gateway
            rpc_url: RPC URL for the blockchain
            chain_id: Chain ID (default: Base Sepolia)
        """
        self.gateway_url = gateway_url.rstrip("/")
        self.rpc_url = rpc_url
        self.chain_id = chain_id
        self.wallet_key = wallet_key
        
        # Background executor for non-blocking notify
        self._executor = ThreadPoolExecutor(max_workers=executor_workers)
        self._executor_workers = executor_workers

        # Fee / retry configuration
        self.max_priority_gwei = max_priority_gwei
        self.max_fee_multiplier = max_fee_multiplier
        self.gas_buffer_multiplier = gas_buffer_multiplier
        self.rpc_retries = rpc_retries
        self.rpc_retry_delay = rpc_retry_delay

        # Ensure executor is shut down on process exit
        atexit.register(self.close)
        
        # Setup Web3
        self.w3 = Web3(Web3.HTTPProvider(rpc_url))
        self.account = Account.from_key(wallet_key)
        self.wallet_address = self.account.address
        
        print(f"[x402-Notify] Initialized with wallet: {self.wallet_address[:10]}...")

    def notify(self, chat_id: str, message: str, agent_tx: Optional[str] = None, background: bool = False) -> dict | Future:
        endpoint = f"{self.gateway_url}/notify"
        payload = {"chat_id": chat_id, "message": message}

        # If agent already supplied a tx hash, use it directly
        if agent_tx:
            headers = {"x-agent-payment-tx": agent_tx}
            print(f"[x402-Notify] Using agent-supplied tx header: {agent_tx}")
            res = requests.post(endpoint, json=payload, headers=headers)
            if res.status_code == 200:
                return res.json()
            raise Exception(f"Delivery failed using agent_tx: {res.status_code} - {res.text}")

        # Step 1: Try without payment (expect 402)
        print(f"[x402-Notify] Sending notification to {chat_id}...")
        res = requests.post(endpoint, json=payload)

        if res.status_code == 200:
            # Already paid or free?
            return res.json()

        if res.status_code != 402:
            raise Exception(f"Unexpected response: {res.status_code} - {res.text}")

        # Step 2: Parse 402 response
        data = res.json()
        x402_data = data.get("x402", {})
        accepts = x402_data.get("accepts", [])

        if not accepts:
            raise Exception("No payment methods in 402 response")

        payment_info = accepts[0]
        pay_to = payment_info["payTo"]
        amount_eth = payment_info["maxAmountRequired"]

        print(f"[x402-Notify] Payment required: {amount_eth} ETH to {pay_to[:10]}...")

        # Step 3: Send payment
        tx_hash = self._send_payment(pay_to, amount_eth)
        print(f"[x402-Notify] Payment sent: {tx_hash[:20]}...")

        # Step 4: Retry with payment header (agent-paid header)
        headers = {"x-agent-payment-tx": tx_hash}
        res_retry = requests.post(endpoint, json=payload, headers=headers)

        if res_retry.status_code == 200:
            print(f"[x402-Notify] ✅ Notification delivered!")
            return res_retry.json()
        else:
            raise Exception(f"Delivery failed after payment: {res_retry.text}")
        
        # If background requested, submit sync task to executor and return a Future
        if background:
            future = self._executor.submit(self._notify_sync, chat_id, message, agent_tx)
            return future
        
        # Otherwise run synchronously and return result
        return self._notify_sync(chat_id, message, agent_tx)
    
    def _notify_sync(self, chat_id: str, message: str, agent_tx: Optional[str] = None) -> dict:
        """Synchronous implementation of notify flow. Can be run in background by `notify(..., background=True)`."""
        endpoint = f"{self.gateway_url}/notify"
        payload = {"chat_id": chat_id, "message": message}
        
        # If agent already supplied a tx hash, use it directly
        if agent_tx:
            headers = {"x-agent-payment-tx": agent_tx}
            print(f"[x402-Notify] Using agent-supplied tx header: {agent_tx}")
            res = requests.post(endpoint, json=payload, headers=headers)
            if res.status_code == 200:
                return res.json()
            raise Exception(f"Delivery failed using agent_tx: {res.status_code} - {res.text}")
        
        # Step 1: Try without payment (expect 402)
        print(f"[x402-Notify] Sending notification to {chat_id}...")
        res = requests.post(endpoint, json=payload)
        
        if res.status_code == 200:
            # Already paid or free?
            return res.json()
        
        if res.status_code != 402:
            raise Exception(f"Unexpected response: {res.status_code} - {res.text}")
        
        # Step 2: Parse 402 response
        data = res.json()
        x402_data = data.get("x402", {})
        accepts = x402_data.get("accepts", [])
        
        if not accepts:
            raise Exception("No payment methods in 402 response")
        
        payment_info = accepts[0]
        pay_to = payment_info["payTo"]
        amount_eth = payment_info["maxAmountRequired"]
        
        print(f"[x402-Notify] Payment required: {amount_eth} ETH to {pay_to[:10]}...")
        
        # Step 3: Send payment
        tx_hash = self._send_payment(pay_to, amount_eth)
        print(f"[x402-Notify] Payment sent: {tx_hash[:20]}...")
        
        # Step 4: Retry with payment header (agent-paid header)
        headers = {"x-agent-payment-tx": tx_hash}
        res_retry = requests.post(endpoint, json=payload, headers=headers)
        
        if res_retry.status_code == 200:
            print(f"[x402-Notify] ✅ Notification delivered!")
            return res_retry.json()
        else:
            raise Exception(f"Delivery failed after payment: {res_retry.text}")

    def _send_payment(self, to_address: str, amount_eth: str) -> str:
        """Send ETH payment to the gateway and wait for receipt.
        
        This function uses EIP-1559 fields when available and estimates gas.
        """
        nonce = self.w3.eth.get_transaction_count(self.wallet_address)
        
        value = self.w3.to_wei(amount_eth, "ether")
        
        # Helper for RPC calls with retries
        def _rpc_with_retries(fn, *args, **kwargs):
            last_exc = None
            for i in range(max(1, self.rpc_retries)):
                try:
                    return fn(*args, **kwargs)
                except Exception as e:
                    last_exc = e
                    time.sleep(self.rpc_retry_delay)
            # final attempt (let exceptions bubble)
            return fn(*args, **kwargs)

        # Estimate gas
        gas_limit = 21000
        try:
            gas_est = _rpc_with_retries(self.w3.eth.estimate_gas, {"to": to_address, "from": self.wallet_address, "value": value})
            gas_limit = int(gas_est * self.gas_buffer_multiplier)
        except Exception:
            gas_limit = 21000
        
        # Attempt EIP-1559 fees
        tx: dict = {
            "to": to_address,
            "value": value,
            "gas": gas_limit,
            "nonce": nonce,
            "chainId": self.chain_id,
        }
        
        try:
            block = _rpc_with_retries(self.w3.eth.get_block, "pending")
            base_fee = block.get("baseFeePerGas", None)
        except Exception:
            base_fee = None

        if base_fee:
            # Use a modest priority fee (configurable)
            max_priority = self.w3.to_wei(self.max_priority_gwei, "gwei")
            # max_fee = base_fee * multiplier + priority (configurable heuristic)
            max_fee = int(base_fee * self.max_fee_multiplier + max_priority)
            tx.update({
                "type": 2,
                "maxPriorityFeePerGas": max_priority,
                "maxFeePerGas": max_fee,
            })
        else:
            # Fallback to legacy gas price
            try:
                gas_price = self.w3.eth.gas_price
            except Exception:
                gas_price = self.w3.to_wei("1", "gwei")
            tx.update({"gasPrice": gas_price})
        
        signed = self.w3.eth.account.sign_transaction(tx, self.wallet_key)
        # web3.py naming differs between versions: support both `rawTransaction` and `raw_transaction`
        raw_tx = getattr(signed, "rawTransaction", None) or getattr(signed, "raw_transaction", None)
        if raw_tx is None:
            raise Exception("Signed transaction object missing raw bytes (rawTransaction/raw_transaction)")
        tx_hash_bytes = _rpc_with_retries(self.w3.eth.send_raw_transaction, raw_tx)
        tx_hash = self.w3.to_hex(tx_hash_bytes)
        
        print(f"[x402-Notify] Transaction broadcast: {tx_hash}")
        print(f"[x402-Notify] Waiting for confirmation (this may take 15s)...")
        
        try:
            receipt = _rpc_with_retries(self.w3.eth.wait_for_transaction_receipt, tx_hash_bytes, timeout=120)
        except Exception:
            # Final attempt without wrapper (will raise normally)
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash_bytes, timeout=120)
        
        if receipt.status != 1:
            raise Exception("Payment transaction failed on-chain")
        
        print(f"[x402-Notify] Transaction confirmed in block {receipt.blockNumber}")
        return tx_hash

    def get_stats(self) -> dict:
        """Get notification stats for this wallet."""
        endpoint = f"{self.gateway_url}/stats/{self.wallet_address}"
        res = requests.get(endpoint)
        return res.json()

    def close(self, wait: bool = True) -> None:
        """Shut down the internal threadpool executor used for background notifications.

        Args:
            wait: If True, wait for pending tasks to finish before returning.
        """
        try:
            self._executor.shutdown(wait=wait)
        except Exception:
            pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        # Ensure executor is closed when used as a context manager
        self.close(wait=True)
