# x402-Notify Python SDK

Send permissionless Telegram notifications via x402 protocol.

## Installation

```bash
pip install x402-notify
```

## Quick Start

```python
from x402_notify import NotifyClient

# Initialize with your wallet's private key
client = NotifyClient(wallet_key="0x...")

# Send notification - x402 payment handled automatically!
client.notify(
    chat_id="123456789",
    message="🚨 ETH dropped below $2000!"
)
```

## How It Works

1. SDK calls the gateway's `/notify` endpoint
2. Gateway returns `402 Payment Required` with payment details
3. SDK automatically sends ETH payment to gateway
4. SDK retries request with payment proof
5. Gateway delivers message to Telegram

**No API keys. No subscriptions. Just crypto.**

## Configuration

```python
client = NotifyClient(
    wallet_key="0x...",
    gateway_url="https://notify.x402.io",  # Production gateway
    rpc_url="https://sepolia.base.org",    # Blockchain RPC
    chain_id=84532,                        # Base Sepolia
)
```

## Get Stats

```python
stats = client.get_stats()
print(f"Total notifications sent: {stats['totalNotifications']}")
```
