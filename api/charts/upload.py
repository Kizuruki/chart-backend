import uuid, io, asyncio

from fastapi import APIRouter, Request, HTTPException, status, UploadFile, Form

from database import charts, accounts

from helpers.models import ChartUploadData
from helpers.hashing import calculate_sha1
from helpers.file_checks import get_and_check_file
from helpers.backgrounds import generate_backgrounds

from typing import Optional

from pydantic import ValidationError

from core import ChartFastAPI

router = APIRouter()


@router.post("/")
async def main(
    request: Request,
    jacket_image: UploadFile,
    chart_file: UploadFile,
    audio_file: UploadFile,
    data: str = Form(...),
    preview_file: Optional[UploadFile] = None,
    background_image: Optional[UploadFile] = None,
):
    app: ChartFastAPI = request.app
    try:
        data: ChartUploadData = ChartUploadData.model_validate_json(data)
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=e.errors())
    auth = request.headers.get("authorization")
    # this is a PUBLIC route, don't check for private auth, only user auth
    if not auth:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Not logged in."
        )
    session_data = app.decode_key(auth)
    if session_data["type"] != "game":  # XXX: switch to external
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Invalid token type."
        )
    query, args = accounts.generate_get_account_from_session_query(
        session_data["user_id"], auth, "game"  # XXX: switch to external
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
        cooldown = result["chart_upload_cooldown"]
        if cooldown and (True):  # XXX: insert cooldown, compared cooldown
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"On cooldown. TIME REMAINING",
            )  # XXX todo

    MAX_FILE_SIZES = {
        "jacket": 5 * 1024 * 1024,  # 5 MB
        "chart": 10 * 1024 * 1024,  # 10 MB
        "audio": 25 * 1024 * 1024,  # 25 MB
        "preview": 5 * 1024 * 1024,  # 5 MB
        "background": 10 * 1024 * 1024,  # 10 MB
    }
    if (
        jacket_image.size > MAX_FILE_SIZES["jacket"]
        or chart_file.size > MAX_FILE_SIZES["chart"]
        or audio_file.size > MAX_FILE_SIZES["audio"]
    ):
        raise HTTPException(
            status_code=status.HTTP_406_NOT_ACCEPTABLE,
            detail="Uploaded files exceed file size limit.",
        )
    if preview_file:
        if preview_file.size > MAX_FILE_SIZES["preview"]:
            raise HTTPException(
                status_code=status.HTTP_406_NOT_ACCEPTABLE,
                detail="Uploaded files exceed file size limit.",
            )
    if background_image:
        if background_image.size > MAX_FILE_SIZES["background"]:
            raise HTTPException(
                status_code=status.HTTP_406_NOT_ACCEPTABLE,
                detail="Uploaded files exceed file size limit.",
            )

    s3_uploads = []
    chart_id = str(uuid.uuid4()).replace("-", "")

    jacket_bytes = await get_and_check_file(jacket_image, "image/png")
    jacket_hash = calculate_sha1(jacket_bytes)
    s3_uploads.append(
        {
            "path": f"{session_data['user_id']}/{chart_id}/{jacket_hash}",
            "hash": jacket_hash,
            "bytes": jacket_bytes,
            "content-type": "image/png",
        }
    )

    # XXX: only needed before file converter
    start = await chart_file.read(2)
    await chart_file.seek(0)
    if start[:2] == b"\x1f\x8b":  # GZIP magic number
        pass
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid file format."
        )
    chart_bytes = await chart_file.read()
    # TODO: implement level converter
    # pip install git+https://github.com/UntitledCharts/sonolus-level-converters
    # except it's not done :heh:
    # for testing purpouse a real level packer :sob:
    chart_hash = calculate_sha1(chart_bytes)
    s3_uploads.append(
        {
            "path": f"{session_data['user_id']}/{chart_id}/{chart_hash}",
            "hash": chart_hash,
            "bytes": chart_bytes,
            "content-type": "application/gzip",
        }
    )

    audio_bytes = await get_and_check_file(audio_file, "audio/mpeg")
    audio_hash = calculate_sha1(audio_bytes)
    s3_uploads.append(
        {
            "path": f"{session_data['user_id']}/{chart_id}/{audio_hash}",
            "hash": audio_hash,
            "bytes": audio_bytes,
            "content-type": "audio/mpeg",
        }
    )

    if preview_file:
        preview_bytes = await get_and_check_file(preview_file, "audio/mpeg")
        preview_hash = calculate_sha1(preview_bytes)
        s3_uploads.append(
            {
                "path": f"{session_data['user_id']}/{chart_id}/{preview_hash}",
                "hash": preview_hash,
                "bytes": preview_bytes,
                "content-type": "audio/mpeg",
            }
        )

    if background_image:
        background_bytes = await get_and_check_file(background_image, "image/png")
        background_hash = calculate_sha1(background_bytes)
        s3_uploads.append(
            {
                "path": f"{session_data['user_id']}/{chart_id}/{background_hash}",
                "hash": background_hash,
                "bytes": background_bytes,
                "content-type": "image/png",
            }
        )
    v1, v3 = await app.run_blocking(generate_backgrounds, jacket_bytes)
    v1_hash = calculate_sha1(v1)
    s3_uploads.append(
        {
            "path": f"{session_data['user_id']}/{chart_id}/{v1_hash}",
            "hash": v1_hash,
            "bytes": v1,
            "content-type": "image/png",
        }
    )
    v3_hash = calculate_sha1(v3)
    s3_uploads.append(
        {
            "path": f"{session_data['user_id']}/{chart_id}/{v3_hash}",
            "hash": v3_hash,
            "bytes": v3,
            "content-type": "image/png",
        }
    )
    async with app.s3_session_getter() as s3:
        bucket = await s3.Bucket(app.s3_bucket)
        tasks = []
        alr_added_hashes = []
        for file in s3_uploads:
            if file["hash"] in alr_added_hashes:
                continue
            alr_added_hashes.append(file["hash"])
            path = file["path"]
            file_bytes = file["bytes"]
            content_type = file["content-type"]
            task = bucket.upload_fileobj(
                Fileobj=io.BytesIO(file_bytes),
                Key=path,
                ExtraArgs={"ContentType": content_type},
            )
            tasks.append(task)
        await asyncio.gather(*tasks)
    query, args = charts.generate_create_chart_query(
        chart_id=chart_id,
        author=session_data["user_id"],
        rating=data.rating,
        description=data.description,
        chart_author=data.author,
        title=data.title,
        artists=data.artists,
        tags=data.tags or [],
        jacket_hash=jacket_hash,
        music_hash=audio_hash,
        chart_hash=chart_hash,
        preview_hash=preview_hash if preview_file else None,
        background_hash=background_hash if background_image else None,
        v1_hash=v1_hash,
        v3_hash=v3_hash,
    )

    async with app.db.acquire() as conn:
        result = await conn.fetchrow(query, *args)
        if result:
            return {"id": result["id"]}
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error while processing upload result.",
        )
