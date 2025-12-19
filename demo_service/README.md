Demo Agent Service (in-memory)
=================================

This lightweight FastAPI service demonstrates using the `x402-notify` SDK to send Telegram notifications where an agent signs the transaction (agent pays). It keeps subscriptions in memory only (no persistence).

Environment variables:
- `AGENT_PRIVATE_KEY`: hex private key for the agent (required to send actual transactions)
- `GATEWAY_URL`: gateway URL (optional)

Run locally:

Demo Agent Service (in-memory)
=================================

What this is
- A minimal FastAPI agent that demonstrates the `x402-notify` flow: subscribers can register a Telegram `chat_id`, and the demo will call the SDK to send messages when simulated price events occur.
- Subscriptions are kept in memory (for demo/testing only).

Prerequisites
- Python 3.10+ and a virtual environment.
- (Optional) A funded agent private key and access to a test RPC if you want to actually send payment transactions.

Environment variables
- `AGENT_PRIVATE_KEY` (required for on-chain sends): example `0xabc...`
- `GATEWAY_URL` (optional): URL of the gateway to call (default: local/demo gateway if configured)
- `DEMO_PERIOD` (optional): simulator period in seconds (controls the sine-wave price simulator)

Install & run (recommended from repo root)

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r demo_service/requirements.txt
export AGENT_PRIVATE_KEY="0x..."
uvicorn demo_service.app:app --reload --port 8001
```

If you prefer to `cd demo_service/` first, run `uvicorn app:app --reload --port 8001` instead — the module import path differs when running inside the folder.

API examples
- Subscribe a chat id:

```bash
curl -X POST http://127.0.0.1:8001/subscribe \
	-H "Content-Type: application/json" \
	-d '{"chat_id":"123456789"}'
```

- Unsubscribe:

```bash
curl -X POST http://127.0.0.1:8001/unsubscribe \
	-H "Content-Type: application/json" \
	-d '{"chat_id":"123456789"}'
```

- Status (current price + subscriber list):

```bash
curl http://127.0.0.1:8001/status
```

Notes & troubleshooting
- This demo uses the published `x402-notify` Python package if installed; to test the local SDK code, install the package from the repo with `pip install -e sdk/python`.
- CORS: the service includes permissive CORS to allow a static demo frontend to poll `/status`.
- Data is in-memory: restarting the process clears subscribers.

Next steps
- Use the `demo_new/` static frontend (if present) to exercise subscribe/unsubscribe flows visually.

Deploying to Render
-------------------

This repository includes a `render.yaml` manifest that deploys the demo as a Python web service on Render. The manifest uses `uvicorn demo_service.app:app` and exposes `/status` as a health check.

Steps:

1. Push this repository to GitHub (if not already).
2. Create a new Web Service on Render and connect your GitHub repo.
3. Render will detect `render.yaml` and use the specified build/start commands.
4. In the Render dashboard, set the `AGENT_PRIVATE_KEY` environment variable (mark it private). Optionally set `GATEWAY_URL`, `DEMO_ALLOWED_ORIGINS`, and `DEMO_PERIOD`.

Example: useful env vars

- `AGENT_PRIVATE_KEY` — your agent's private key (keep secret)
- `GATEWAY_URL` — gateway to use for delivery (defaults to `https://x402notify.onrender.com`)
- `DEMO_ALLOWED_ORIGINS` — origins allowed for the frontend (default `*`)
- `DEMO_PERIOD` — simulator period in seconds (default `60`)

After deploy, open the service URL (Render will provide it) and the frontend will be served at `/` while API endpoints are under the same host.
