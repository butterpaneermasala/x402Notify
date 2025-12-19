# x402-Notify

**Permissionless notification infrastructure for AI Agents**

> Send Telegram messages using x402 protocol. No API keys. No subscriptions. Just crypto.

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    x402-Notify                               │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│   /gateway         Node.js API that accepts x402 payments   │
│                    and delivers Telegram messages            │
│                                                              │
│   /sdk/python      Python SDK for developers                 │
│                    pip install x402-notify                   │
│                                                              │
│   /demo            Example "Whale Watcher" app               │
│                    Shows SDK integration                     │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## 🚀 Quick Start

### For Developers (using the SDK)

```python
from x402_notify import NotifyClient

# Initialize with your wallet
client = NotifyClient(wallet_key="0x...")

# Send notification - x402 payment handled automatically!
client.notify(
    chat_id="123456789",
    message="🚨 Alert from my agent!"
)
```

### For Users (getting Chat ID)

1. Open Telegram
2. Message [@x402aleartbot](https://t.me/x402aleartbot)
3. Send `/getId`
4. Copy your Chat ID

## 📁 Repository Structure

| Folder | Description | Deploy To |
|--------|-------------|-----------|
| `/gateway` | x402 API + Telegram Bot | Railway/Render |
| `/sdk/python` | Python SDK | PyPI |
| `/demo` | Whale Watcher example | Vercel |

## 🔧 Local Development

```bash
# Gateway
cd gateway
npm install
npm run dev

# Demo
cd demo
npm install
npm run dev
```

## 🌐 Network

- **Chain**: Base Sepolia (Testnet)
- **Chain ID**: 84532
- **Price**: 0.00001 ETH per message (~$0.02)

## 📜 License

MIT
