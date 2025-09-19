import asyncio
from fastapi import APIRouter, Request, HTTPException, status

from database import charts
from helpers.session import get_session, Session

from core import ChartFastAPI

router = APIRouter()


@router.delete("/")
async def main(
    request: Request,
    id: str,
    session: Session = get_session(
        enforce_auth=True, enforce_type="external", allow_banned_users=False
    ),
):
    app: ChartFastAPI = request.app

    if len(id) != 37 or not id.startswith("UnCh-") or not id[5:].isalnum():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid chart ID."
        )

    chart_id = id.removeprefix("UnCh-")

    query = charts.delete_chart(
        chart_id, session.sonolus_id, confirm_change=True
    )
    async with app.db_acquire() as conn:
        exists = await conn.conn.fetchrow(query.sql, *query.args)
    if exists:
        async with app.s3_session_getter() as s3:
            bucket = await s3.Bucket(app.s3_bucket)
            tasks = []
            prefix = f"{session.sonolus_id}/{chart_id}/"
            objects = [obj async for obj in bucket.objects.filter(Prefix=prefix)]
            if objects:
                tasks = [obj.delete() for obj in objects]
                await asyncio.gather(*tasks)
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Chart not found."
        )
