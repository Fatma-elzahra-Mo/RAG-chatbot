"""
Pydantic models for conversation memory.

Models for storing and managing conversation history with session tracking.
"""

from datetime import datetime
from typing import Dict, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class ConversationMessage(BaseModel):
    """
    Single conversation message.

    Attributes:
        id: Unique message identifier
        session_id: Session identifier for grouping messages
        role: Message role ("human" or "ai")
        content: Message text content
        timestamp: UTC timestamp of message creation
        metadata: Additional metadata for the message
    """

    id: UUID = Field(default_factory=uuid4)
    session_id: str
    role: str  # "human" or "ai"
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict = Field(default_factory=dict)

    class Config:
        json_encoders = {
            UUID: str,
            datetime: lambda v: v.isoformat(),
        }


class ConversationTurn(BaseModel):
    """
    A complete conversation turn (question + answer).

    Represents a single exchange between user and AI.

    Attributes:
        session_id: Session identifier
        user_message: User's question or input
        ai_message: AI's response
        timestamp: UTC timestamp of the exchange
        metadata: Additional metadata (confidence, sources, etc.)
    """

    session_id: str
    user_message: str
    ai_message: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict = Field(default_factory=dict)
