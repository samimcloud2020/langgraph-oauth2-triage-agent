import os
import requests
from typing import Optional
from fastapi import FastAPI, HTTPException, Depends, Form
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="BSNL Ticket Triage Backend")
security = HTTPBearer()

HUBSPOT_ACCESS_TOKEN = os.getenv("HUBSPOT_ACCESS_TOKEN", "your_hubspot_token_here")

class TriageRequest(BaseModel):
    message: str
    thread_id: str
    username: str

# Helper function to categorize the customer issue
def categorize_issue(text: str) -> tuple[str, str]:
    text_lower = text.lower()
    
    if any(k in text_lower for k in ["bill", "payment", "charge", "invoice", "refund", "tariff", "recharge"]):
        return "Billing & Payments", "Billing & Account Services Section"
    elif any(k in text_lower for k in ["buy", "new connection", "plan upgrade", "sales", "purchase", "sim"]):
        return "Sales & New Connections", "Sales & Customer Onboarding Section"
    elif any(k in text_lower for k in ["slow", "down", "fault", "fiber", "modem", "broadband", "speed", "no signal", "router"]):
        return "Technical Fault", "Technical Operations & Network Maintenance Section"
    else:
        return "General Query", "Customer Support & Triage Section"

def create_hubspot_ticket(subject: str, content: str, priority: str = "HIGH") -> Optional[str]:
    url = "https://api.hubapi.com/crm/v3/objects/tickets"
    headers = {
        "Authorization": f"Bearer {HUBSPOT_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "properties": {
            "hs_pipeline": "0",
            "hs_pipeline_stage": "1",
            "hs_ticket_priority": priority,
            "subject": subject,
            "content": content
        }
    }

    try:
        res = requests.post(url, json=payload, headers=headers, timeout=15)
        if res.status_code == 201:
            return res.json().get("id")
        else:
            print(f"[HubSpot API Error {res.status_code}]: {res.text}")
            return None
    except Exception as e:
        print(f"[HubSpot Request Exception]: {e}")
        return None

@app.post("/login")
def login(username: str = Form(...), password: str = Form(...)):
    if username == "emp101" and password == "password123":
        return {
            "access_token": "mock-jwt-token-bsnl-101",
            "session_id": "sess-99201",
            "default_thread_id": "thread-bsnl-01"
        }
    raise HTTPException(status_code=401, detail="Invalid credentials")

@app.post("/triage")
def handle_triage(req: TriageRequest, credentials: HTTPAuthorizationCredentials = Depends(security)):
    # 1. Classify Category and Assigned Section
    category, assigned_section = categorize_issue(req.message)
    
    # 2. Create HubSpot Ticket
    subject = f"BSNL [{category}]: {req.message[:35]}..."
    content = f"Customer/Officer: {req.username}\nCategory: {category}\nAssigned Section: {assigned_section}\n\nDetails:\n{req.message}"
    
    ticket_id = create_hubspot_ticket(subject=subject, content=content)
    
    # 3. Format Dynamic Customer Confirmation Message
    if ticket_id:
        response_msg = (
            f"Dear Customer,\n\n"
            f"Your request regarding **{category}** has been recorded and successfully assigned to the **{assigned_section}** for resolution.\n\n"
            f"You can check out your resolution status anytime using your Ticket ID: `{ticket_id}`."
        )
        return {
            "response": response_msg,
            "ticket_id": ticket_id,
            "category": category,
            "assigned_section": assigned_section
        }
    else:
        return {
            "response": "Dear Customer,\n\nWe analyzed your query, but ticket registration failed due to a CRM service error. Please try again shortly.",
            "ticket_id": None
        }

@app.get("/triage/status/{ticket_id}")
def get_ticket_status(ticket_id: str, credentials: HTTPAuthorizationCredentials = Depends(security)):
    url = f"https://api.hubapi.com/crm/v3/objects/tickets/{ticket_id}"
    headers = {"Authorization": f"Bearer {HUBSPOT_ACCESS_TOKEN}"}
    
    res = requests.get(url, headers=headers)
    if res.status_code == 200:
        return res.json()
    elif res.status_code == 404:
        raise HTTPException(status_code=404, detail="Ticket ID not found in HubSpot.")
    else:
        raise HTTPException(status_code=res.status_code, detail=res.text)
