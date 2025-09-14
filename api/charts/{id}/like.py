from fastapi import APIRouter, Request, HTTPException, status
from core import ChartFastAPI

from database import charts, accounts

from helpers.models import Like

router = APIRouter()


@router.post("/")
async def main(request: Request, id: str, data: Like):
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

    if data.type == "like":
        query, args = charts.generate_add_like_query(chart_id, sonolus_id)
    elif data.type == "unlike":
        query, args = charts.generate_remove_like_query(chart_id, sonolus_id)
    async with app.db.acquire() as conn:
        check_query, check_args = accounts.generate_get_account_from_session_query(
            session_data["user_id"], auth, "game"
        )

        result = await conn.fetchrow(check_query, *check_args)
        if not result:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Not logged in."
            )

        if result["banned"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="User banned."
            )

        await conn.execute(query, *args)
    return {"result": "success"}
