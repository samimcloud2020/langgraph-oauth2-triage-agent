from typing import Annotated, List, Literal, TypedDict
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages

Department = Literal["sales", "support", "billing", "general"]

class CRMTriageState(TypedDict):
    messages: Annotated[List[BaseMessage], add_messages]
    department: Department
    crm_customer_id: str
    action_status: str
    session_id: str
    thread_id: str
