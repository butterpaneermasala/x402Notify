# Whale Watcher — Static Demo

This is a small static demo that simulates an ETH price feed and allows a user to subscribe/unsubscribe locally. Subscriptions are stored in `localStorage` and no network calls are made.

How it works:
- The feed simulates price data and toggles between crossing ≥4000 and dropping ≤3000 every minute.
- When the simulated price crosses the thresholds, a notification is added to the Events log and 'Delivered to subscribers (simulated)' is added when subscribed.

To run:
1. Open `demo/index.html` in a browser (no server required).
2. Enter an identifier in the input (optional) and click Subscribe.
