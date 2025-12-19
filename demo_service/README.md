Demo Agent Service (in-memory)
=================================

This lightweight FastAPI service demonstrates using the `x402-notify` SDK to send Telegram notifications where an agent signs the transaction (agent pays). It keeps subscriptions in memory only (no persistence).

Environment variables:
- `AGENT_PRIVATE_KEY`: hex private key for the agent (required to send actual transactions)
- `GATEWAY_URL`: gateway URL (optional)

Run locally:

```bash
python -m pip install -r demo_service/requirements.txt
export AGENT_PRIVATE_KEY="0x..."
uvicorn demo_service.app:app --reload --port 8001
```

Endpoints:
- `POST /subscribe` {"chat_id":"..."}
- `POST /unsubscribe` {"chat_id":"..."}
- `GET /status` -> {price, subscribers}
