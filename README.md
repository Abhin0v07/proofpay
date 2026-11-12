# ProofPay

Pay only when the work is proven. The buyer's money is held by PayPal, an AI referee checks the delivery against the brief, then PayPal captures the payment or voids the hold.

## How it works
1. Buyer posts a brief and an amount. PayPal creates an order with `intent=AUTHORIZE`, so the money is held, not charged.
2. Seller submits the delivery.
3. A Gemini AI referee turns the brief into a checklist, scores each item pass or fail with a reason, and approves or rejects.
4. Approved: PayPal **captures** the authorization (seller is paid). Rejected: PayPal **voids** it (buyer keeps the money).

## Built with
- PayPal Orders and Payments APIs (sandbox): authorize, capture, void
- Google Gemini for the AI referee
- Python, FastAPI, HTML/JavaScript

## Run it
1. At developer.paypal.com, create a free sandbox app (type Merchant) linked to a **US** sandbox business account. Also create a **US** sandbox personal account to act as the buyer.
2. Install:
```
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```
3. Create a `.env` file in the project folder:
```
PAYPAL_CLIENT_ID=your_sandbox_client_id
PAYPAL_SECRET=your_sandbox_secret
BASE_URL=http://localhost:8000
GEMINI_API_KEY=your_gemini_key
GEMINI_MODEL=gemini-3.6-flash
```
4. Start the server: `uvicorn main:app --reload`, then open http://localhost:8000
5. Click "Create job and hold payment", then "Approve payment on PayPal" and log in with your sandbox **personal** (buyer) account. Submit a delivery and watch the referee decide.

Optional: set `ALLOW_FALLBACK=1` in `.env` to use a simple keyword check if Gemini is temporarily unavailable. The demo uses the real Gemini referee.

Sandbox only: no real money moves. The referee reads a text description of the delivery.

## Why it matters
Non-delivery and disputes erode trust in online payments. ProofPay protects buyers, gives sellers certainty that approved work is paid, and means more completed PayPal transactions with fewer disputes.

## Next steps
Milestone payments with partial capture, a dispute evidence report, PayPal webhooks, and a human override for borderline cases.

License: MIT
