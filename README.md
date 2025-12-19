x402-Notify — SDK + demo for permissionless Telegram notifications
===============================================================

This repository contains the core Python SDK (`sdk/python/x402_notify`) and a lightweight demo agent service that shows how an agent can pay on-chain to send Telegram notifications using the x402 "Payment Required" flow.

What you'll find here
- **`sdk/python/`** — Python SDK (`x402_notify`) with `NotifyClient` and helpers.
- **`demo_service/`** — FastAPI in-memory demo agent service (subscribe/unsubscribe/status).
- **`docs/`** — Design notes and protocol references.
- **`.github/`** — CI workflows (build, tests, publish).

Quickstart (run demo locally)
1. Create and activate a virtualenv from the repo root:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r demo_service/requirements.txt
```

2a. Run from repo root (recommended):

```bash
uvicorn demo_service.app:app --reload --port 8001
```

2b. Or run from inside `demo_service/`:

```bash
cd demo_service
uvicorn app:app --reload --port 8001
```

3. Use the demo frontend (if present) or `curl` to subscribe:

```bash
curl -X POST http://127.0.0.1:8001/subscribe -H "Content-Type: application/json" -d '{"chat_id":"123456789"}'
```

More details and SDK usage are in `sdk/python/README.md` and `demo_service/README.md`.

Contributing
- See `CONTRIBUTING.md` for contribution guidelines and how to run tests.

License
- Check `LICENSE` in the repository root (if present).
