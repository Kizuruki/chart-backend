import datetime
from core import ChartFastAPI

from fastapi import APIRouter, Request, HTTPException, status
from fastapi.responses import JSONResponse

from database import external

router = APIRouter()


def setup():
    @router.get("/")
    async def main(request: Request):
        app: ChartFastAPI = request.app

        id_key = request.query_params.get("id")
        if not id_key:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Missing ID"
            )

        query, args = external.generate_get_external_login_query(id_key)
        query2, args2 = external.generate_delete_external_login_query(id_key)

        async with app.db.acquire() as conn:
            result = await conn.fetchrow(query, *args)
            if result:
                if result["session_key"]:
                    await conn.execute(query2, *args2)
                    session_key = result["session_key"]
                    expires_at: datetime.datetime = result["expires_at"]
                    expiry_ms = int(
                        (expires_at.timestamp() - 60) * 1000
                    )  # "expire" 1 min earlier in website
                    return JSONResponse(
                        content={"session_key": session_key, "expiry": expiry_ms},
                        status_code=202,
                    )
                else:
                    return {}
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Invalid ID key.",
            )
