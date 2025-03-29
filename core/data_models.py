"""Data models for email classification."""

from pydantic import BaseModel
from typing import Dict, Any

class State(BaseModel):
    email: Dict[str, Any]  # Stores email data
    messages: list = []  # List of previous messages

class RespondTo(BaseModel):
    response: str  # Can be "email", "notify", or "no"
