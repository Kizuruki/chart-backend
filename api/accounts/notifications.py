from core import ChartFastAPI

from typing import Optional

from fastapi import APIRouter, Request, HTTPException, status, Query

from database import accounts
from helpers.session import get_session, Session
from helpers.models import NotificationRequest, Notification, ReadUpdate

router = APIRouter()


@router.get("/")
async def main(
    request: Request,
    page: Optional[int] = Query(0, ge=0),
    only_unread: Optional[bool] = Query(False),
    session: Session = get_session(enforce_auth=True),
):
    app: ChartFastAPI = request.app
    page = page if page else 0

    async with app.db_acquire() as conn:
        notifications = await conn.fetch(
            accounts.get_notifications(
                session.sonolus_id, page=page, only_unread=only_unread
            )
        )

    notifs = (
        [notification.model_dump() for notification in notifications]
        if notifications
        else []
    )
    for notif in notifs:
        notif["timestamp"] = int(notif["created_at"].timestamp() * 1000)
    return {"notifications": notifs}


@router.post("/")
async def add(
    notification: NotificationRequest,
    request: Request,
    session: Session = get_session(enforce_auth=True, allow_banned_users=False),
):
    app: ChartFastAPI = request.app
    user = await session.user()

    if not user.admin and not user.mod:
        raise HTTPException(status.HTTP_403_FORBIDDEN)

    async with app.db_acquire() as conn:
        await conn.execute(
            accounts.add_notification(
                Notification(
                    user_id=notification.user_id,
                    title=notification.title,
                    content=notification.content,
                )
            )
        )

    return {"result": "success"}


@router.get("/{notification_id}/")
async def read(
    notification_id: str,
    request: Request,
    session: Session = get_session(enforce_auth=True),
):
    app: ChartFastAPI = request.app

    async with app.db_acquire() as conn:
        notification = await conn.fetchrow(
            accounts.get_notification(notification_id, session.sonolus_id)
        )

        if not notification_id:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Failed to get.")

    return notification.model_dump()


@router.patch("/{notification_id}/")
async def toggle_notification_read_status(
    notification_id: int,
    request: Request,
    read: ReadUpdate,
    session: Session = get_session(enforce_auth=True),
):
    app: ChartFastAPI = request.app

    async with app.db_acquire() as conn:
        notification = await conn.fetchrow(
            accounts.toggle_notification_read_status(
                notification_id, session.sonolus_id, read.is_read
            )
        )

        if not notification_id:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Failed to update.")

    return notification.model_dump()


@router.delete("/{notification_id}/")
async def delete(
    notification_id: int,
    request: Request,
    session: Session = get_session(enforce_auth=True),
):
    app: ChartFastAPI = request.app

    user = await session.user()
    if not user.admin and not user.mod:
        raise HTTPException(status.HTTP_403_FORBIDDEN)

    async with app.db_acquire() as conn:
        notification = await conn.fetchrow(
            accounts.delete_notification(notification_id, session.sonolus_id)
        )

        if not notification:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Failed to delete.")

    return {"result": "success"}
