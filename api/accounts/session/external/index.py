import uuid, json, base64, hashlib
import hmac
from core import ChartFastAPI

from fastapi import APIRouter, Request, HTTPException, status

from database import accounts, external

from helpers.models import ExternalServiceUserProfileWithType

router = APIRouter()


def setup():
    @router.post("/")
    async def main(request: Request, data: ExternalServiceUserProfileWithType):
        """
        We support a maximum of 6 sessions:
        - 3 external (eg. website)
        - 3 in-game

        This route will replace any expired or nonexistent session.

        If all sessions are not expired, we replace the OLDEST session.
        """
        app: ChartFastAPI = request.app

        if request.headers.get(app.auth_header) != app.auth:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="why?")

        id_data = app.decode_key(data.id_key, return_dict=True)

        session_key_data = {
            "id": id_data["id"],
            "user_id": data.id,
            "type": data.type,
        }
        encoded_key = base64.urlsafe_b64encode(
            json.dumps(session_key_data).encode()
        ).decode()
        signature = hmac.new(
            app.token_secret_key.encode(), encoded_key.encode(), hashlib.sha256
        ).hexdigest()
        session_key = f"{encoded_key}.{signature}"
        query, args = (
            accounts.generate_create_account_if_not_exists_and_new_session_query(
                session_key, data.id, int(data.handle), data.type
            )
        )
        query2, args2 = external.generate_update_session_key_query(
            id_key=data.id_key, session_key=session_key
        )

        async with app.db.acquire() as conn:
            result = await conn.fetchrow(query, *args)
            await conn.execute(query2, *args2)

            if result:
                session_key = result["session_key"]
                expiry = int(result["expires"])
                return {"session": session_key, "expiry": expiry}
            # account was created
            # run it again

            result = await conn.fetchrow(query, *args)
            if result:
                session_key = result["session_key"]
                expiry = int(result["expires"])
                return {"session": session_key, "expiry": expiry}

            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error while processing session result.",
            )
