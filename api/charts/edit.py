donotload = False

import uuid, io, asyncio

from fastapi import APIRouter, Request, HTTPException, status, UploadFile, Form

from database import charts, accounts

from helpers.models import ChartEditData
from helpers.sha1 import calculate_sha1

# WARNING: not async!!
# WARNING: heavy workload!!
import pjsk_background_gen_PIL as pjsk_bg
from PIL import Image

from typing import Optional, Literal

from pydantic import ValidationError

router = APIRouter()


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


def setup():
    @router.patch("/")
    async def main(
        request: Request,
        data: str = Form(...),
        jacket_image: Optional[UploadFile] = None,
        chart_file: Optional[UploadFile] = None,
        audio_file: Optional[UploadFile] = None,
        preview_file: Optional[UploadFile] = None,
        background_image: Optional[UploadFile] = None,
    ):
        try:
            data: ChartEditData = ChartEditData.model_validate_json(data)
        except ValidationError as e:
            raise HTTPException(status_code=422, detail=e.errors())
        auth = request.headers.get("authorization")
        # this is a PUBLIC route, don't check for private auth, only user auth
        if not auth:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Not logged in."
            )
        session_data = request.app.decode_key(auth)
        if session_data["type"] != "game":  # XXX: switch to external
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Invalid token type."
            )
        query, args = accounts.generate_get_account_from_session_query(
            session_data["user_id"], auth, "game"  # XXX: switch to external
        )
        async with request.app.db.acquire() as conn:
            result = await conn.fetchrow(query, *args)
            if not result:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED, detail="Not logged in."
                )
            if result["banned"]:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN, detail="User banned."
                )

        MAX_FILE_SIZES = {
            "jacket": 5 * 1024 * 1024,  # 5 MB
            "chart": 10 * 1024 * 1024,  # 10 MB
            "audio": 25 * 1024 * 1024,  # 20 MB
            "preview": 5 * 1024 * 1024,  # 5 MB
            "background": 10 * 1024 * 1024,  # 10 MB
        }

        query, args = charts.generate_get_chart_by_id_query(data.chart_id)
        async with request.app.db.acquire() as conn:
            result = await conn.fetchrow(query, *args)
            if not result:
                raise HTTPException(status_code=404, detail="Chart not found.")
            old_chart_data = dict(result)

        s3_uploads = []
        old_deletes = []

        if chart_file:
            if chart_file.size > MAX_FILE_SIZES["chart"]:
                raise HTTPException(
                    status_code=status.HTTP_406_NOT_ACCEPTABLE,
                    detail="Uploaded files exceed file size limit.",
                )
            if data.includes_chart:
                # XXX: only needed before file converter
                start = await chart_file.read(2)
                await chart_file.seek(0)
                if start[:2] == b"\x1f\x8b":  # GZIP magic number
                    pass
                else:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Invalid file format.",
                    )
                chart_bytes = await chart_file.read()
                # TODO: implement level converter
                # pip install git+https://github.com/UntitledCharts/sonolus-level-converters
                # except it's not done :heh:
                # for testing purpouse a real level packer :sob:
                chart_hash = calculate_sha1(chart_bytes)
                if not chart_hash == old_chart_data["chart_file_hash"]:
                    s3_uploads.append(
                        {
                            "path": f"{session_data['user_id']}/{data.chart_id}/{chart_hash}",
                            "hash": chart_hash,
                            "bytes": chart_bytes,
                            "content-type": "application/gzip",
                        }
                    )
                    old_deletes.append("chart_file_hash")
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Includes unexpected file.",
                )
        elif data.includes_chart:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="File not found."
            )
        if jacket_image:
            if jacket_image.size > MAX_FILE_SIZES["jacket"]:
                raise HTTPException(
                    status_code=status.HTTP_406_NOT_ACCEPTABLE,
                    detail="Uploaded files exceed file size limit.",
                )
            if data.includes_jacket:
                jacket_bytes = await get_and_check_file(jacket_image, "image/png")
                jacket_hash = calculate_sha1(jacket_bytes)
                if not jacket_hash == old_chart_data["jacket_file_hash"]:
                    s3_uploads.append(
                        {
                            "path": f"{session_data['user_id']}/{data.chart_id}/{jacket_hash}",
                            "hash": jacket_hash,
                            "bytes": jacket_bytes,
                            "content-type": "image/png",
                        }
                    )
                    old_deletes.append("jacket_file_hash")

                    def generate_backgrounds(jacket_bytes: bytes):
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

                    v1, v3 = await request.app.run_blocking(
                        generate_backgrounds, jacket_bytes
                    )
                    v1_hash = calculate_sha1(v1)
                    s3_uploads.append(
                        {
                            "path": f"{session_data['user_id']}/{data.chart_id}/{v1_hash}",
                            "hash": v1_hash,
                            "bytes": v1,
                            "content-type": "image/png",
                        }
                    )
                    v3_hash = calculate_sha1(v3)
                    s3_uploads.append(
                        {
                            "path": f"{session_data['user_id']}/{data.chart_id}/{v3_hash}",
                            "hash": v3_hash,
                            "bytes": v3,
                            "content-type": "image/png",
                        }
                    )
                    old_deletes.append("background_v1_file_hash")
                    old_deletes.append("background_v3_file_hash")
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Includes unexpected file.",
                )
        elif data.includes_jacket:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="File not found."
            )
        if audio_file:
            if audio_file.size > MAX_FILE_SIZES["audio"]:
                raise HTTPException(
                    status_code=status.HTTP_406_NOT_ACCEPTABLE,
                    detail="Uploaded files exceed file size limit.",
                )
            if data.includes_audio:
                audio_bytes = await get_and_check_file(audio_file, "audio/mpeg")
                audio_hash = calculate_sha1(audio_bytes)
                if not audio_hash == old_chart_data["music_file_hash"]:
                    s3_uploads.append(
                        {
                            "path": f"{session_data['user_id']}/{data.chart_id}/{audio_hash}",
                            "hash": audio_hash,
                            "bytes": audio_bytes,
                            "content-type": "audio/mpeg",
                        }
                    )
                    old_deletes.append("music_file_hash")
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Includes unexpected file.",
                )
        elif data.includes_audio:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="File not found."
            )
        if preview_file:
            if preview_file.size > MAX_FILE_SIZES["preview"]:
                raise HTTPException(
                    status_code=status.HTTP_406_NOT_ACCEPTABLE,
                    detail="Uploaded files exceed file size limit.",
                )
            if data.includes_preview and not data.delete_preview:
                preview_bytes = await get_and_check_file(preview_file, "audio/mpeg")
                preview_hash = calculate_sha1(preview_bytes)
                if not preview_hash == old_chart_data["preview_file_hash"]:
                    s3_uploads.append(
                        {
                            "path": f"{session_data['user_id']}/{data.chart_id}/{preview_hash}",
                            "hash": preview_hash,
                            "bytes": preview_bytes,
                            "content-type": "audio/mpeg",
                        }
                    )
                    old_deletes.append("preview_file_hash")
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Includes unexpected file.",
                )
        elif data.delete_preview and not data.includes_preview:
            old_deletes.append("preview_file_hash")
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Can't delete and include.",
            )
        if background_image:
            if background_image.size > MAX_FILE_SIZES["background"]:
                raise HTTPException(
                    status_code=status.HTTP_406_NOT_ACCEPTABLE,
                    detail="Uploaded files exceed file size limit.",
                )
            if data.includes_background and not data.delete_background:
                background_bytes = await get_and_check_file(
                    background_image, "image/png"
                )
                background_hash = calculate_sha1(background_bytes)
                if not background_hash == old_chart_data["background_file_hash"]:
                    s3_uploads.append(
                        {
                            "path": f"{session_data['user_id']}/{data.chart_id}/{background_hash}",
                            "hash": background_hash,
                            "bytes": background_bytes,
                            "content-type": "image/png",
                        }
                    )
                    old_deletes.append("background_file_hash")
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Includes unexpected file.",
                )
        elif data.delete_background and not data.includes_background:
            old_deletes.append("background_file_hash")
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Can't delete and include.",
            )

        all_hash_keys = {
            "background_file_hash",
            "background_v1_file_hash",
            "background_v3_file_hash",
            "jacket_file_hash",
            "chart_file_hash",
            "music_file_hash",
            "preview_file_hash",
        }
        old_deletes_set = set(old_deletes)
        kept_hash_keys = all_hash_keys - old_deletes_set
        kept_hashes = set(
            old_chart_data[hash_key]
            for hash_key in kept_hash_keys
            if hash_key in old_chart_data
        )
        deleted_candidate_hashes = set(
            old_chart_data[hash_key]
            for hash_key in old_deletes
            if hash_key in old_chart_data
        )
        deleted_hashes = deleted_candidate_hashes - kept_hashes
        if deleted_hashes or s3_uploads:
            async with request.app.s3_session.resource(
                **request.app.s3_resource_options
            ) as s3:
                bucket = await s3.Bucket(request.app.s3_bucket)
                tasks = []
                alr_deleted_hashes = []
                for file_hash in deleted_hashes:
                    if file_hash in alr_deleted_hashes:
                        continue
                    key = f"{session_data['user_id']}/{data.chart_id}/{file_hash}"
                    obj = bucket.Object(key)
                    task = obj.delete()
                    tasks.append(task)
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
        query, args = charts.generate_update_metadata_query(
            chart_id=data.chart_id,
            chart_author=data.author,
            rating=data.rating,
            title=data.title,
            artists=data.artists,
            tags=data.tags or None,
            description=data.description if data.description.strip() != "" else None,
            update_none_description=False if data.description.strip() != "" else True,
        )
        query2, args2 = charts.generate_update_file_hash_query(
            chart_id=data.chart_id,
            jacket_hash=jacket_hash if data.includes_jacket and jacket_image else None,
            v1_hash=v1_hash if data.includes_jacket and jacket_image else None,
            v3_hash=v3_hash if data.includes_jacket and jacket_image else None,
            music_hash=audio_hash if data.includes_audio and audio_file else None,
            chart_hash=chart_hash if data.includes_chart and chart_file else None,
            preview_hash=(
                preview_hash if data.includes_preview and preview_file else None
            ),
            background_hash=(
                background_hash
                if data.includes_background and background_image
                else None
            ),
            confirm_change=True,
            update_none_preview=True if data.delete_preview else False,
            update_none_background=True if data.delete_background else False,
        )

        async with request.app.db.acquire() as conn:
            res1 = await conn.execute(query, *args)
            res2 = await conn.execute(query2, *args2)
            print(res1, res2)
        return {"result": "success"}
