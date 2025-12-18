from fastapi import FastAPI, HTTPException, Depends, Header
from pydantic import BaseModel
import sqlite3
import os
from typing import Optional
from concurrent.futures import ThreadPoolExecutor
from .client import NotifyClient


class SubscribeIn(BaseModel):
    user_id: str
    chat_id: str


class SendIn(BaseModel):
    message: str


def create_agent_app(wallet_key: str,
                     gateway_url: str = "http://localhost:3000",
                     db_path: str = "./agent_server.db",
                     api_key: Optional[str] = None,
                     workers: int = 2) -> FastAPI:
    """Create a minimal agent FastAPI app that stores subscriptions and sends notifications.

    This helper is intended so developers write almost no code: install the SDK and run this app.
    """
    app = FastAPI(title="x402 Agent Server")

    client = NotifyClient(wallet_key=wallet_key, gateway_url=gateway_url)
    executor = ThreadPoolExecutor(max_workers=workers)

    # DB init
    def init_db():
        conn = sqlite3.connect(db_path)
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
        conn.commit()
        conn.close()

    init_db()

    def upsert_subscription(user_id: str, chat_id: str):
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO subscriptions (user_id, chat_id) VALUES (?, ?)"
            " ON CONFLICT(user_id) DO UPDATE SET chat_id=excluded.chat_id",
            (user_id, chat_id),
        )
        conn.commit()
        conn.close()

    def get_chat_id(user_id: str) -> Optional[str]:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute("SELECT chat_id FROM subscriptions WHERE user_id = ?", (user_id,))
        row = cur.fetchone()
        conn.close()
        return row[0] if row else None

    def require_api_key(x_api_key: Optional[str] = Header(None)):
        if api_key:
            if not x_api_key or x_api_key != api_key:
                raise HTTPException(status_code=401, detail="Invalid API key")

    @app.post("/subscribe")
    async def subscribe(payload: SubscribeIn, _=Depends(require_api_key)):
        upsert_subscription(payload.user_id, payload.chat_id)
        return {"ok": True, "user_id": payload.user_id, "chat_id": payload.chat_id}

    def _process(user_id: str, chat_id: str, message: str):
        try:
            client.notify(chat_id, message)
        except Exception as e:
            # In production, wire up retries/alerts
            print(f"AgentServer delivery failed for {user_id}: {e}")

    @app.post("/send/{user_id}")
    async def send_to_user(user_id: str, payload: SendIn, _=Depends(require_api_key)):
        chat_id = get_chat_id(user_id)
        if not chat_id:
            raise HTTPException(status_code=404, detail="user not found")
        executor.submit(_process, user_id, chat_id, payload.message)
        return {"ok": True, "status": "queued"}

    @app.get("/users")
    async def list_users():
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute("SELECT user_id, chat_id, created_at FROM subscriptions ORDER BY created_at DESC")
        rows = cur.fetchall()
        conn.close()
        return [{"user_id": r[0], "chat_id": r[1], "created_at": r[2]} for r in rows]

    return app


def run_simple_agent(wallet_key: str,
                     gateway_url: str = "http://localhost:3000",
                     db_path: str = "./agent_server.db",
                     api_key: Optional[str] = None,
                     port: int = 8001):
    """Convenience runner for quick demos. Developers should run with Uvicorn in production.
    """
    try:
        import uvicorn
    except ImportError:
        raise RuntimeError("uvicorn is required to run the agent server (pip install uvicorn)")

    app = create_agent_app(wallet_key=wallet_key, gateway_url=gateway_url, db_path=db_path, api_key=api_key)
    uvicorn.run(app, host="0.0.0.0", port=port)
