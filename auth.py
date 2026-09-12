import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel

SECRET_KEY = os.getenv("JWT_SECRET", "supersecretkey12345")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 480

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

FAKE_USERS_DB = {
    "emp101": {
        "username": "emp101",
        "hashed_password": pwd_context.hash("password123"),
        "department": "support"
    }
}

class Token(BaseModel):
    access_token: str
    token_type: str
    session_id: str
    default_thread_id: str

class UserSession(BaseModel):
    username: str
    department: str
    session_id: str
    default_thread_id: str

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> tuple[str, str, str]:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=15))
    
    # Session ID identifies the user's active login
    session_id = f"sess_{data['sub']}_{uuid.uuid4().hex[:8]}"
    # Default Thread ID isolated under this session
    default_thread_id = f"thread_{session_id}_main"
    
    to_encode.update({
        "exp": expire,
        "session_id": session_id,
        "default_thread_id": default_thread_id
    })
    
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt, session_id, default_thread_id

async def get_current_user_session(token: str = Depends(oauth2_scheme)) -> UserSession:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials or active session",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        session_id: str = payload.get("session_id")
        default_thread_id: str = payload.get("default_thread_id")
        
        if not username or username not in FAKE_USERS_DB or not session_id:
            raise credentials_exception
            
        user_data = FAKE_USERS_DB[username]
        return UserSession(
            username=user_data["username"], 
            department=user_data["department"],
            session_id=session_id,
            default_thread_id=default_thread_id
        )
    except JWTError:
        raise credentials_exception
