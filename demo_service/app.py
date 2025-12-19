import os
import asyncio
from typing import Set
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

AGENT_PRIVATE_KEY = os.getenv("AGENT_PRIVATE_KEY")
GATEWAY_URL = os.getenv("GATEWAY_URL", "https://x402notify.onrender.com")

app = FastAPI(title="Demo Agent Service (in-memory)")


class SubIn(BaseModel):
    chat_id: str


# in-memory set of chat ids (no persistence)
subscribers: Set[str] = set()

# price simulation state
current_price = {"value": 3500, "phase": 0}

# SDK client (created if SDK available and AGENT_PRIVATE_KEY provided)
client = None
try:
    from x402_notify.client import NotifyClient
    if AGENT_PRIVATE_KEY:
        client = NotifyClient(wallet_key=AGENT_PRIVATE_KEY, gateway_url=GATEWAY_URL)
    else:
        client = None
except Exception:
    client = None


@app.post("/subscribe")
async def subscribe(payload: SubIn):
    if not payload.chat_id:
        raise HTTPException(status_code=400, detail="chat_id required")
    subscribers.add(payload.chat_id)
    return {"ok": True, "subscribed": True, "count": len(subscribers)}


@app.post("/unsubscribe")
async def unsubscribe(payload: SubIn):
    if not payload.chat_id:
        raise HTTPException(status_code=400, detail="chat_id required")
    subscribers.discard(payload.chat_id)
    return {"ok": True, "subscribed": False, "count": len(subscribers)}


@app.get("/status")
async def status():
    return {"price": current_price["value"], "subscribers": list(subscribers)}


async def notify_all(message: str):
    if not subscribers:
        return
    if client is None:
        # SDK not configured; just log
        print("SDK client not configured; skipping notifications")
        return
    loop = asyncio.get_running_loop()
    for chat_id in list(subscribers):
        # run sync notify in executor to avoid blocking
        await loop.run_in_executor(None, lambda c=chat_id, m=message: client.notify(c, m))


async def price_simulator():
    """Every 60s toggle price between >4000 and <3000 and notify subscribers."""
    await asyncio.sleep(2)
    while True:
        # phase 0 -> cross above 4000
        current_price["value"] = 4005
        current_price["phase"] = 0
        msg = f"🚀 ETH surged above $4,000 — price {current_price['value']}"
        print(msg)
        await notify_all(msg)
        await asyncio.sleep(60)

        # phase 1 -> drop below 3000
        current_price["value"] = 2995
        current_price["phase"] = 1
        msg = f"🔻 ETH dropped below $3,000 — price {current_price['value']}"
        print(msg)
        await notify_all(msg)
        await asyncio.sleep(60)


@app.on_event("startup")
async def startup_event():
    # start background price simulator
    asyncio.create_task(price_simulator())
