**SDK Guide**

- **Purpose:** Python SDK `x402-notify` lets server-side agents send Telegram notifications via the x402 payment flow. The SDK handles the full sequence: request → receive 402 → pay on-chain → retry with proof.

- **Where:** `sdk/python/x402_notify/client.py` (class `NotifyClient`).

**Quick Install**

```bash
# from repo root
cd sdk/python
pip install -e .
```

**Quick Start (server-side agent)**

```python
from x402_notify import NotifyClient
import os

client = NotifyClient(
    wallet_key=os.environ['AGENT_PRIVATE_KEY'],  # keep this in env or secrets manager
    gateway_url='https://your-gateway.example',
    rpc_url='https://sepolia.base.org',
    chain_id=84532,
)

res = client.notify(chat_id='123456789', message='Hello from the agent')
print(res)
```

If you plan to use background mode or create short-lived clients, close the client when finished to
gracefully shutdown the internal thread pool:

```python
from x402_notify import NotifyClient
import os

client = NotifyClient(wallet_key=os.environ['AGENT_PRIVATE_KEY'])
future = client.notify('123', 'Hello background', background=True)
# do other work...
res = future.result(timeout=180)
print(res)

# Close when done to free threads
client.close()
```

Alternatively use the client as a context manager to auto-close:

```python
from x402_notify import NotifyClient
import os

with NotifyClient(wallet_key=os.environ['AGENT_PRIVATE_KEY']) as client:
  res = client.notify('123', 'Hi from context manager')
  print(res)
```

Running a minimal agent server (zero boilerplate)
------------------------------------------------

The SDK includes a convenience FastAPI app so developers can run a minimal server with almost no code:

```python
from x402_notify.agent_server import run_simple_agent
import os

run_simple_agent(
  wallet_key=os.environ['AGENT_PRIVATE_KEY'],
  gateway_url='http://localhost:3000',
  api_key='your-dev-api-key',
  port=8001,
)
```

This exposes `/subscribe` and `/send/{user_id}` endpoints and handles background delivery using the SDK.

**Agent-Pays Flow (recommended)**

- The developer/agent runs a server process that holds a funded private key (never put keys in the browser).
- The agent calls `NotifyClient.notify(chat_id, message)` which:
  1. `POST /notify` → receives HTTP 402 with `x402` payment instructions.
  2. Signs & broadcasts an on-chain payment to the gateway `payTo` address using the provided private key.
  3. Waits for on-chain confirmation (SDK waits for tx confirmation by default).
  4. Retries `POST /notify` with header `x-agent-payment-tx: <txHash>` so the gateway verifies and delivers the Telegram message.

This keeps the user UX payment-free while the agent covers costs.

Background workers (recommended for production)
-----------------------------------------------

If you don't want your web process to wait for on-chain confirmations (recommended), offload payments to a background worker. The SDK includes a tiny helper using RQ (Redis Queue).

Producer example (enqueue job):

```python
from x402_notify.queue import enqueue_notify

job_id = enqueue_notify(
  redis_url='redis://localhost:6379/0',
  wallet_key=os.environ['AGENT_PRIVATE_KEY'],
  gateway_url='http://localhost:3000',
  rpc_url='https://sepolia.base.org',
  chain_id=84532,
  chat_id='123456',
  message='Hello from queued worker',
)
print('enqueued', job_id)
```

Start a worker in a separate process to process jobs:

```bash
# install runtime deps if needed
pip install rq redis

# run worker attached to the default queue
rq worker -u redis://localhost:6379/0
```

The worker process will import `x402_notify.queue.run_notify_job` and execute the full notify flow there, so your web server never blocks waiting for blockchain confirmation.

Local development with Docker Compose
-----------------------------------

We include a `docker-compose.yml` that brings up Redis, the `dev_service` (uvicorn), and an `rq_worker` service for local testing.

Create a `.env` with your `AGENT_PRIVATE_KEY` and then run:

```bash
docker compose up --build
```

This starts Redis on port `6379` and the dev service on port `8001`. Use the dev service endpoints to subscribe and enqueue jobs during local development.

**Agent-supplied payment proof**

If a developer prefers to sign & broadcast transactions themselves (e.g., to control gas or use a payment pipeline), they can call the gateway directly and include the header `x-agent-payment-tx: 0x...` in the `POST /notify` request; the gateway will verify the tx and deliver the message.

Example (manual agent flow):

```python
# Dev broadcasts tx using their payment pipeline and gets tx_hash
tx_hash = '0xabc123...'

import requests

data = { 'chat_id': '123456789', 'message': 'Hi' }
headers = { 'x-agent-payment-tx': tx_hash }
res = requests.post('https://your-gateway.example/notify', json=data, headers=headers)
print(res.json())
```

**NotifyClient API (overview)**

- `NotifyClient(wallet_key, gateway_url='http://localhost:3000', rpc_url='https://sepolia.base.org', chain_id=84532, *, executor_workers=2, max_priority_gwei=2, max_fee_multiplier=2.0, gas_buffer_multiplier=1.1, rpc_retries=3, rpc_retry_delay=1.0)`
  - `wallet_key` (str): Private key the agent uses to sign payments.
  - `gateway_url` (str): Gateway base URL.
  - `rpc_url` / `chain_id`: Blockchain RPC and chain id used to send & confirm payments.
  - `executor_workers` (int): Number of background worker threads for `background=True` calls.
  - `max_priority_gwei` (int): Default max priority fee (gwei) used when building EIP-1559 txs.
  - `max_fee_multiplier` (float): Multiplier applied to the current block baseFee when computing `maxFeePerGas`.
  - `gas_buffer_multiplier` (float): Buffer multiplier applied to estimated gas to avoid underestimates.
  - `rpc_retries` / `rpc_retry_delay`: Retries and delay (seconds) for transient RPC failures.

- `notify(chat_id: str, message: str, agent_tx: str = None) -> dict`
  - If `agent_tx` (a real tx hash) is provided, the SDK will send a single request to the gateway with header `x-agent-payment-tx` and will not broadcast any transaction itself.
  - Otherwise the SDK executes the full x402 payment flow.

- `get_stats()` — requests `GET /stats/<wallet_address>` on the gateway (if implemented).

Async client (native)
---------------------

For async applications you can use a native async client which uses `web3.AsyncWeb3` and `httpx`:

```python
from x402_notify.async_native import AsyncNotifyClient
import os

async def send():
  async with AsyncNotifyClient(wallet_key=os.environ['AGENT_PRIVATE_KEY']) as client:
    res = await client.notify('123', 'Hello async world')
    print(res)

# Run via asyncio.run(send())
```

Note: `httpx` is required for the async client; install via `pip install httpx` or `pip install .[http]`.

**Security & Production Notes**

- Keep `wallet_key` in a secret store (environment variable, HashiCorp Vault, AWS Secrets Manager).
- Use a dedicated minimal-balance wallet for notifications; rotate keys and monitor balance.
- Use a background job queue for sending notifications (do not block HTTP request handlers while waiting for chain confirmations in production).
- Implement retries and idempotency (use transaction hash as dedupe key).
- Log only minimal metadata and avoid storing user PII in logs.

**Troubleshooting**

- `Unexpected response: 402` — SDK expects a 402 when a payment is required; it will then create a payment transaction.
- `Insufficient payment` — gateway rejects payment if the sent value is below the required amount. Ensure fees + value are correct.
- `Transaction not yet mined` — network or RPC latency. Increase RPC reliability or adjust confirmation waiting.

**References**

- Gateway README: `gateway/README.md`
- Example agent service: `dev_service/README.md` and `dev_service/app.py`
