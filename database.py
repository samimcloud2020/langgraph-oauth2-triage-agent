import os
from langgraph.checkpoint.postgres import PostgresSaver
from psycopg_pool import ConnectionPool

DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "postgresql://crm_user:crm_password@localhost:5432/crm_checkpointer"
)

pool = ConnectionPool(conninfo=DATABASE_URL, max_size=20, kwargs={"autocommit": True})

def get_checkpointer() -> PostgresSaver:
    checkpointer = PostgresSaver(pool)
    checkpointer.setup()
    return checkpointer
