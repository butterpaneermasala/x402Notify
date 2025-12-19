# x402-Notify Gateway

Permissionless notification gateway using x402 protocol.

## Deploy to Railway

[![Deploy on Railway](https://railway.app/button.svg)](https://railway.app/template)

### Environment Variables

| Variable | Description |
|----------|-------------|
| `TELEGRAM_BOT_TOKEN` | Your Telegram bot token from @BotFather |
| `GATEWAY_WALLET_ADDRESS` | Wallet address to receive x402 payments |
| `PORT` | Server port (default: 3000) |
| `RPC_URL` | JSON-RPC endpoint for Base Sepolia (default: `https://sepolia.base.org`) |
| `CHAIN_ID` | Expected chain id (default: `84532` for Base Sepolia) |
| `MIN_CONFIRMATIONS` | How many confirmations to wait for before delivering (default: `1`) |
| `MESSAGE_PRICE_ETH` | Price per message in ETH (default: `0.00001`) |
| `DEMO_TX_PREFIX` | Demo payment tx prefix accepted by gateway (default: `0x_DEMO_TX_`) |

| `REDIS_URL` | Redis connection URL for idempotent processed tx storage (optional, recommended for production) |

## Local Development

```bash
npm install
npm run dev
```

## API Endpoints

### POST /notify

Send a notification via x402.

**Request:**
```json
{
  "chat_id": "123456789",
  "message": "Hello from my agent!"
}
```

**Without payment → 402 Response:**
```json
{
  "error": "Payment Required",
  "x402": {
    "version": "1.0",
    "accepts": [{
      "scheme": "exact",
      "network": "base-sepolia",
      "maxAmountRequired": "0.00001",
      "payTo": "0x...",
      "asset": "ETH"
    }]
  }
}
```

**With payment header → 200 Response:**
```json
{
  "success": true,
  "txHash": "0x..."
}
```

Notes:
- The gateway will verify the payment transaction on the configured RPC network (default: Base Sepolia).
- For quick local demos (the React demo uses a mock tx hash starting with `0x_DEMO_TX_`), set `DEMO_TX_PREFIX` (or leave default) and the gateway will accept those demo txs without on-chain verification.

Redis idempotency (recommended):
- For safe, multi-instance deployments, set `REDIS_URL` (e.g. `redis://localhost:6379`). The gateway will use Redis to record processed tx hashes and avoid delivering duplicate messages across instances.
- If `REDIS_URL` is not set, gateway falls back to non-distributed behavior (no Redis idempotency). Previously the gateway used a file-backed cache; that has been replaced with Redis for production safety.

Agent-Pays mode
----------------

The gateway supports a developer-friendly "agent-pays" flow where end users do not need to pay — the agent (the service or SDK making calls on behalf of the user) covers message costs. For this:

- The agent should include a payment proof header when calling `POST /notify`: either `x-payment-tx` (existing) or `x-agent-payment-tx` (explicit agent-paid header).
- If the gateway receives a payment header, it will verify the transaction on-chain (or accept demo txs) and deliver the message without requiring the end user to perform any payment steps.
- If no payment header is provided, the gateway returns HTTP 402 with the `x402` payment instructions so an agent can pay and retry.

This makes it easy to keep user UX free while ensuring authors/operators of agents pay for notifications.

## Telegram Bot Commands

- `/start` - Welcome message + Chat ID
- `/getId` - Get your Chat ID
