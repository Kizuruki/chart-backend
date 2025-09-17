import asyncio
from fastapi import APIRouter, Request, HTTPException, status

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

        auth = request.headers.get("authorization")
        # this is a PUBLIC route, don't check for private auth, only user auth
        if not auth:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Not logged in."
            )
        session_data = app.decode_key(auth)
        if session_data.type != "external":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Invalid token type."
            )
        query, args = accounts.generate_get_account_from_session_query(
            session_data.user_id, auth, "external"
        )
        async with app.db.acquire() as conn:
            result = await conn.fetchrow(query, *args)
            if not result:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED, detail="Not logged in."
                )
            if result["banned"]:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN, detail="User banned."
                )

        query, args = charts.generate_delete_chart_query(
            chart_id, session_data.user_id, confirm_change=True
        )
        async with app.db.acquire() as conn:
            exists = await conn.fetchrow(query, *args)
        if exists:
            async with app.s3_session_getter() as s3:
                bucket = await s3.Bucket(app.s3_bucket)
                tasks = []
                prefix = f"{session_data.user_id}/{chart_id}/"
                objects = [obj async for obj in bucket.objects.filter(Prefix=prefix)]
                if objects:
                    tasks = [obj.delete() for obj in objects]
                    await asyncio.gather(*tasks)
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Chart not found."
            )
