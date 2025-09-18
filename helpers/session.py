from fastapi import Header, HTTPException, status, Request
from core import ChartFastAPI
from typing import Literal
from database import accounts


class Session:
    def __init__(
        self,
        enforce_auth: bool = False,
        enforce_type: Literal["game", "external", False] = False,
        allow_banned_users: bool = True,
    ):
        self.enforce_auth = enforce_auth
        self.enforce_type = enforce_type
        self.allow_banned_users = allow_banned_users
        self._user_fetched = False
        self._user = None

    async def user(self) -> dict:
        if not self._user_fetched:
            query, args = accounts.generate_get_account_from_session_query(
                self.session_data.user_id, self.auth, self.session_data.type
            )

            async with self.app.db.acquire() as conn:
                result = await conn.fetchrow(query, *args)

                if not result and self.enforce_auth:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Not logged in.",
                    )

                self._user = dict(result)
                self._user_fetched = True

        return self._user

    async def __call__(self, request: Request, authorization: str = Header(...)):
        self.app: ChartFastAPI = request.app
        self.auth = authorization

        if not authorization and self.enforce_auth:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Not logged in."
            )

        if authorization:
            self.session_data = self.app.decode_key(authorization)
            self.sonolus_id = self.session_data.user_id

            if self.enforce_type and self.session_data.type != self.enforce_type:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN, detail="Invalid token type."
                )

            if not self.allow_banned_users:
                if (await self.user())["banned"]:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN, detail="User banned."
                    )
        return self
