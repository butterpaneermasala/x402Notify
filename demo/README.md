# Whale Watcher Demo

Example app built using x402-Notify SDK.

## Deploy to Vercel

[![Deploy with Vercel](https://vercel.com/button)](https://vercel.com/new/clone)

### Environment Variables

| Variable | Description |
|----------|-------------|
| `VITE_GATEWAY_URL` | URL of your deployed Gateway (e.g., `https://gateway.railway.app`) |

## Local Development

```bash
npm install
npm run dev
```

## How It Works

1. User enters their Telegram Chat ID
2. Price simulator runs in the browser
3. When price crosses thresholds:
   - App calls Gateway's `/notify` endpoint
   - Gets `402 Payment Required`
   - In real SDK: pays via Base Sepolia
   - Gateway verifies payment & delivers Telegram message

## This is a DEMO

This app demonstrates what developers can build using the **x402-Notify SDK**.

The real product is:
- **Gateway**: The x402-powered API that delivers messages
- **SDK**: The library that handles payments automatically
