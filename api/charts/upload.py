donotload = False

from fastapi import APIRouter, Request, HTTPException, status, UploadFile, File

from database import charts, accounts

from helpers.models import ChartUploadData
from helpers.sha1 import calculate_sha1

from typing import Optional, Literal

router = APIRouter()


async def get_and_check_file(file, expected_type: Literal["image/png", "audio/mp3"]):
    # Read the first few bytes of the file (enough for magic number check)
    file_bytes = await file.read(10)

    if expected_type == "image/png":
        # PNG magic number (89 50 4E 47 0D 0A 1A 0A)
        if file_bytes[:8] != b"\x89\x50\x4E\x47\x0D\x0A\x1A\x0A":
            raise HTTPException(
                status_code=400,
                detail="Invalid file format. Please upload a valid PNG image.",
            )
    elif expected_type == "audio/mp3":
        # MP3 magic number (FF FB or FF F3 or FF F2)
        if not (
            file_bytes[:2] == b"\xFF\xFB"
            or file_bytes[:2] == b"\xFF\xF3"
            or file_bytes[:2] == b"\xFF\xF2"
        ):
            raise HTTPException(
                status_code=400,
                detail="Invalid file format. Please upload a valid MP3 audio file.",
            )
    await file.seek(0)
    return await file.read()


def setup():
    @router.post("/")
    async def main(
        request: Request,
        data: ChartUploadData,
        jacket_image: UploadFile,
        chart_file: UploadFile,
        audio_file: UploadFile,
        preview_file: Optional[UploadFile] = None,
        background_image: Optional[UploadFile] = None,
    ):
        auth = request.headers.get("authorization")
        # this is a PUBLIC route, don't check for private auth
        if not auth:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Not logged in."
            )
        query, args = accounts.generate_get_account_from_session_query(
            data.sonolus_id, auth, "external"
        )
        # XXX: debugging! let's not even check if account is valid rn lol, we don't even have external auth

        MAX_FILE_SIZES = {
            "jacket": 10 * 1024 * 1024,  # 10 MB
            "chart": 10 * 1024 * 1024,  # 10 MB
            "audio": 25 * 1024 * 1024,  # 20 MB
            "preview": 5 * 1024 * 1024,  # 5 MB
            "background": 15 * 1024 * 1024,  # 15 MB
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

        jacket_bytes = await get_and_check_file(jacket_image, "image/png")
        jacket_hash = calculate_sha1(jacket_bytes)
        await upload_to_s3(jacket_image, jacket_hash)

        chart_bytes = await chart_file.read()
        chart_hash = calculate_sha1(chart_bytes)
        await upload_to_s3(chart_file, chart_hash)

        audio_bytes = await get_and_check_file(audio_file, "audio/mp3")
        audio_hash = calculate_sha1(audio_bytes)
        await upload_to_s3(audio_file, audio_hash)

        if preview_file:
            preview_bytes = await get_and_check_file(preview_file, "audio/mp3")
            preview_hash = calculate_sha1(preview_bytes)
            await upload_to_s3(preview_bytes, preview_hash)

        # Optional: Reading bytes and calculating hash for background image
        if background_image:
            background_bytes = await get_and_check_file(background_image, "image/png")
            background_hash = calculate_sha1(background_bytes)
            await upload_to_s3(background_image, background_hash)

        query, args = charts.generate_create_chart_query(
            author="delete_me",# XXX: sonolus id except we're not grabbing account yet
            title=data.title,
            artists=data.artists,
            tags=data.tags or [],
            jacket_hash=jacket_hash,
            music_hash=audio_hash,
            chart_hash=chart_hash,
            preview_hash=preview_hash if preview_file else None,
            background_hash=background_hash if background_image else None,
        )

        async with request.app.db.acquire() as conn:
            result = await conn.fetchrow(query, *args)
            if result:
                id = result["id"]
                if id:
                    query, args = charts.generate_get_chart_by_id_query(
                        data.id
                    )
                    res = await conn.fetchrow(query, *args)
                    print(res)
                return {"id": result["id"]}
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error while processing session result.",
            )
