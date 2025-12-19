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
    # x402-Notify Python SDK

    Lightweight client to implement the x402 payment-required notification flow. The SDK handles: calling a gateway, detecting `402 Payment Required`, sending the agent-signed payment (EIP-1559 by default), and retrying the delivery with payment proof.

    Installation

    ```bash
    pip install x402-notify
    ```

    Quick start

    ```python
    from x402_notify import NotifyClient

    # Create a client (use a test key for local/integration tests)
    client = NotifyClient(
        wallet_key="0xYOUR_PRIVATE_KEY",
        gateway_url="http://127.0.0.1:8080",
        rpc_url="https://sepolia.public-rpc.example",
        chain_id=84531,
    )

    # Send a notification (SDK handles the on-chain payment flow)
    client.notify(chat_id="123456789", message="Hello from x402 SDK")
    ```

    Configuration options
    - `wallet_key` (required): hex private key used to sign the agent payment tx.
    - `gateway_url` (optional): gateway endpoint to call for delivery.
    - `rpc_url`, `chain_id` (optional): blockchain provider details for sending the payment.
    - `max_retries`, `timeout`, and logging configuration available via constructor args.

    Advanced usage
    - Background enqueueing and retry helpers are provided in `x402_notify.queue` for use with RQ/Redis.

    Testing & development
    - Run unit tests with `pytest` from the repo root.
    - To test the SDK against the local demo gateway, run the demo (`demo_service`) and point `gateway_url` at it.

    Troubleshooting
    - If imports fail in your editor, ensure the active Python interpreter points to the repo virtualenv or install the package (editable) with `pip install -e sdk/python`.
    - For RPC errors, check your `rpc_url` and `chain_id` values and ensure the account has test funds.

    Docs & contribution
    - API reference and design notes are in the `docs/` folder.
    - See `CONTRIBUTING.md` for how to run tests, format code, and submit PRs.
