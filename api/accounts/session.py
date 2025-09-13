donotload = False

from fastapi import APIRouter, Request, HTTPException, status

from database import accounts

from helpers.models import ServiceUserProfileWithType

router = APIRouter()


def setup():
    @router.post("/")
    async def main(request: Request, data: ServiceUserProfileWithType):
        """
        We support a maximum of 6 sessions:
        - 3 external (eg. website)
        - 3 in-game

        This route will replace any expired or nonexistent session.

        If all sessions are not expired, we replace the OLDEST session.
        """
        if request.headers.get(request.app.auth_header) != request.app.auth:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="why?")
        query, args = (
            accounts.generate_create_account_if_not_exists_and_new_session_query(
                data.id, int(data.handle), data.type
            )
        )

        async with request.app.db.acquire() as conn:
            result = await conn.fetchrow(query, *args)
            if result:
                session_key = result["session_key"]
                expiry = int(result["expires"])
                return {"session": session_key, "expiry": expiry}
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error while processing session result.",
            )
