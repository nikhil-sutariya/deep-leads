from typing import Optional
from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.security import decode_token, oauth2_scheme
from app.repositories.user_repository import get_user_by_id
from app.schemas.user import CurrentUser
import uuid


async def _extract_token(request: Request, bearer_token: Optional[str]) -> Optional[str]:
	"""
	Extract access token from cookies (preferred) or Authorization bearer header.
	"""
	cookie_token = request.cookies.get("access_token")
	if cookie_token:
		return cookie_token
	if bearer_token:
		return bearer_token
	return None


async def get_current_user(
	request: Request,
	db: AsyncSession = Depends(get_db),
	token: Optional[str] = Depends(oauth2_scheme)
) -> CurrentUser:
	"""
	Resolve the authenticated user from access token.
	No role checks; only ensures the user is authenticated.
	"""
	access_token = await _extract_token(request, token)
	if not access_token:
		raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

	payload = decode_token(access_token)
	if not payload or not payload.get("id"):
		raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")

	try:
		user_id = uuid.UUID(str(payload["id"]))
	except Exception:
		raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")

	user = await get_user_by_id(db, user_id)
	if not user:
		raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

	return CurrentUser(
		id=user.id,
		email=user.email,
		role=getattr(user, "role", "user"),
		first_name=getattr(user, "first_name", None),
		last_name=getattr(user, "last_name", None),
	)


async def get_current_user_from_token(access_token: str, db: AsyncSession) -> CurrentUser:
	"""
	Resolve user directly from a provided access token string.
	Useful for websocket token auth.
	"""
	payload = decode_token(access_token)
	if not payload or not payload.get("id"):
		raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")

	user = await get_user_by_id(db, uuid.UUID(str(payload["id"])))
	if not user:
		raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

	return CurrentUser(
		id=user.id,
		email=user.email,
		role=getattr(user, "role", "user"),
		first_name=getattr(user, "first_name", None),
		last_name=getattr(user, "last_name", None),
	)


async def require_admin(current_user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
	"""Dependency that allows only admins through."""
	if current_user.role != "admin":
		raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
	return current_user


async def verify_refresh_token(token: Optional[str]) -> Optional[dict]:
	"""
	Validate refresh token structure and expiry.
	Returns decoded payload on success, otherwise None.
	"""
	if not token:
		return None
	payload = decode_token(token)
	if not payload or not payload.get("id") or not payload.get("refresh"):
		return None
	return payload

