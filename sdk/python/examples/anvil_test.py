#!/usr/bin/env python3
"""Quick Anvil test for x402 NotifyClient.

Usage:
  Set `ANVIL_PRIVATE_KEY` to your Anvil private key (or export it to use the default),
  ensure Anvil is running at `RPC_URL` (default `http://127.0.0.1:8545`) and run:

    python sdk/python/examples/anvil_test.py

This script will instantiate the `NotifyClient` and broadcast a small ETH
transfer to another local Anvil account to verify signing and confirmation.
"""
import os
import sys
import time

from x402_notify.client import NotifyClient


def main():
    rpc_url = os.environ.get("RPC_URL", "http://127.0.0.1:8545")
    priv = os.environ.get("ANVIL_PRIVATE_KEY")
    if not priv:
        print("ANVIL_PRIVATE_KEY not set — will attempt node-sent tx fallback (uses unlocked Anvil account).")

    # Use a short timeout-friendly chain id commonly used by Anvil/Hardhat
    chain_id = int(os.environ.get("CHAIN_ID", "31337"))

    # Create client (gateway not used for this test)
    # If ANVIL_PRIVATE_KEY is provided, use NotifyClient signing path.
    # Otherwise, fall back to sending via the node's unlocked account (Anvil exposes unlocked accounts).
    client = None
    if priv:
        client = NotifyClient(wallet_key=priv, rpc_url=rpc_url, gateway_url="http://127.0.0.1:9999", chain_id=chain_id)

    # Discover accounts on the node to pick a recipient (use second account if available)
    # Use the node's accounts list for recipient selection.
    tmp_w3 = None
    try:
        from web3 import Web3 as _Web3
        tmp_w3 = _Web3(_Web3.HTTPProvider(rpc_url))
    except Exception:
        tmp_w3 = None

    if client:
        accounts = client.w3.eth.accounts
    elif tmp_w3:
        accounts = tmp_w3.eth.accounts
    else:
        accounts = []

    if len(accounts) >= 2:
        to_addr = accounts[1]
    else:
        # fallback: send to self (just to ensure tx works)
        to_addr = None

    amount = "0.001"
    if client:
        src = client.wallet_address
        tgt = to_addr or client.wallet_address
        print(f"Sending {amount} ETH from {src} to {tgt} via {rpc_url} (signed locally)")
        try:
            tx_hash = client._send_payment(tgt, amount)
            print("TX hash:", tx_hash)
            print("Success: transaction confirmed")
        except Exception as e:
            print("Error while sending payment:", e)
            sys.exit(1)
    else:
        # Use node to send a transaction from the first account (no local signing required)
        if not tmp_w3:
            print("Cannot create RPC client to send transaction")
            sys.exit(1)
        node_accounts = tmp_w3.eth.accounts
        if not node_accounts:
            print("Node returned no accounts; ensure Anvil is running and RPC_URL is correct")
            sys.exit(1)
        src = node_accounts[0]
        tgt = to_addr or src
        print(f"Sending {amount} ETH from node account {src} to {tgt} via {rpc_url} (node-sent)")
        try:
            val = tmp_w3.to_wei(amount, "ether")
            tx_hash = tmp_w3.eth.send_transaction({"from": src, "to": tgt, "value": val})
            print("Broadcast tx hash:", tmp_w3.to_hex(tx_hash))
            print("Waiting for receipt...")
            receipt = tmp_w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
            if receipt.status == 1:
                print("Success: transaction confirmed in block", receipt.blockNumber)
            else:
                print("Tx failed on-chain: receipt:", receipt)
        except Exception as e:
            print("Error while sending transaction via node:", e)
            sys.exit(1)


if __name__ == "__main__":
    main()
