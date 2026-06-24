from pydantic import BaseModel, Field, field_validator
from pydantic.networks import EmailStr
from app.core import constants
from datetime import datetime
from typing import Optional
import re
import uuid

# Base schemas for API requests
class LoginSchema(BaseModel):
    email: EmailStr = Field(pattern=constants.email_regex)
    password: str = Field(min_length=8, max_length=16)

    @field_validator('email')
    def validate_email(cls, value):
        if not re.match(constants.email_regex, value):
            raise ValueError("Invalid email address")
        return value
    
    @field_validator("password")
    def validate_password(cls, value):
        if not any(c.isupper() for c in value):
            raise ValueError("Password must contain at least one uppercase character.")

        symbols = "!@#$%^&*()_-+=<>?"
        if not any(c in symbols for c in value):
            raise ValueError("Password must contain at least one symbol.")
        
        numbers = "0123456789"
        if not any(c in numbers for c in value):
            raise ValueError("Password must contain at least one number.")

        return value
    
class RequestEmailLinkForgotPasswordSchema(BaseModel):
    email: EmailStr = Field(pattern=constants.email_regex)

    @field_validator('email')
    def validate_email(cls, value):
        if not re.match(constants.email_regex, value):
            raise ValueError("Invalid email address")
        return value

class ResetForgotPasswordSchema(BaseModel):
    secret_token: str = Field()
    new_password: str = Field()
    confirm_password: str = Field()

class ChangePasswordSchema(BaseModel):
    current_password: str = Field()
    new_password: str = Field()
    confirm_password: str = Field()

class VerifyPasswordSchema(BaseModel):
    password: str = Field()

class UpdateProfileSchema(BaseModel):
    first_name: Optional[str] = Field(default=None)
    last_name: Optional[str] = Field(default=None)
    phone: Optional[str] = Field(default=None)
    address: Optional[str] = Field(default=None)

class CreateNotificationSchema(BaseModel):
    user_id: uuid.UUID
    type: str
    message: str
    is_seen: bool = False


# ---------------------------- SMTP settings ----------------------------- #

class SmtpSettingsUpdate(BaseModel):
    """Per-user SMTP config. `password` optional so re-saving keeps the stored one."""
    smtp_host: Optional[str] = None
    smtp_port: Optional[int] = None
    smtp_username: Optional[str] = None
    smtp_password: Optional[str] = None
    smtp_from_email: Optional[str] = None
    smtp_from_name: Optional[str] = None
    # IMAP / reply detection (login reuses the SMTP username + password)
    imap_host: Optional[str] = None
    imap_port: Optional[int] = None
    reply_scan_enabled: Optional[bool] = None


class SmtpSettingsResponse(BaseModel):
    smtp_host: Optional[str] = None
    smtp_port: Optional[int] = None
    smtp_username: Optional[str] = None
    smtp_from_email: Optional[str] = None
    smtp_from_name: Optional[str] = None
    password_set: bool = False
    # Only populated when explicitly revealed (?reveal=true)
    smtp_password: Optional[str] = None
    imap_host: Optional[str] = None
    imap_port: Optional[int] = None
    reply_scan_enabled: bool = False


# ---------------------------- Admin: users ------------------------------ #

class InviteUserSchema(BaseModel):
    email: EmailStr
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    role: str = "user"
    password: Optional[str] = None  # if omitted, a temp password is generated


class UserListItem(BaseModel):
    id: uuid.UUID
    email: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    role: str = "user"
    last_loggedin_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True

# Response schemas for API responses
class CurrentUser(BaseModel):
    """User model for authentication context - doesn't include sensitive fields"""
    id: uuid.UUID
    email: str
    role: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None

    class Config:
        from_attributes = True

class UserProfileResponse(BaseModel):
    """User profile model for API responses - excludes sensitive fields"""
    id: uuid.UUID
    email: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    profile_picture: Optional[str] = None
    last_loggedin_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class UserOut(BaseModel):
    """Standard user payload for API responses with UUID id"""
    id: uuid.UUID
    email: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    profile_picture: Optional[str] = None
    last_loggedin_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class UserCreate(BaseModel):
    """Schema for creating a new user"""
    email: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    password: str
    role: str = "user"

class UserUpdate(BaseModel):
    """Schema for updating user data"""
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    profile_picture: Optional[str] = None
    last_loggedin_at: Optional[datetime] = None

class NotificationResponse(BaseModel):
    """Notification response schema"""
    id: uuid.UUID
    user_id: uuid.UUID
    organization_id: Optional[uuid.UUID] = None
    type: str
    message: str
    is_seen: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class LogResponse(BaseModel):
    """Log response schema"""
    id: uuid.UUID
    user_id: Optional[uuid.UUID] = None
    message: str
    module: str
    log_type: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class LogCreate(BaseModel):
    """Schema for creating a log entry"""
    user_id: Optional[uuid.UUID] = None
    message: str
    module: str
    log_type: str
