Queue demo
==========

This example shows how to subscribe a user, enqueue a notification job, and poll job status using the local `dev_service` and RQ worker.

Quick start
-----------

1. Create a `.env` in the repo root with at minimum `AGENT_PRIVATE_KEY=0x...`.
2. Start services:

```bash
docker compose up --build
```

3. Run the demo script (in another terminal):

```bash
python examples/queue_demo.py
```

Notes
-----
- The demo assumes `dev_service` is reachable at `http://localhost:8001` and Redis is running via the compose file. If you run services on different hosts, set `DEV_SERVICE_URL` or `DEV_SERVICE_API_KEY` as needed.
- If you don't want to use Docker, install dependencies locally (`pip install rq redis requests`) and run the worker with `rq worker -u redis://localhost:6379/0` before running this script.
