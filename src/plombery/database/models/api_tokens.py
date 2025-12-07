"""
Database models for API tokens
"""
from sqlalchemy import Column, String, Text, DateTime
from sqlalchemy.sql import func

from plombery.database.base import Base


class ApiToken(Base):
    """Store API tokens for external services (SingleSource tokens)"""

    __tablename__ = "api_tokens"

    key = Column(String, primary_key=True)  # e.g., "base_token", "client_token_TomPrice"
    value = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
