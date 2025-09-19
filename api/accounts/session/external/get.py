import datetime
from core import ChartFastAPI

from fastapi import APIRouter, Request, HTTPException, status
from fastapi.responses import JSONResponse

from database import external

router = APIRouter()


@router.get("/")
async def main(request: Request):
    app: ChartFastAPI = request.app

    id_key = request.query_params.get("id")
    if not id_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Missing ID"
        )

    query = external.get_external_login(id_key)
    query2 = external.delete_external_login(id_key)

    async with app.db_acquire() as conn:
        result = await conn.fetchrow(query)
        if result:
            if result.session_key:
                await conn.execute(query2)
                expiry_ms = int(
                    (result.expires_at.timestamp() - 60) * 1000
                )  # "expire" 1 min earlier in website
                return JSONResponse(
                    content={"session_key": result.session_key, "expiry": expiry_ms},
                    status_code=202,
                )
            else:
                return {}
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invalid ID key.",
        )
