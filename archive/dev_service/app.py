import os
import sqlite3
from typing import Optional
from fastapi import FastAPI, HTTPException, Header, Depends
from pydantic import BaseModel
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor
from fastapi import Request
import json
import uuid
import requests

# load env
load_dotenv()
DB_PATH = os.getenv("DB_PATH", "./dev_service.db")
AGENT_PRIVATE_KEY = os.getenv("AGENT_PRIVATE_KEY")
GATEWAY_URL = os.getenv("GATEWAY_URL", "http://localhost:3000")
# Optional API key to protect the dev service endpoints
DEV_SERVICE_API_KEY = os.getenv("DEV_SERVICE_API_KEY")

if not AGENT_PRIVATE_KEY:
    raise RuntimeError("AGENT_PRIVATE_KEY must be set in environment")

# SDK import (install package in editable mode during setup)
try:
    from x402_notify.client import NotifyClient
except Exception as e:
    raise RuntimeError("Cannot import x402_notify SDK. Install it (see dev_service/README.md)")

# Initialize SDK client (this will sign & send transactions)
client = NotifyClient(wallet_key=AGENT_PRIVATE_KEY, gateway_url=GATEWAY_URL)

# Simple thread pool for background delivery jobs
executor = ThreadPoolExecutor(max_workers=int(os.getenv("DEV_SERVICE_WORKERS", "2")))

app = FastAPI(title="Agent Dev Service (example)")

class SubscribeIn(BaseModel):
    user_id: str
    chat_id: str

class SendIn(BaseModel):
    message: str


class EnqueueIn(BaseModel):
    user_id: str
    message: str

# Initialize DB
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS subscriptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT UNIQUE NOT NULL,
            chat_id TEXT NOT NULL,
            created_at INTEGER DEFAULT (strftime('%s','now'))
        )
        """
    )
    # Delivery persistence intentionally omitted to keep this example simple.
    conn.commit()
    conn.close()

    # jobs table for enqueue/poll
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS jobs (
            job_id TEXT PRIMARY KEY,
            user_id TEXT,
            status TEXT,
            result TEXT,
            error TEXT,
            created_at INTEGER DEFAULT (strftime('%s','now')),
            updated_at INTEGER DEFAULT (strftime('%s','now'))
        )
        """
    )
    conn.commit()
    conn.close()

init_db()

def upsert_subscription(user_id: str, chat_id: str):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO subscriptions (user_id, chat_id) VALUES (?, ?)"
        " ON CONFLICT(user_id) DO UPDATE SET chat_id=excluded.chat_id",
        (user_id, chat_id),
    )
    conn.commit()
    conn.close()


def persist_job_record(job_id: str, user_id: str, status: str, result: Optional[dict] = None, error: Optional[str] = None):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        "INSERT OR REPLACE INTO jobs (job_id, user_id, status, result, error, created_at, updated_at) VALUES (?, ?, ?, ?, ?, COALESCE((SELECT created_at FROM jobs WHERE job_id = ?), strftime('%s','now')), strftime('%s','now'))",
        (job_id, user_id, status, json.dumps(result) if result else None, error, job_id),
    )
    conn.commit()
    conn.close()


def _process_delivery_simple(user_id: str, chat_id: str, message: str):
    try:
        # SDK handles the full payment flow (402 -> pay -> confirm -> retry)
        res = client.notify(chat_id, message)
        print(f"Delivery for user={user_id} completed: {res}")
    except Exception as e:
        # Log failure; SDK-level retries/handling should be implemented in SDK or by devs
        print(f"Delivery for user={user_id} failed: {e}")


@app.post("/enqueue")
async def enqueue(payload: EnqueueIn, request: Request, _=Depends(require_api_key)):
    # Find chat id
    chat_id = get_chat_id(payload.user_id)
    if not chat_id:
        raise HTTPException(status_code=404, detail="user not found")

    # callback URL the worker will POST updates to
    base = str(request.base_url).rstrip('/')

    # Enqueue via RQ helper
    from x402_notify.queue import enqueue_notify

    redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
    job_id = enqueue_notify(
        redis_url=redis_url,
        wallet_key=AGENT_PRIVATE_KEY,
        gateway_url=GATEWAY_URL,
        rpc_url=os.getenv('RPC_URL', 'https://sepolia.base.org'),
        chain_id=int(os.getenv('CHAIN_ID', 84532)),
        chat_id=chat_id,
        message=payload.message,
        callback_url=base,
    )

    # Persist job record
    persist_job_record(job_id, payload.user_id, 'queued')
    return {"ok": True, "job_id": job_id}


@app.post('/jobs/{job_id}/update')
async def job_update(job_id: str, payload: dict, _=Depends(require_api_key)):
    # Expected payload: { status: 'running'|'finished'|'failed', result?: {...}, error?: '...'}
    status = payload.get('status')
    result = payload.get('result')
    error = payload.get('error')

    # Update DB
    persist_job_record(job_id, payload.get('user_id', None), status, result, error)
    return {"ok": True}


@app.get('/jobs/{job_id}')
async def get_job(job_id: str, _=Depends(require_api_key)):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute('SELECT job_id, user_id, status, result, error, created_at, updated_at FROM jobs WHERE job_id = ?', (job_id,))
    row = cur.fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail='job not found')
    return {
        'job_id': row[0],
        'user_id': row[1],
        'status': row[2],
        'result': json.loads(row[3]) if row[3] else None,
        'error': row[4],
        'created_at': row[5],
        'updated_at': row[6],
    }


def require_api_key(x_api_key: Optional[str] = Header(None)):
    if DEV_SERVICE_API_KEY:
        if not x_api_key or x_api_key != DEV_SERVICE_API_KEY:
            raise HTTPException(status_code=401, detail="Invalid API key")

def get_chat_id(user_id: str) -> Optional[str]:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT chat_id FROM subscriptions WHERE user_id = ?", (user_id,))
    row = cur.fetchone()
    conn.close()
    return row[0] if row else None

@app.post("/subscribe")
async def subscribe(payload: SubscribeIn, _=Depends(require_api_key)):
    upsert_subscription(payload.user_id, payload.chat_id)
    return {"ok": True, "user_id": payload.user_id, "chat_id": payload.chat_id}

@app.post("/send/{user_id}")
async def send_to_user(user_id: str, payload: SendIn, _=Depends(require_api_key)):
    chat_id = get_chat_id(user_id)
    if not chat_id:
        raise HTTPException(status_code=404, detail="user not found")

    # Enqueue job using RQ helper if REDIS_URL configured, otherwise fall back to thread pool
    redis_url = os.getenv('REDIS_URL')
    if redis_url:
        from x402_notify.queue import enqueue_notify
        base = os.getenv('DEV_SERVICE_BASE_URL') or None
        callback = base if base else None
        job_id = enqueue_notify(
            redis_url=redis_url,
            wallet_key=AGENT_PRIVATE_KEY,
            gateway_url=GATEWAY_URL,
            rpc_url=os.getenv('RPC_URL', 'https://sepolia.base.org'),
            chain_id=int(os.getenv('CHAIN_ID', 84532)),
            chat_id=chat_id,
            message=payload.message,
            callback_url=callback,
        )
        persist_job_record(job_id, user_id, 'queued')
        return {"ok": True, "status": "queued", "job_id": job_id}
    else:
        # Submit background job that calls SDK (SDK handles payment/batching)
        executor.submit(_process_delivery_simple, user_id, chat_id, payload.message)
        return {"ok": True, "status": "queued"}

@app.get("/users")
async def list_users():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT user_id, chat_id, created_at FROM subscriptions ORDER BY created_at DESC")
    rows = cur.fetchall()
    conn.close()
    return [{"user_id": r[0], "chat_id": r[1], "created_at": r[2]} for r in rows]
