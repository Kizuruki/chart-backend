import uuid, json, base64, hashlib
import hmac
from core import ChartFastAPI

from fastapi import APIRouter, Request, HTTPException, status

from database import external

router = APIRouter()


def setup():
    @router.post("/")
    async def main(request: Request):
        app: ChartFastAPI = request.app
        id_data = {"id": str(uuid.uuid4())}
        encoded_id = base64.urlsafe_b64encode(json.dumps(id_data).encode()).decode()
        signature = hmac.new(
            app.token_secret_key.encode(), encoded_id.encode(), hashlib.sha256
        ).hexdigest()
        id_key = f"{encoded_id}.{signature}"
        query, args = external.generate_create_external_login_query(id_key)

        async with app.db.acquire() as conn:
            result = await conn.fetchrow(query, *args)
            if result:
                id_key = result["id_key"]
                return {"id": id_key}
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error while processing generate result.",
            )
