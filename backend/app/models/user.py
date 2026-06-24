from sqlalchemy import Column, String, DateTime, Boolean, Text, Integer
from sqlalchemy import false as sa_false
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from app.core.database import Base
import uuid

class User(Base):
    """SQLAlchemy User model"""
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, unique=True, nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)
    password = Column(String(255), nullable=False)
    role = Column(String(20), default="user", nullable=False)
    profile_picture = Column(String(500), nullable=True)
    last_loggedin_at = Column(DateTime(timezone=True), nullable=True)

    # Per-user SMTP configuration (password stored encrypted via app.core.crypto)
    smtp_host = Column(String(255), nullable=True)
    smtp_port = Column(Integer, nullable=True)
    smtp_username = Column(String(255), nullable=True)
    smtp_password_encrypted = Column(Text, nullable=True)
    smtp_from_email = Column(String(255), nullable=True)
    smtp_from_name = Column(String(255), nullable=True)

    # IMAP for reply detection (reuses smtp_username + smtp_password for login)
    imap_host = Column(String(255), nullable=True)
    imap_port = Column(Integer, nullable=True)
    reply_scan_enabled = Column(Boolean, nullable=False, server_default=sa_false())

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class Notification(Base):
    """SQLAlchemy Notification model"""
    __tablename__ = "notifications"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, unique=True, nullable=False)
    user_id = Column(UUID(as_uuid=True), nullable=False)
    message = Column(Text, nullable=False)
    is_seen = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

