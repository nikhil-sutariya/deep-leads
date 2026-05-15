import uuid
from typing import Dict, Union
from fastapi import APIRouter, status, Depends, BackgroundTasks, Path, File, UploadFile, \
    WebSocket, WebSocketDisconnect, Response as FastAPIResponse, Request 
from fastapi.websockets import WebSocketState
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger
from app.messages.user import ErrorMessage, InfoMessage
from app.schemas.user import (
    LoginSchema, RequestEmailLinkForgotPasswordSchema,
    ResetForgotPasswordSchema, ChangePasswordSchema, UpdateProfileSchema,
    CurrentUser
)
from fastapi.security import OAuth2PasswordRequestForm
from app.repositories.user_repository import get_notifications_by_user, update_notification_status, get_user_by_id
from app.api.deps.auth_deps import get_current_user, get_current_user_from_token
from app.core.database import get_db
from app.core.config import get_settings
from app.core import constants
from pathlib import Path as PathlibPath
import asyncio
from app.core.socket_manager import UserNotificationManager
from app.utils import send_email
from app.services.user_service import UserService
from app.core.security import create_access_token
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder

settings = get_settings()
user_notification_manager = UserNotificationManager()
user_service = UserService()

UPLOAD_PROFILE_DIR: PathlibPath = PathlibPath("uploads/profile_pictures")
UPLOAD_PROFILE_DIR.mkdir(parents=True, exist_ok=True)
ALLOWED_EXTENSIONS: set[str] = {"image/jpg", "image/jpeg", "image/png"}

router = APIRouter()

@router.post("/login")
async def login_user(response: FastAPIResponse, payload: LoginSchema, db: AsyncSession = Depends(get_db)) -> FastAPIResponse:
    try:
        result, error = await user_service.login_user(db, payload)
        if error:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"success": False, "message": error, "error": None}
            )
        
        response = JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"success": True, "message": InfoMessage.login_success, "data": jsonable_encoder(result['user_data'])}
        )
               
        response.set_cookie(
            key="access_token", 
            value=result['access_token'], 
            httponly=True, 
            secure=True if settings.environment == constants.Environment.production else False,
            samesite="Lax",
            path="/"
        )

        response.set_cookie(
            key="refresh_token",
            value=result['refresh_token'],
            httponly=True,
            secure=True if settings.environment == constants.Environment.production else False,
            samesite="Lax",
            path="/"
        )
        return response
    
    except Exception as e:
        logger.error(str(e))
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"success": False, "message": ErrorMessage.server_error, "error": str(e)}
        )

@router.post("/logout")
async def logout(response: FastAPIResponse) -> FastAPIResponse:
    try:
        response = JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"success": True, "message": InfoMessage.logout_success, "data": None}
        )
        response.delete_cookie("access_token", path="/")
        response.delete_cookie("refresh_token", path="/")
        return response
    except Exception as e:
        logger.error(str(e))
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"success": False, "message": ErrorMessage.server_error, "error": str(e)}
        )

@router.post("/refresh-token")
async def refresh_token(request: Request, db: AsyncSession = Depends(get_db)) -> FastAPIResponse:
    try:
        refresh_token = request.cookies.get("refresh_token")
        result, error = await user_service.refresh_token(db, refresh_token)
        if error:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"success": False, "message": error, "error": None}
            )
        
        response = JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content={"success": True, "message": InfoMessage.access_token_refreshed, "data": jsonable_encoder(result)}
        )
               
        response.set_cookie(
            key="access_token", 
            value=result['access_token'], 
            httponly=True, 
            secure=True if settings.environment == constants.Environment.production else False,
            samesite="Lax",
            path="/"
        )

        response.set_cookie(
            key="refresh_token",
            value=result['refresh_token'],
            httponly=True,
            secure=True if settings.environment == constants.Environment.production else False,
            samesite="Lax",
            path="/"
        )

        return response
    except Exception as e:
        logger.error(str(e))
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"success": False, "message": ErrorMessage.server_error, "error": str(e)}
        )

@router.post('/swagger-login', response_model=None)
async def swagger_login(
    response: FastAPIResponse, 
    form_data: OAuth2PasswordRequestForm = Depends(), 
    db: AsyncSession = Depends(get_db)
):
    """
    OAuth2 compatible token endpoint for Swagger UI.
    
    Use this endpoint to authenticate in Swagger UI:
    1. Click the "Authorize" button (🔓) in Swagger UI
    2. Enter your email as 'username' and password
    3. Click "Authorize"
    4. The token will be automatically used for all subsequent requests
    """
    try:
        login_payload = LoginSchema(email=form_data.username, password=form_data.password)
        result, error = await user_service.login_user(db, login_payload)
        if error:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"success": False, "message": error, "error": None}
            )
        
        # Set cookies for browser-based access (optional for Swagger)
        response.set_cookie(
            key="access_token", 
            value=result['access_token'], 
            httponly=True, 
            secure=True if settings.environment == constants.Environment.production else False,
            samesite="Lax",
            path="/"
        )

        response.set_cookie(
            key="refresh_token",
            value=result['refresh_token'],
            httponly=True,
            secure=True if settings.environment == constants.Environment.production else False,
            samesite="Lax",
            path="/"
        )

        # Return token in OAuth2 format for Swagger UI
        return {
            "access_token": result['access_token'],
            "token_type": "bearer"  # Required by OAuth2 spec
        }
    except Exception as e:
        logger.error(str(e))
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"success": False, "message": ErrorMessage.server_error, "error": str(e)}
        )

@router.post('/forget-password', status_code=status.HTTP_200_OK)
async def forget_password(payload: RequestEmailLinkForgotPasswordSchema, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)) -> FastAPIResponse:
    try:
        context, email, template, token = await user_service.send_forgot_password_email(db, payload.email)
        if not context:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"success": False, "message": ErrorMessage.user_email_not_exists, "error": None}
            )
        
        background_tasks.add_task(send_email.send, "Reset password", email, template, context)
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"success": True, "message": InfoMessage.forgot_password_mail_sent, "data": jsonable_encoder(context)}
        )
    except Exception as e:
        logger.error(str(e))
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"success": False, "message": ErrorMessage.server_error, "error": str(e)}
        )

@router.post('/reset-password', status_code=status.HTTP_200_OK)
async def reset_password(payload: ResetForgotPasswordSchema, db: AsyncSession = Depends(get_db)) -> FastAPIResponse:
    try:
        result, error = await user_service.reset_forgotten_password(
            db,
            payload.secret_token,
            payload.new_password,
            payload.confirm_password
        )
        if error:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"success": False, "message": error, "error": None}
            )
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"success": True, "message": InfoMessage.password_updated, "data": None}
        )
    except Exception as e:
        logger.error(str(e))
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"success": False, "message": ErrorMessage.server_error, "error": str(e)}
        )

@router.patch('/change-password')
async def change_password(payload: ChangePasswordSchema, current_user: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> FastAPIResponse:
    try:
        # Get the full user object from database
        user = await get_user_by_id(db, current_user.id)
        if not user:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"success": False, "message": ErrorMessage.user_email_not_exists, "error": None}
            )
            
        result, error = await user_service.change_password(
            db,
            user,
            payload.current_password,
            payload.new_password,
            payload.confirm_password
        )
        if error:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"success": False, "message": error, "error": None}
            )
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"success": True, "message": InfoMessage.password_updated, "data": None}
        )
    except Exception as e:
        logger.error(str(e))
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"success": False, "message": ErrorMessage.server_error, "error": str(e)}
        )

@router.get("/get-profile")
async def get_profile(current_user: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> FastAPIResponse:
    try:
        user_data, error = await user_service.get_profile(db, current_user.id)
        if error:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"success": False, "message": error, "error": None}
            )
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"success": True, "message": InfoMessage.user_account_fetched, "data": jsonable_encoder(user_data)}
        )
    except Exception as e:
        logger.error(str(e))
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"success": False, "message": ErrorMessage.server_error, "error": str(e)}
        )

@router.patch("/update-profile/{user_id}")
async def update_profile(payload: UpdateProfileSchema, user_id: uuid.UUID = Path(description="Id of the user"), current_user: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> FastAPIResponse:
    try:
        user_data, error = await user_service.update_profile(db, user_id, payload.model_dump(exclude_unset=True))
        if error:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"success": False, "message": error, "error": None}
            )
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"success": True, "message": InfoMessage.profile_updated, "data": jsonable_encoder(user_data)}
        )
    except Exception as e:
        logger.error(str(e))
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"success": False, "message": ErrorMessage.server_error, "error": str(e)}
        )

@router.patch("/upload-profile-picture/{user_id}")
async def update_profile_picture(profile_picture: UploadFile = File(), user_id: uuid.UUID = Path(description="Id of the user"), current_user: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> FastAPIResponse:
    try:
        result, error = await user_service.update_profile_picture(db, user_id, profile_picture)
        if error:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"success": False, "message": error, "error": None}
            )
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"success": True, "message": InfoMessage.profile_updated, "data": jsonable_encoder({"profile_picture": result})}
        )
    except Exception as e:
        logger.error(str(e))
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"success": False, "message": ErrorMessage.server_error, "error": str(e)}
        )

@router.get("/get-notifications")
async def get_notifications(current_user: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> FastAPIResponse:
    try:
        notifications = await get_notifications_by_user(db, current_user.id)
        # Convert SQLAlchemy objects to dictionaries for JSON serialization
        notifications_data = []
        if notifications:
            for notification in notifications:
                notifications_data.append({
                    "id": notification.id,
                    "user_id": notification.user_id,
                    "organization_id": notification.organization_id,
                    "type": notification.type,
                    "message": notification.message,
                    "is_seen": notification.is_seen,
                    "created_at": notification.created_at,
                    "updated_at": notification.updated_at
                })
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"success": True, "message": InfoMessage.available_notifications, "data": jsonable_encoder(notifications_data)}
        )
    except Exception as e:
        logger.error(str(e))
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"success": False, "message": ErrorMessage.server_error, "error": str(e)}
        )

@router.put("/notification-seen")
async def notification_seen(current_user: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> FastAPIResponse:
    try:
        await update_notification_status(db, current_user.id)
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"success": True, "message": InfoMessage.notification_seen, "data": None}
        )
    except Exception as e:
        logger.error(str(e))
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"success": False, "message": ErrorMessage.server_error, "error": str(e)}
        )

@router.get("/ws-token")
async def get_ws_token(user: CurrentUser = Depends(get_current_user)) -> Dict[str, str]:
    token = create_access_token(str(user.id), duration=5)
    return {"ws_token": token}

@router.websocket("/ws/notifications")
async def notification_websocket(websocket: WebSocket) -> None:
    token = websocket.query_params.get("token")
    if not token:
        logger.warning("WebSocket connection attempt without token")
        await websocket.close(code=4000)
        return

    try:
        logger.info("Attempting to authenticate websocket connection")
        # Create DB session for authentication
        async for admin_db in get_db():
            try:
                current_user = await get_current_user_from_token(token, admin_db)
                user_id = current_user.id
                logger.info(f"WebSocket authenticated for user {user_id}")
                await user_notification_manager.manage_connection(str(user_id), websocket)

                try:
                    while websocket.client_state == WebSocketState.CONNECTED:
                        try:
                            await asyncio.wait_for(websocket.receive_text(), timeout=10)
                        except asyncio.TimeoutError:
                            pass
                except WebSocketDisconnect:
                    logger.info(f"User disconnected {user_id}")
                except Exception as e:
                    logger.error(f"Unexpected error for user {user_id}: {e}")
                finally:
                    await user_notification_manager.manage_disconnection(str(user_id), websocket)
            except Exception as e:
                logger.error(f"Authentication error in websocket: {e}")
                await websocket.close(code=4000)
            break  # Exit the async for loop after processing
    except Exception as e:
        logger.error(f"Database connection error in websocket: {e}")
        await websocket.close(code=4000)
