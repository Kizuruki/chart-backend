from fastapi import APIRouter, Request, HTTPException, status, UploadFile, Form

from database import charts, accounts
from helpers.session import Session

from core import ChartFastAPI

router = APIRouter()


def setup():
    @router.delete("/")
    async def main(
        request: Request,
        id: str,
        session=Session(enforce_auth=True, enforce_type="external"),
    ):
        app: ChartFastAPI = request.app

        if len(id) != 37 or not id.startswith("UnCh-") or not id[5:].isalnum():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid chart ID."
            )

        chart_id = id.removeprefix("UnCh-")

        async with app.db.acquire() as conn:
            ...  # TODO
