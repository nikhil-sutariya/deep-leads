from datetime import datetime, timezone
import time
import uuid
import shutil
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User as UserModel
from app.schemas.user import (
    LoginSchema, CreateNotificationSchema
)
from app.repositories.user_repository import (
    get_user_by_email, get_user_by_id, create_user, update_user
)
from app.core.constants import NotificationType
from app.core.security import get_password_hash, verify_password
from app.core.security import create_access_token, create_refresh_token
from app.api.deps.auth_deps import verify_refresh_token
from app.core.exceptions import UserAlreadyExistsException
from app.core.config import get_settings
from app.messages.user import ErrorMessage, NotificationMessage
from app.core.socket_manager import UserNotificationManager
import jwt
from loguru import logger

user_notification_manager = UserNotificationManager()

settings = get_settings()


UPLOAD_PROFILE_DIR: Path = Path("uploads/profile_pictures")
UPLOAD_PROFILE_DIR.mkdir(parents=True, exist_ok=True)
ALLOWED_EXTENSIONS: set[str] = {"image/jpg", "image/jpeg", "image/png"}

class UserService:
    async def login_user(self, session: AsyncSession, payload: LoginSchema) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        try:
            user = await get_user_by_email(session, payload.email)

            if not user:
                return None, ErrorMessage.user_email_not_exists
            
            if payload.email.lower() != user.email:
                return None, ErrorMessage.wrong_email

            if not verify_password(payload.password, user.password):
                return None, ErrorMessage.wrong_password

            # Update last login time
            await update_user(session, user.id, {
                "last_loggedin_at": datetime.now(timezone.utc)
            })

            user_data = {
                "id": user.id,
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name
            }

            access_token = create_access_token(str(user.id))
            refresh_token = create_refresh_token(str(user.id))


            return {
                "user_data": user_data,
                "access_token": access_token,
                "refresh_token": refresh_token
            }, None
        except Exception as e:
            logger.error(f"Error in login: {str(e)}")
            return None, ErrorMessage.server_error

    async def refresh_token(self, session: AsyncSession, token: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        try:
            payload = await verify_refresh_token(token)

            if not payload:
                return None, ErrorMessage.empty_refresh_token

            user_id = uuid.UUID(payload.get("id"))
            user = await get_user_by_id(session, user_id)

            if not user:
                return None, ErrorMessage.user_email_not_exists

            user_data = {
                "id": user.id,
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name
            }

            access_token = create_access_token(str(user_data["id"]))
            refresh_token = create_refresh_token(str(user_data["id"]))

            return {
                "user_data": user_data,
                "access_token": access_token,
                "refresh_token": refresh_token
            }, None
        except Exception as e:
            logger.error(f"Error refreshing token: {str(e)}")
            return None, ErrorMessage.server_error

    async def send_forgot_password_email(self, session: AsyncSession, email: str) -> Tuple[Optional[Dict[str, Any]], Optional[str], Optional[str], Optional[str]]:
        try:
            user = await get_user_by_email(session, email)
            if not user:
                return None, ErrorMessage.user_email_not_exists

            token_payload = {
                "user_id": user.id,
                "expires": time.time() + 900
            }

            secret_token = create_access_token(token_payload)
            forget_url_link = f"{settings.frontend_host_url}/{settings.frontend_forget_password_url}?token={secret_token}"

            context = {
                "name": f"{user.first_name} {user.last_name}",
                "link_expiry_min": 15,
                "reset_link": forget_url_link
            }


            return context, user.email, "forgot_password.html", secret_token
        except Exception as e:
            logger.error(f"Error sending forgot password email: {str(e)}")
            return None, ErrorMessage.server_error

    async def reset_forgotten_password(self, session: AsyncSession, token: str, new_password: str, confirm_password: str) -> Tuple[Optional[bool], Optional[str]]:
        try:
            decoded_payload = jwt.decode(token, settings.secret_key, algorithms=[settings.oauth_algorithm])
        except:
            return None, ErrorMessage.forgot_password_link_expire

        if time.time() > decoded_payload['expires']:
            return None, ErrorMessage.forgot_password_link_expire

        user_id = decoded_payload['user_id']
        if new_password != confirm_password:
            return None, ErrorMessage.same_not_password

        try:
            user = await get_user_by_id(session, user_id)
            if not user:
                return None, ErrorMessage.user_email_not_exists

            if verify_password(new_password, user.password):
                return None, ErrorMessage.same_password

            password_hash = get_password_hash(new_password)
            updated_user = await update_user(session, user_id, {"password": password_hash})

            if updated_user:

                notification_data = CreateNotificationSchema(
                    user_id=user_id,
                    type=NotificationType.success,
                    message=NotificationMessage.reset_password
                ).model_dump()
                await user_notification_manager.send_notification(session, str(user_id), notification_data)

                return True, None
            return None, ErrorMessage.password_not_updated
        except Exception as e:
            logger.error(f"Error resetting password: {str(e)}")
            return None, ErrorMessage.password_not_updated

    async def change_password(self, session: AsyncSession, user: UserModel, current_password: str, new_password: str, confirm_password: str) -> Tuple[Optional[bool], Optional[str]]:
        try:
            if not verify_password(current_password, user.password):
                return None, ErrorMessage.wrong_current_password
            if new_password != confirm_password:
                return None, ErrorMessage.same_not_password
            if verify_password(new_password, user.password):
                return None, ErrorMessage.same_password

            updated_user = await update_user(session, user.id, {
                "password": get_password_hash(new_password)
            })

            if updated_user:

                notification_data = CreateNotificationSchema(
                    user_id=user.id,
                    type=NotificationType.success,
                    message=NotificationMessage.change_password
                ).model_dump()
                await user_notification_manager.send_notification(session, str(user.id), notification_data)

                return True, None
            return None, ErrorMessage.password_not_updated
        except Exception as e:
            logger.error(f"Error changing password: {str(e)}")
            return None, ErrorMessage.password_not_updated

    async def get_profile(self, session: AsyncSession, user_id: uuid.UUID) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        try:
            user = await get_user_by_id(session, user_id)
            if not user:
                return None, ErrorMessage.profile_data_not_found
            
            return {
                "id": user.id,
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "profile_picture": user.profile_picture,
                "last_loggedin_at": user.last_loggedin_at,
                "created_at": user.created_at,
                "updated_at": user.updated_at
            }, None
        except Exception as e:
            logger.error(f"Error getting profile: {str(e)}")
            return None, ErrorMessage.server_error

    async def update_profile(self, session: AsyncSession, user_id: uuid.UUID, payload: Dict[str, Any]) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        try:
            user = await get_user_by_id(session, user_id)
            if not user:
                return None, ErrorMessage.profile_data_not_found
            
            updated_user = await update_user(session, user_id, payload)
            if updated_user:

                notification_data = CreateNotificationSchema(
                    user_id=user_id,
                    type=NotificationType.success,
                    message=NotificationMessage.profile_updated
                ).model_dump()
                await user_notification_manager.send_notification(session, str(user_id), notification_data)

                return {
                    "id": updated_user.id,
                    "email": updated_user.email,
                    "first_name": updated_user.first_name,
                    "last_name": updated_user.last_name,
                    "profile_picture": updated_user.profile_picture,
                    "last_loggedin_at": updated_user.last_loggedin_at,
                    "created_at": updated_user.created_at,
                    "updated_at": updated_user.updated_at
                }, None
            return None, ErrorMessage.profile_not_updated
        except Exception as e:
            logger.error(f"Error updating profile: {str(e)}")
            return None, ErrorMessage.profile_not_updated

    async def update_profile_picture(self, session: AsyncSession, user_id: uuid.UUID, file: UploadFile) -> Tuple[Optional[str], Optional[str]]:
        if file.content_type not in ALLOWED_EXTENSIONS:
            return None, ErrorMessage.invalid_image_type

        extension = file.filename.split('.')[-1]
        filename = f"{uuid.uuid4().hex}.{extension}"
        file_path = UPLOAD_PROFILE_DIR / filename
        with file_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        profile_picture_url = f"/uploads/profile_pictures/{filename}"

        user = await get_user_by_id(session, user_id)
        if not user:
            return None, ErrorMessage.profile_data_not_found

        updated_user = await update_user(session, user_id, {"profile_picture": profile_picture_url})

        if updated_user:

            notification_data = CreateNotificationSchema(
                user_id=user_id,
                type=NotificationType.success,
                message=NotificationMessage.profile_pic_updated
            ).model_dump()
            await user_notification_manager.send_notification(str(user_id), notification_data)

            return profile_picture_url, None
        return None, ErrorMessage.profile_not_updated
