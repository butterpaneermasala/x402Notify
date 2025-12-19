import os
import asyncio
from typing import Set
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
from pathlib import Path
from fastapi.staticfiles import StaticFiles

load_dotenv()

AGENT_PRIVATE_KEY = os.getenv("AGENT_PRIVATE_KEY")
GATEWAY_URL = os.getenv("GATEWAY_URL", "https://x402notify.onrender.com")

app = FastAPI(title="Demo Agent Service (in-memory)")

# CORS: allow the demo frontend to call the demo service (adjust origins in env if needed)
allowed_origins = os.getenv("DEMO_ALLOWED_ORIGINS", "*")
if allowed_origins == "*":
    origins = ["*"]
else:
    origins = [o.strip() for o in allowed_origins.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

# Serve the static demo frontend if available (demo_new directory at repo root)
static_dir = Path(__file__).resolve().parent.parent / "demo_new"
if static_dir.exists():
    app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="static")
    print(f"[static] Serving frontend from {static_dir}")
else:
    print(f"[static] demo_new folder not found at {static_dir}; frontend not served")


class SubIn(BaseModel):
    chat_id: str


# in-memory set of chat ids (no persistence)
subscribers: Set[str] = set()

# price simulation state
current_price = {"value": 3500, "phase": 0}

# ########## SDK START ##########
# SDK client (created if SDK available and AGENT_PRIVATE_KEY provided)
client = None
try:
    import importlib
    module = importlib.import_module("x402_notify.client")
    NotifyClient = getattr(module, "NotifyClient", None)
    if NotifyClient and AGENT_PRIVATE_KEY:
        client = NotifyClient(wallet_key=AGENT_PRIVATE_KEY, gateway_url=GATEWAY_URL)
    else:
        client = None
except Exception:
    client = None
# SDK END
# ########## SDK END ##########


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
    # send notifications concurrently without blocking the simulator
    async def _send(chat_id: str):
        try:
            # run the (possibly blocking) sync client.notify in a thread
            await asyncio.to_thread(client.notify, chat_id, message)
            print(f"[x402-Notify] Sent notification to {chat_id}")
        except Exception as exc:
            print(f"[x402-Notify] Error sending to {chat_id}: {exc}")

    # limit concurrent sends to avoid overwhelming local resources
    sem = asyncio.Semaphore(8)

    async def _send_with_sem(chat_id: str):
        async with sem:
            await _send(chat_id)

    tasks = [asyncio.create_task(_send_with_sem(c)) for c in list(subscribers)]
    # schedule background gather so notify_all returns quickly
    asyncio.create_task(asyncio.gather(*tasks, return_exceptions=True))
    print(f"[x402-Notify] Scheduled {len(tasks)} send tasks")


async def price_simulator():
    """Emit a smooth sine-wave price every second and notify on threshold crossings.

    Environment vars:
      DEMO_PERIOD: full sine period in seconds (default 120)
    """
    import time, math

    period = float(os.getenv("DEMO_PERIOD", "60"))
    amplitude = 510
    center = 3500   
    interval = 0.5
    start = time.time()
    prev_in_range = None

    iter_count = 0
    while True:
        try:
            t = time.time() - start
            price = int(center + amplitude * math.sin(2 * math.pi * t / period))
            current_price["value"] = price

            # periodic debug log every 10 iterations
            iter_count += 1
            if iter_count % 10 == 0:
                print(f"[sim] price={price} subscribers={len(subscribers)}")

            # detect crossing out of the safe range [3000,4000]
            in_range = 3000 <= price <= 4000
            if prev_in_range is None:
                prev_in_range = in_range
            else:
                if prev_in_range and not in_range:
                    if price > 4000:
                        msg = f"🚀 ETH surged above $4,000 — price {price}"
                    else:
                        msg = f"🔻 ETH dropped below $3,000 — price {price}"
                    print(msg)
                    # schedule notify and don't await long-running sends
                    try:
                        asyncio.create_task(notify_all(msg))
                    except Exception as exc:
                        print(f"[sim] failed to schedule notify_all: {exc}")
                prev_in_range = in_range

            await asyncio.sleep(interval)
        except Exception as exc:
            print(f"[sim] error in price_simulator loop: {exc}")
            await asyncio.sleep(1)


@app.on_event("startup")
async def startup_event():
    # start background price simulator and keep a reference for shutdown
    sim_task = asyncio.create_task(price_simulator())
    app.state.sim_task = sim_task
    print("[sim] price simulator started")


@app.on_event("shutdown")
async def shutdown_event():
    task = getattr(app.state, 'sim_task', None)
    if task and not task.done():
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            print('[sim] price simulator cancelled')
