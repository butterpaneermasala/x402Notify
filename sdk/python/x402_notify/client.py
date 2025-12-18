"""
x402 Notify Client
Handles the 402 payment flow automatically.
"""

import requests
from web3 import Web3
from eth_account import Account


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
        
        
        # Setup Web3
        self.w3 = Web3(Web3.HTTPProvider(rpc_url))
        self.account = Account.from_key(wallet_key)
        self.wallet_address = self.account.address
        
        print(f"[x402-Notify] Initialized with wallet: {self.wallet_address[:10]}...")

    def notify(self, chat_id: str, message: str, agent_tx: str = None) -> dict:
        """
        Send a notification to a Telegram chat.
        Handles x402 payment automatically.
        
        Args:
            chat_id: Telegram chat ID to send to
            message: Message content
            
        Returns:
            dict with success status and tx hash
        """
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
        """Send ETH payment to the gateway and wait for receipt."""
        nonce = self.w3.eth.get_transaction_count(self.wallet_address)
        
        # Simple gas estimation
        try:
            gas_price = self.w3.eth.gas_price
        except:
            gas_price = self.w3.to_wei('1', 'gwei') # Fallback

        tx = {
            "to": to_address,
            "value": self.w3.to_wei(amount_eth, "ether"),
            "gas": 21000,
            "gasPrice": gas_price,
            "nonce": nonce,
            "chainId": self.chain_id,
        }

        signed = self.w3.eth.account.sign_transaction(tx, self.wallet_key)
        tx_hash_bytes = self.w3.eth.send_raw_transaction(signed.rawTransaction)
        tx_hash = self.w3.to_hex(tx_hash_bytes)

        print(f"[x402-Notify] Transaction broadcast: {tx_hash}")
        print(f"[x402-Notify] Waiting for confirmation (this may take 15s)...")
        
        # In Strict x402, we MUST wait for the block to be mined 
        # so the Gateway can verify it's not just in the mempool
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
