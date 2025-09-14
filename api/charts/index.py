from fastapi import APIRouter, Request, HTTPException, status
from core import ChartFastAPI

from database import charts

from helpers.models import ServiceUserProfileWithType

router = APIRouter()


@router.get("/")
async def main(request: Request):
    app: ChartFastAPI = request.app

    auth = request.headers.get("authorization")
    sonolus_id = None

    if auth:
        session_data = app.decode_key(auth)
        sonolus_id = session_data["user_id"]

    query_params = dict(request.query_params)
    if query_params.get("type") == "random":
        item_count = 5
        query, args = charts.generate_get_random_charts_query(
            item_count, sonolus_id=sonolus_id
        )

        async with app.db.acquire() as conn:
            rows = await conn.fetch(query, *args)

        data = [dict(row) for row in rows] if rows else []
        return {"data": data, "asset_base_url": app.s3_asset_base_url}
    
    page = 0
    items_per_page = 5
    query, args = charts.generate_get_chart_list_query(
        page=page,
        items_per_page=items_per_page,
        title_includes="love",
        sonolus_id=sonolus_id,
    )

    async with app.db.acquire() as conn:
        rows = await conn.fetch(query, *args)
        if rows:
            total = rows[0]["total_count"]
            page_count = (total + items_per_page - 1) // items_per_page
            data = [dict(row) for row in rows]
        else:
            total = 0
            page_count = 0
            data = []

    print(rows, total, page_count, data)
    
    return {
        "pageCount": page_count,
        "data": data,
        "asset_base_url": app.s3_asset_base_url,
    }