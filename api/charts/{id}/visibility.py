import uuid, io, asyncio
from core import ChartFastAPI

from fastapi import APIRouter, Request, HTTPException, status, UploadFile, Form
from helpers.session import get_session, Session

from database import charts

from helpers.models import ChartVisibilityData

router = APIRouter()


@router.patch("/")
async def main(
    request: Request,
    id: str,
    data: ChartVisibilityData,
    session: Session = get_session(
        enforce_auth=True, enforce_type=False, allow_banned_users=False
    ),
):
    if len(id) != 32 or not id.isalnum():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid chart ID."
        )
    app: ChartFastAPI = request.app
    user = await session.user()

    if user.mod:
        query = charts.update_status(chart_id=id, status=data.status)
    else:
        query = charts.update_status(
            chart_id=id, sonolus_id=user.sonolus_id, status=data.status
        )

    async with app.db_acquire() as conn:
        result = await conn.fetchrow(query)
        if result:
            return {"id": result.id}
        if user.mod:
            raise HTTPException(
                status=status.HTTP_404_NOT_FOUND,
                detail=f'Chart with ID "{id}" not found for any user!',
            )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f'Chart with ID "{id}" not found for this user.',
        )
