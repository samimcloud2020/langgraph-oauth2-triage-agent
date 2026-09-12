import os
import random
from typing import TypedDict, Sequence, Optional, Dict, Any
from dotenv import load_dotenv

load_dotenv()

from langchain_core.messages import BaseMessage, HumanMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY not found in environment or .env file.")

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

# ---------------------------------------------------------------------------
# State Definition
# ---------------------------------------------------------------------------
class CRMTriageState(TypedDict):
    messages: Sequence[BaseMessage]
    username: Optional[str]
    department: Optional[str]
    hubspot_ticket_id: Optional[str]
    response: Optional[str]


# ---------------------------------------------------------------------------
# Node 1: Classifier Node
# ---------------------------------------------------------------------------
async def classifier_node(state: CRMTriageState) -> Dict[str, Any]:
    latest_msg = state["messages"][-1].content
    
    prompt = (
        "Classify the following customer support issue into exactly ONE of these categories: "
        "'billing', 'technical', or 'sales'. Respond ONLY with the single category word in lowercase.\n\n"
        f"User Issue: {latest_msg}"
    )

    try:
        res = await llm.ainvoke([HumanMessage(content=prompt)])
        category = res.content.strip().lower().replace(".", "").replace("'", "")
        
        valid_categories = {"billing", "technical", "sales"}
        if category not in valid_categories:
            category = "technical" if "modem" in latest_msg.lower() else "billing"
    except Exception:
        lower_msg = latest_msg.lower()
        if any(w in lower_msg for w in ["bill", "invoice", "payment", "cost"]):
            category = "billing"
        elif any(w in lower_msg for w in ["modem", "install", "network", "router", "setup"]):
            category = "technical"
        else:
            category = "sales"

    return {"department": category}


# ---------------------------------------------------------------------------
# Node 2: Ticket Creation Node
# ---------------------------------------------------------------------------
async def hubspot_creator_node(state: CRMTriageState) -> Dict[str, Any]:
    mock_ticket_id = str(random.randint(3000000000, 3999999999))
    return {"hubspot_ticket_id": mock_ticket_id}


# ---------------------------------------------------------------------------
# Node 3: Responder Node (Generates Dynamic Bold Email Response)
# ---------------------------------------------------------------------------
async def responder_node(state: CRMTriageState) -> Dict[str, Any]:
    latest_msg = state["messages"][-1].content
    dept = state.get("department", "support")
    ticket_id = state.get("hubspot_ticket_id", "N/A")
    user_name = state.get("username", "Customer")

    # Dynamic bold email format
    email_response = (
        f"**Subject: Confirmation of Your Inquiry - Ticket #{ticket_id}**\n\n"
        f"**Dear {user_name},**\n\n"
        f"**Thank you for reaching out to us regarding your inquiry. We understand your concern, and we are here to assist you.**\n\n"
        f"**Your inquiry has been assigned Ticket #{ticket_id}. Our {dept.upper()} team will review the details of your request and get back to you as soon as possible with the necessary information and next steps.**\n\n"
        f"**If you have any additional details or documentation to share, please feel free to reply to this message. We appreciate your patience and look forward to resolving your issue promptly.**\n\n"
        f"**Best regards,**\n"
        f"**BSNL Customer Support Team**"
    )

    return {"response": email_response}


# ---------------------------------------------------------------------------
# Graph Assembly & Exports
# ---------------------------------------------------------------------------
checkpointer = MemorySaver()

def build_triage_graph():
    workflow = StateGraph(CRMTriageState)

    workflow.add_node("classifier", classifier_node)
    workflow.add_node("hubspot_creator", hubspot_creator_node)
    workflow.add_node("responder", responder_node)

    workflow.set_entry_point("classifier")
    workflow.add_edge("classifier", "hubspot_creator")
    workflow.add_edge("hubspot_creator", "responder")
    workflow.add_edge("responder", END)

    return workflow.compile(checkpointer=checkpointer)

graph = build_triage_graph()
triage_graph = graph
async_pool = None

async def get_ticket_status_async(ticket_id: str) -> Dict[str, Any]:
    return {
        "ticket_id": ticket_id,
        "status": "IN_PROGRESS",
        "department": "technical",
        "subject": "Vendor installation issue",
        "created_at": "2026-09-12T06:17:10Z"
    }
