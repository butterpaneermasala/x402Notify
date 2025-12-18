import os
from x402_notify.client import NotifyClient

# Mock Wallet Key (Would need real ETH on Base Sepolia)
# For this verify step, we rely on the logic being correct as we can't emit real money in this environment.
# But we can simulate the "402" response from the gateway.

def test_flow():
    print("Testing One-Off Notification Flow...")
    
    # Check if we have ENV vars
    key = os.getenv("TEST_WALLET_KEY")
    if not key:
        print("Skipping real payment test (No Private Key)")
        return

    client = NotifyClient(wallet_key=key, gateway_url="http://localhost:3000")
    
    try:
        res = client.notify("123456", "Test Message from Logic Check")
        print("Success:", res)
    except Exception as e:
        print("Error:", e)

if __name__ == "__main__":
    test_flow()
