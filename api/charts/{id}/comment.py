from fastapi import APIRouter, Request, HTTPException, status
from core import ChartFastAPI

from database import comments
from helpers.session import get_session, Session

from helpers.models import CommentRequest

router = APIRouter()


@router.post("/")
async def main(
    request: Request,
    id: str,
    data: CommentRequest,
    session: Session = get_session(enforce_auth=True, allow_banned_users=False),
):
    # exposed to public
    # authentication needed

    app: ChartFastAPI = request.app

    if len(id) != 32 or not id.isalnum():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid chart ID."
        )
    if len(data.content) > 200:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Comments cannot be larger than 200 characters.",
        )
    user = await session.user()
    query = comments.create_comment(user.sonolus_id, id, data.content)
    async with app.db_acquire() as conn:
        result = await conn.fetchrow(query)
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Chart not found."
            )
    return {"result": "success"}


@router.delete("/{comment_id}")
async def main(
    request: Request,
    id: str,
    comment_id: int,
    session: Session = get_session(enforce_auth=True, allow_banned_users=False),
):
    # exposed to public
    # authentication needed

    app: ChartFastAPI = request.app

    if len(id) != 32 or not id.isalnum():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid chart ID."
        )
    user = await session.user()
    if user.mod:
        query = comments.delete_comment(comment_id)
    else:
        query = comments.delete_comment(comment_id, user.sonolus_id)
    async with app.db_acquire() as conn:
        result = await conn.fetchrow(query)
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Chart or comment not found.",
            )
    return {"result": "success"}


@router.get("/")
async def main(
    request: Request,
    id: str,
):
    app: ChartFastAPI = request.app

    if len(id) != 32 or not id.isalnum():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid chart ID."
        )
    query = comments.get_comments(id)
    async with app.db_acquire() as conn:
        result = await conn.fetch(query)
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Chart not found."
            )
    return {"data": [row.model_dump() for row in result]}
