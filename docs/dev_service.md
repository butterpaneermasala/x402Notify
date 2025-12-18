**Agent Dev Service (example)**

This document describes the `dev_service` example included in the repo. It demonstrates how a developer should implement an agent that stores user chat ids and pays for notifications on behalf of users using the `x402-notify` Python SDK.

**Purpose**
- Show the recommended server-side pattern: the developer/agent stores `chat_id`, holds a funded private key on the server, and calls the SDK to perform payments and trigger message delivery.

**Files**
- `dev_service/app.py` - FastAPI example server.
- `dev_service/README.md` - run instructions and notes.
- `dev_service/.env.example` - environment variables template.

**Endpoints (example)**
- `POST /subscribe` { user_id, chat_id }
  - Store or update a subscription (maps `user_id` -> `chat_id`).

- `POST /send/{user_id}` { message }
  - Look up the `chat_id` and call `NotifyClient.notify(chat_id, message)`; the SDK performs the x402 payment flow and sends the message.

- `GET /users` - list current subscriptions.

**How it works (flow)**
1. User gets Chat ID from the Telegram bot (`/getId`) and gives it to the developer product.
2. Developer stores the `chat_id` in their DB (example uses SQLite).
3. When an event occurs, the developer's agent calls `NotifyClient.notify(chat_id, message)`.
   - SDK fetches the `x402` 402 response from the gateway.
   - SDK signs and broadcasts a payment on Base Sepolia using the stored private key.
   - SDK waits for confirmation and retries the gateway with `x-agent-payment-tx` header.
4. Gateway verifies the transaction and delivers the message to Telegram.

**Run locally (example)**

```bash
cd dev_service
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
# Install SDK from repo (from repo root):
# cd sdk/python && pip install -e .
# configure .env then run
uvicorn app:app --reload --port 8001
```

**Production recommendations**
- Do not block HTTP request handling while waiting for chain confirmations. Instead enqueue notifications and process them in a worker process.
- Store private keys in a secrets manager and rotate regularly.
- Use a minimal funded wallet and monitor balance and successful txs.
- Implement rate-limiting and idempotency; use tx hash to dedupe deliveries.
- Add authentication on endpoints and audit logging for payments.

**Integrating with the demo front-end**
- Update the demo to call a server endpoint (e.g., `POST /api/subscribe`) that proxies subscription actions to the developer service. The demo UI remains payment-free — the agent-service will handle payments when sending notifications.

**Further improvements**
- Use a transaction queue with retries and backoff.
- Add metrics (payments sent, notifications delivered, failures) and alerting.
- Provide an admin UI to view subscription lists and payment history.
