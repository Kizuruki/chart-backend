from fastapi import APIRouter, Request, HTTPException, status
from core import ChartFastAPI

from database import charts
from helpers.session import get_session, Session

from helpers.models import Like

router = APIRouter()


@router.post("/")
async def main(
    request: Request,
    id: str,
    data: Like,
    session: Session = get_session(enforce_auth=True, allow_banned_users=False)
):
    # exposed to public
    # authentication needed

    app: ChartFastAPI = request.app

    if len(id) != 37 or not id.startswith("UnCh-") or not id[5:].isalnum():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid chart ID."
        )

    chart_id = id.removeprefix("UnCh-")

    if data.type == "like": # XXX: could return an error if info desyncs between sessions (yeah, it's minor, but still)
        query = charts.add_like(chart_id, session.sonolus_id)
    elif data.type == "unlike":
        query = charts.remove_like(chart_id, session.sonolus_id)
    async with app.db_acquire() as conn:
        await conn.execute(query)
    return {"result": "success"}
