from core import ChartFastAPI

from fastapi import APIRouter, Request, HTTPException, status

from database import accounts

router = APIRouter()


@router.delete("/")
async def main_delete(request: Request, id: str):
    app: ChartFastAPI = request.app

    if request.headers.get(app.auth_header) != app.auth:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="why?")

    prefix = f"{id}/"
    bucket_name = app.s3_bucket

    async with app.s3_session_getter() as s3_client:
        paginator = s3_client.get_paginator("list_objects_v2")

        async for page in paginator.paginate(Bucket=bucket_name, Prefix=prefix):
            objects = page.get("Contents", [])

            if not objects:
                continue

            delete_keys = [{"Key": obj["Key"]} for obj in objects]
            await s3_client.delete_objects(
                Bucket=bucket_name, Delete={"Objects": delete_keys}
            )

    query, args = accounts.generate_delete_account_query(id, confirm_change=True)

    async with app.db.acquire() as conn:
        await conn.execute(query, *args)

    return {"result": "success"}
