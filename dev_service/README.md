# Agent Dev Service (example)

This is a minimal example server that demonstrates the recommended "agent-pays" pattern:

- The developer runs a server-side agent service.
- The agent stores user `chat_id`s in its own DB (SQLite in this example).
- The agent holds a funded private key in an environment variable (or secret manager).
- When an event triggers, the agent calls the x402 SDK to pay and deliver a Telegram message via the gateway.

This example uses FastAPI.

## Setup

1. Create a virtualenv and install dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
# Install the local SDK (from this repo). From the repo root:
# cd sdk/python && pip install -e .
```

2. Configure environment (see `.env.example`):

```bash
cp .env.example .env
# Edit .env and set AGENT_PRIVATE_KEY and GATEWAY_URL
```

3. Run the service:

```bash
uvicorn app:app --reload --port 8001
```

## Endpoints

- `POST /subscribe` { "user_id": "dev-user-1", "chat_id": "123456" }
  - Store or update a mapping from `user_id` to `chat_id`.

- `POST /send/{user_id}` { "message": "Hello" }
  - Look up `chat_id` for `user_id` and call the SDK to send a notification (agent pays).

- `GET /users` - list subscriptions.

## Security
- Do NOT commit your `AGENT_PRIVATE_KEY` to source control.
- Use a secrets manager (Vault, AWS Secrets Manager) in production.
- Use a minimal funded wallet and rotate keys regularly.

## Notes
This example intentionally keeps logic simple and synchronous to be easy to follow. In production you should:
- Queue notifications and process them asynchronously.
- Add retries, error handling, and observability.
- Protect endpoints with authentication.
