import uuid, io, asyncio
from core import ChartFastAPI

from fastapi import APIRouter, Request, HTTPException, status, UploadFile, Form

from database import charts, accounts

# WARNING: not async!!
# WARNING: heavy workload!!
import pjsk_background_gen_PIL as pjsk_bg # type: ignore
from PIL import Image

from helpers.models import ChartUploadData
from helpers.hashing import calculate_sha1

from typing import Optional, Literal

from pydantic import ValidationError

router = APIRouter()

MAX_FILE_SIZES = {
    "jacket": 5 * 1024 * 1024,  # 5 MB
    "chart": 10 * 1024 * 1024,  # 10 MB
    "audio": 25 * 1024 * 1024,  # 20 MB
    "preview": 5 * 1024 * 1024,  # 5 MB
    "background": 10 * 1024 * 1024,  # 10 MB
}

async def get_and_check_file(file, expected_type: Literal["image/png", "audio/mpeg"]):
    # Read the first few bytes of the file (enough for magic number check)
    if expected_type == "image/png":
        file_bytes = await file.read(10)
        # PNG magic number (89 50 4E 47 0D 0A 1A 0A)
        if file_bytes[:8] != b"\x89\x50\x4E\x47\x0D\x0A\x1A\x0A":
            raise HTTPException(
                status_code=400,
                detail="Invalid file format. Please upload a valid PNG image.",
            )
    elif expected_type == "audio/mpeg":
        file_bytes = await file.read(10)
        if not (file_bytes.startswith(b"ID3") or file_bytes[:2] == b"\xff\xfb"):
            raise HTTPException(
                status_code=400,
                detail="Invalid file format. Please upload a valid MP3 audio file.",
            )
    await file.seek(0)
    return await file.read()

def generate_backgrounds(jacket_bytes: bytes): # read api/charts/edit.py
    jacket_pil_image = Image.open(io.BytesIO(jacket_bytes))

    v1 = pjsk_bg.render_v1(jacket_pil_image)
    v3 = pjsk_bg.render_v3(jacket_pil_image)

    v1_buffer = io.BytesIO()
    v1.save(v1_buffer, format="PNG")
    v1_bytes = v1_buffer.getvalue()
    v1_buffer.close()

    v3_buffer = io.BytesIO()
    v3.save(v3_buffer, format="PNG")
    v3_bytes = v3_buffer.getvalue()
    v3_buffer.close()

    return v1_bytes, v3_bytes

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
        data = ChartUploadData.model_validate_json(data)
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
        pass # Why bother checking? If it comes from converter, it's always gzip. If it comes from client, it's never gzip (at least shouldn't be)
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