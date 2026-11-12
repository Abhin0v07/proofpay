import os
import httpx
from dotenv import load_dotenv

load_dotenv()

BASE = "https://api-m.sandbox.paypal.com"
CLIENT_ID = os.getenv("PAYPAL_CLIENT_ID")
SECRET = os.getenv("PAYPAL_SECRET")
APP_URL = os.getenv("BASE_URL", "http://localhost:8000")
TIMEOUT = 30


def _check(r, label):
    if r.status_code >= 400:
        print(f"PAYPAL {label} ERROR:", r.status_code, r.text)
    r.raise_for_status()


def get_token() -> str:
    r = httpx.post(
        f"{BASE}/v1/oauth2/token",
        auth=(CLIENT_ID, SECRET),
        data={"grant_type": "client_credentials"},
        timeout=TIMEOUT,
    )
    _check(r, "TOKEN")
    return r.json()["access_token"]


def _headers() -> dict:
    return {
        "Authorization": f"Bearer {get_token()}",
        "Content-Type": "application/json",
    }


def create_order(amount: str) -> dict:
    """Create an order that only HOLDS the money (intent=AUTHORIZE)."""
    body = {
        "intent": "AUTHORIZE",
        "purchase_units": [
            {"amount": {"currency_code": "USD", "value": amount}}
        ],
        "payment_source": {
            "paypal": {
                "experience_context": {
                    "return_url": f"{APP_URL}/paypal/return",
                    "cancel_url": f"{APP_URL}/paypal/cancel",
                    "user_action": "PAY_NOW",
                }
            }
        },
    }
    r = httpx.post(
        f"{BASE}/v2/checkout/orders", json=body, headers=_headers(), timeout=TIMEOUT
    )
    _check(r, "CREATE ORDER")
    data = r.json()
    approve_url = next(
        l["href"] for l in data["links"] if l["rel"] in ("payer-action", "approve")
    )
    return {"order_id": data["id"], "approve_url": approve_url}


def authorize_order(order_id: str) -> str:
    """After the buyer approves, place the hold. Returns the authorization id."""
    r = httpx.post(
        f"{BASE}/v2/checkout/orders/{order_id}/authorize",
        headers=_headers(),
        timeout=TIMEOUT,
    )
    _check(r, "AUTHORIZE")
    data = r.json()
    return data["purchase_units"][0]["payments"]["authorizations"][0]["id"]


def capture(auth_id: str) -> dict:
    """Take the held money (work approved)."""
    r = httpx.post(
        f"{BASE}/v2/payments/authorizations/{auth_id}/capture",
        json={"final_capture": True},
        headers=_headers(),
        timeout=TIMEOUT,
    )
    _check(r, "CAPTURE")
    return r.json()


def void(auth_id: str) -> None:
    """Release the hold (work rejected)."""
    r = httpx.post(
        f"{BASE}/v2/payments/authorizations/{auth_id}/void",
        headers=_headers(),
        timeout=TIMEOUT,
    )
    _check(r, "VOID")