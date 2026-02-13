from pydantic import BaseModel
from typing import Optional, List

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None
    role: Optional[str] = None

class User(BaseModel):
    username: str
    password: str
    role: str = "user" # 'admin', 'user'

class LoginRequest(BaseModel):
    username: str
    password: str
