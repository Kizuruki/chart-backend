import uuid, io, asyncio
from core import ChartFastAPI

from fastapi import APIRouter, Request, HTTPException, status, UploadFile, Form

from database import charts, accounts

from helpers.models import ChartVisibilityData

router = APIRouter()


@router.patch("/")
async def main(
    request: Request,
    data: ChartVisibilityData,
):
    app: ChartFastAPI = request.app
    auth = request.headers.get("authorization")
    # this is a PUBLIC route, don't check for private auth, only user auth
    if not auth:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Not logged in."
        )
    session_data = app.decode_key(auth)
    if session_data["type"] != "game":  # XXX: switch to external
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Invalid token type."
        )
    query, args = accounts.generate_get_account_from_session_query(
        session_data["user_id"], auth, "game"  # XXX: switch to external
    )
    async with app.db.acquire() as conn:
        result = await conn.fetchrow(query, *args)
        if not result:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Not logged in."
            )
        if result["banned"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="User banned."
            )
        
    query, args = charts.generate_update_status_query(
        chart_id=data.chart_id,
        status=data.status,
        sonolus_id=session_data["user_id"],
    )

    async with app.db.acquire() as conn:
        result = await conn.fetchrow(query, *args)
        if result:
            return {"id": result["id"]}
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f'Chart with ID "{data.chart_id}" not found for this user.',
        )