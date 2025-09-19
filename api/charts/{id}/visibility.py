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
    session: Session = get_session(enforce_auth=True, enforce_type="external", allow_banned_users=False)
):
    app: ChartFastAPI = request.app
    # this is a PUBLIC route, don't check for private auth, only user auth

    query = charts.update_status(
        chart_id=id,
        sonolus_id=(await session.user()).user_id,
        status=data.status
    )

    async with app.db_acquire() as conn:
        result = await conn.fetchrow(query)
        if result:
            return {"id": result.id}
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f'Chart with ID "{id}" not found for this user.',
        )
