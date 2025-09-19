from fastapi import APIRouter, Request, HTTPException, status
from core import ChartFastAPI

from database import charts
from helpers.session import get_session, Session

router = APIRouter()


@router.get("/")
async def main(request: Request, id: str, session: Session = get_session()):
    # exposed to public
    # no authentication needed
    # however, if they are authed
    # use it to check if liked

    app: ChartFastAPI = request.app

    if len(id) != 37 or not id.startswith("UnCh-") or not id[5:].isalnum():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid chart ID."
        )

    chart_id = id.removeprefix("UnCh-")
    query = charts.get_chart_by_id(
        chart_id, sonolus_id=session.sonolus_id
    )

    async with app.db_acquire() as conn:
        result = await conn.fetchrow(query)

        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=f"Chart not found."
            )

        if result.status == "PRIVATE" and result.author != session.sonolus_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=f"Chart not found."
            )

    return {"data": result.model_dump, "asset_base_url": app.s3_asset_base_url}
