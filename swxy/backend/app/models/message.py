from sqlalchemy import JSON, Column, DateTime, ForeignKey, String, Text
from sqlalchemy.sql import func

from models.base import Base


class Message(Base):
    __tablename__ = "messages"

    message_id = Column(String(36), primary_key=True)
    session_id = Column(
        String(16), ForeignKey("sessions.session_id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_question = Column(Text, nullable=False)
    model_answer = Column(Text, nullable=False)
    thinking = Column(Text, nullable=True)
    citations = Column(JSON, nullable=False, default=list)
    recommendations = Column(JSON, nullable=False, default=list)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

