from typing import Optional, List, Dict, Any
from uuid import UUID
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User, Notification


async def get_user_by_email(session: AsyncSession, email: str) -> Optional[User]:
	result = await session.execute(select(User).where(User.email == email.lower()))
	return result.scalars().first()


async def get_user_by_id(session: AsyncSession, user_id: UUID) -> Optional[User]:
	result = await session.execute(select(User).where(User.id == user_id))
	return result.scalars().first()


async def create_user(session: AsyncSession, payload: Dict[str, Any]) -> Optional[User]:
	user = User(**payload)
	session.add(user)
	await session.flush()
	await session.refresh(user)
	return user


async def update_user(session: AsyncSession, user_id: UUID, updates: Dict[str, Any]) -> Optional[User]:
	await session.execute(
		update(User)
		.where(User.id == user_id)
		.values(**updates)
	)
	# Re-fetch updated user
	return await get_user_by_id(session, user_id)


async def get_notifications_by_user(session: AsyncSession, user_id: UUID) -> List[Notification]:
	result = await session.execute(
		select(Notification).where(Notification.user_id == user_id).order_by(Notification.created_at.desc())
	)
	return list(result.scalars().all())


async def update_notification_status(session: AsyncSession, user_id: UUID) -> None:
	await session.execute(
		update(Notification)
		.where(Notification.user_id == user_id, Notification.is_seen == False)
		.values(is_seen=True)
	)


