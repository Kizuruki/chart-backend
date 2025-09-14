donotload = False
import uuid, json, base64, hashlib
import hmac

from fastapi import APIRouter, Request, HTTPException, status

from database import accounts

from helpers.models import ServiceUserProfileWithType

router = APIRouter()


def setup():
    @router.delete("/")
    async def main_delete(request: Request, id: str):
        if request.headers.get(request.app.auth_header) != request.app.auth:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="why?")

        prefix = f"{id}/"
        bucket_name = request.app.s3_bucket

        async with request.app.s3_session.client(
            **request.app.s3_resource_options
        ) as s3_client:
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
        async with request.app.db.acquire() as conn:
            await conn.execute(query, *args)
        return {"result": "success"}
