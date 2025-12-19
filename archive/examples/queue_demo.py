#!/usr/bin/env python3
"""
Example: subscribe a demo user, enqueue a notification job, and poll job status.

Prereqs:
- Run `docker compose up --build` from the repo root (starts dev_service + redis + worker)
- Ensure `AGENT_PRIVATE_KEY` is set in the environment or in the compose .env

Usage:
    python examples/queue_demo.py
"""
import os
import time
import requests

DEV_SERVICE = os.environ.get("DEV_SERVICE_URL", "http://localhost:8001")
API_KEY = os.environ.get("DEV_SERVICE_API_KEY")

HEADERS = {"Content-Type": "application/json"}
if API_KEY:
    HEADERS["x-api-key"] = API_KEY


def subscribe(user_id: str, chat_id: str):
    url = f"{DEV_SERVICE}/subscribe"
    payload = {"user_id": user_id, "chat_id": chat_id}
    r = requests.post(url, json=payload, headers=HEADERS)
    r.raise_for_status()
    return r.json()


def enqueue(user_id: str, message: str):
    url = f"{DEV_SERVICE}/enqueue"
    payload = {"user_id": user_id, "message": message}
    r = requests.post(url, json=payload, headers=HEADERS)
    r.raise_for_status()
    return r.json().get("job_id")


def get_job(job_id: str):
    url = f"{DEV_SERVICE}/jobs/{job_id}"
    r = requests.get(url, headers=HEADERS)
    if r.status_code == 404:
        return None
    r.raise_for_status()
    return r.json()


def main():
    user_id = "demo-user"
    chat_id = os.environ.get("DEMO_CHAT_ID", "12345678")
    message = "Hello from queue_demo"

    print("Subscribing demo user...")
    subscribe(user_id, chat_id)
    print("Subscribed.")

    print("Enqueueing job...")
    job_id = enqueue(user_id, message)
    print("Enqueued job_id:", job_id)

    print("Polling job status...")
    timeout = 180
    start = time.time()
    while time.time() - start < timeout:
        job = get_job(job_id)
        if job is None:
            print("Job not found yet")
        else:
            status = job.get("status")
            print("status:", status)
            if status in ("finished", "failed"):
                print("job result:", job.get("result"))
                print("error:", job.get("error"))
                return
        time.sleep(3)

    print("Timed out waiting for job completion")


if __name__ == "__main__":
    main()
