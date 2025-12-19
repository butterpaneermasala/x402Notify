"""
Lightweight RQ helpers for enqueuing x402 Notify jobs.

This module provides a small helper to enqueue notification jobs into Redis via RQ
and a worker-callable `run_notify_job` which re-creates a `NotifyClient` and
executes the notify flow in a separate process. This avoids blocking the web
server or main process while waiting for on-chain confirmations.

Usage (producer):

from x402_notify.queue import enqueue_notify
enqueue_notify(redis_url="redis://localhost:6379/0", wallet_key=..., gateway_url=..., chat_id="123", message="hi")

Run worker (in separate terminal/process):

# install RQ and redis-py (if not installed):
# pip install rq redis

# then start a worker that watches the default queue:
rq worker -u redis://localhost:6379/0

The worker will import this module and execute `run_notify_job` for enqueued tasks.
"""

from redis import Redis
from rq import Queue
from typing import Optional
from x402_notify.client import NotifyClient
import requests
import uuid


def run_notify_job(
    job_id: str,
    wallet_key: str,
    gateway_url: str,
    rpc_url: str,
    chain_id: int,
    chat_id: str,
    message: str,
    agent_tx: Optional[str] = None,
    callback_url: Optional[str] = None,
    **kwargs,
) -> dict:
    """Worker-callable: executes the full notify flow synchronously.

    This function is intentionally simple so RQ can import it and run it in
    a separate process. It returns the gateway response dict on success.
    """
    # Notify job started (callback)
    if callback_url:
        try:
            requests.post(f"{callback_url.rstrip('/')}/jobs/{job_id}/update", json={"status": "running"}, timeout=5)
        except Exception:
            pass

    client = NotifyClient(
        wallet_key=wallet_key,
        gateway_url=gateway_url,
        rpc_url=rpc_url,
        chain_id=chain_id,
    )

    try:
        res = client.notify(chat_id=chat_id, message=message, agent_tx=agent_tx, background=False)
        # Success callback
        if callback_url:
            try:
                requests.post(f"{callback_url.rstrip('/')}/jobs/{job_id}/update", json={"status": "finished", "result": res}, timeout=5)
            except Exception:
                pass
        return res
    finally:
        try:
            client.close()
        except Exception:
            pass


def enqueue_notify(
    redis_url: str,
    wallet_key: str,
    gateway_url: str,
    rpc_url: str,
    chain_id: int,
    chat_id: str,
    message: str,
    agent_tx: Optional[str] = None,
    queue_name: str = "default",
    callback_url: Optional[str] = None,
) -> str:
    """Enqueue a notify job into Redis RQ.

    Returns the job ID. The job will be processed by an RQ worker that must be
    running separately (see module docstring for `rq worker` command).
    """
    redis_conn = Redis.from_url(redis_url)
    q = Queue(name=queue_name, connection=redis_conn)
    # generate a stable job id so we can track it from the producer
    job_id = uuid.uuid4().hex
    job = q.enqueue(
        "x402_notify.queue.run_notify_job",
        job_id,
        wallet_key,
        gateway_url,
        rpc_url,
        chain_id,
        chat_id,
        message,
        agent_tx,
        callback_url=callback_url,
        job_id=job_id,
    )
    return job_id
