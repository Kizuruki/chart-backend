from typing import Optional, List, Literal

from fastapi import APIRouter, Request, HTTPException, status, Query
from core import ChartFastAPI

from database import charts

router = APIRouter()


def setup():
    @router.get("/")
    async def main(
        request: Request,
        type: Literal["random", "quick", "advanced"] = Query("random"),
        page: int = Query(0, ge=0),
        min_rating: Optional[int] = Query(None),
        max_rating: Optional[int] = Query(None),
        tags: Optional[List[str]] = Query(None),
        min_likes: Optional[int] = Query(None),
        max_likes: Optional[int] = Query(None),
        liked_by: Optional[bool] = Query(False),
        title_includes: Optional[str] = Query(None),
        description_includes: Optional[str] = Query(None),
        artists_includes: Optional[str] = Query(None),
        sort_by: Literal[
            "created_at", "rating", "likes", "decaying_likes", "abc"
        ] = Query("created_at"),
        sort_order: Literal["desc", "asc"] = Query("desc"),
        sonolus_id: Optional[str] = Query(None),
        status: Literal["PUBLIC", "UNLISTED", "PRIVATE"] = Query("PUBLIC"),
        meta_includes: Optional[str] = Query(None),
    ):
        app: ChartFastAPI = request.app

        auth = request.headers.get("authorization")
        sonolus_id = None

        if status != "PUBLIC":
            return  # XXX: implement

        if auth:
            session_data = app.decode_key(auth)
            sonolus_id = session_data.user_id
        item_page_count = 10
        if type == "random":
            query, args = charts.generate_get_random_charts_query(
                item_page_count // 2, sonolus_id=sonolus_id
            )
            async with app.db.acquire() as conn:
                rows = await conn.fetch(query, *args)
            data = [dict(row) for row in rows] if rows else []
            return {"data": data, "asset_base_url": app.s3_asset_base_url}
        elif type == "quick":
            query, args = charts.generate_get_chart_list_query(
                page=page, items_per_page=item_page_count, meta_includes=meta_includes
            )
        else:
            if sort_by == "abc":
                sort_order = "asc" if sort_order == "desc" else "desc"
            query, args = charts.generate_get_chart_list_query(
                page=page,
                items_per_page=item_page_count,
                min_rating=min_rating,
                max_rating=max_rating,
                status=status,
                tags=tags,
                min_likes=min_likes,
                max_likes=max_likes,
                liked_by=sonolus_id if liked_by else None,
                title_includes=title_includes,
                description_includes=description_includes,
                artists_includes=artists_includes,
                sort_by=sort_by,
                sort_order=sort_order,
                meta_includes=meta_includes,
                sonolus_id=sonolus_id,
            )
        async with app.db.acquire() as conn:
            rows = await conn.fetch(query, *args)
            if rows:
                total = rows[0]["total_count"]
                page_count = (total + item_page_count - 1) // item_page_count
                data = [dict(row) for row in rows]
            else:
                # XXX: todo: past max pages error
                total = 0
                page_count = 0
                data = []

        return {
            "pageCount": page_count,
            "data": data,
            "asset_base_url": app.s3_asset_base_url,
        }
