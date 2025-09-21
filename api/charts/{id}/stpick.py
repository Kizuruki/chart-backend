import uuid, io, asyncio
from core import ChartFastAPI

from fastapi import APIRouter, Request, HTTPException, status, UploadFile, Form
from helpers.session import get_session, Session

from database import charts

from helpers.models import ChartStPickData

router = APIRouter()


@router.patch("/")
async def main(
    request: Request,
    id: str,
    data: ChartStPickData,
    session: Session = get_session(
        enforce_auth=True, enforce_type="game", allow_banned_users=False
    ),
):
    if len(id) != 32 or not id.isalnum():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid chart ID."
        )
    app: ChartFastAPI = request.app
    user = await session.user()

    if not user.mod:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="not mod")

    query = charts.set_staff_pick(chart_id=id, value=data.value)

    async with app.db_acquire() as conn:
        result = await conn.fetchrow(query)
        if result:
            return {"id": result.id}
        raise HTTPException(
            status=status.HTTP_404_NOT_FOUND,
            detail=f'Chart with ID "{id}" not found for any user!',
        )
