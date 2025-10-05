import io, asyncio, gzip

from fastapi import APIRouter, Request, HTTPException, status

from database import charts

from helpers.models import ChartConstantData

from typing import Optional

from helpers.session import get_session, Session

from pydantic import ValidationError

from core import ChartFastAPI

router = APIRouter()


@router.patch("/")
async def main(
    request: Request,
    id: str,
    data: ChartConstantData,
    session: Session = get_session(
        enforce_auth=True, enforce_type="game", allow_banned_users=False
    ),
):
    if len(id) != 32 or not id.isalnum():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid chart ID."
        )

    user = await session.user()

    if not user.mod:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="not mod")

    app: ChartFastAPI = request.app
    if (data.constant >= 1000) or (data.constant <= -1000):
        raise HTTPException(
            status=status.HTTP_400_BAD_REQUEST, detail="Length limits exceeded"
        )
    elif (
        "." in str(abs(data.constant))
        and len(str(abs(data.constant)).split(".")[1]) > 4
    ):
        raise HTTPException(
            status=status.HTTP_400_BAD_REQUEST,
            detail="More than 4 decimal places are not allowed",
        )
    query = charts.update_metadata(
        chart_id=id,
        rating=data.constant,
    )
    async with app.db_acquire() as conn:
        await conn.execute(query)
    return {"result": "success"}
