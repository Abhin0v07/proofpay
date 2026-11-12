import uuid
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from pydantic import BaseModel

import paypal
from judge import judge

app = FastAPI()
jobs = {}  # in-memory storage is fine for the hackathon


class NewJob(BaseModel):
    brief: str
    amount: str  # e.g. "25.00"


class Delivery(BaseModel):
    delivery: str


@app.get("/")
def home():
    return FileResponse("index.html")


@app.post("/api/jobs")
def create_job(job: NewJob):
    order = paypal.create_order(job.amount)
    job_id = str(uuid.uuid4())[:8]
    jobs[job_id] = {
        "brief": job.brief,
        "amount": job.amount,
        "order_id": order["order_id"],
        "auth_id": None,
        "status": "awaiting_buyer_approval",
    }
    return {"jobId": job_id, "approveUrl": order["approve_url"]}


@app.get("/paypal/return", response_class=HTMLResponse)
def paypal_return(token: str):
    for job in jobs.values():
        if job["order_id"] == token:
            job["auth_id"] = paypal.authorize_order(token)
            job["status"] = "held"
            return "<h2>Payment is on hold. You can close this tab.</h2>"
    raise HTTPException(404, "Unknown order")


@app.get("/paypal/cancel", response_class=HTMLResponse)
def paypal_cancel():
    return "<h2>Payment cancelled.</h2>"


@app.get("/api/jobs/{job_id}")
def get_job(job_id: str):
    if job_id not in jobs:
        raise HTTPException(404, "Job not found")
    return jobs[job_id]


@app.post("/api/jobs/{job_id}/deliver")
def deliver(job_id: str, body: Delivery):
    job = jobs.get(job_id)
    if not job or job["status"] != "held":
        raise HTTPException(400, "Job is not in the held state")

    # Step 1: the AI judges the delivery (PayPal is not touched yet)
    try:
        verdict = judge(job["brief"], body.delivery)
    except Exception as e:
        raise HTTPException(502, f"Judge failed: {e}")

    # Step 2: PayPal captures or voids the held money
    try:
        if verdict["approved"]:
            paypal.capture(job["auth_id"])
            job["status"] = "paid"
        else:
            paypal.void(job["auth_id"])
            job["status"] = "refunded"
    except Exception as e:
        raise HTTPException(502, f"PayPal failed: {e}")

    job["verdict"] = verdict
    return {"status": job["status"], "verdict": verdict}