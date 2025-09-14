from fastapi import APIRouter, Request, HTTPException, status
from core import ChartFastAPI

from database import charts

router = APIRouter()


@router.get("/")
async def main(request: Request, id: str):
    # exposed to public
    # no authentication needed
    # however, if they are authed
    # use it to check if liked

    app: ChartFastAPI = request.app

    auth = request.headers.get("authorization")
    sonolus_id = None

    if auth:
        session_data = app.decode_key(auth)
        sonolus_id = session_data["user_id"]

    if len(id) != 37 or not id.startswith("UnCh-") or not id[5:].isalnum():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid chart ID."
        )

    chart_id = id.removeprefix("UnCh-")
    query, args = charts.generate_get_chart_by_id_query(chart_id, sonolus_id=sonolus_id)

    async with app.db.acquire() as conn:
        result = await conn.fetchrow(query, *args)

        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=f"Chart not found."
            )

        if result["status"] == "PRIVATE" and result["author"] != sonolus_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=f"Chart not found."
            )

    data = dict(result)
    return {"data": data, "asset_base_url": app.s3_asset_base_url}
