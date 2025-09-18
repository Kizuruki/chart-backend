from core import ChartFastAPI

import time

from fastapi import APIRouter, Request, status, HTTPException
from fastapi.responses import JSONResponse
from authlib.integrations.starlette_client import OAuth

from helpers.session import Session

from database import accounts

router = APIRouter()

raise NotImplementedError()


def setup():
    @router.get("/login")
    # XXX: oauth LOGIN as well, not just linking
    async def login_discord(
        request: Request,
        session=Session(
            enforce_auth=True, enforce_type="external", allow_banned_users=False
        ),
    ):
        await session.user()
        app: ChartFastAPI = request.app
        redirect_uri = request.url_for("link_discord")
        return await app.oauth.discord.authorize_redirect(request, redirect_uri)

    @router.get("/link")
    async def auth_discord(
        request: Request,
        session=Session(
            enforce_auth=True, enforce_type="external", allow_banned_users=False
        ),
    ):
        user = await session.user()
        if user["discord_id"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Already linked."
            )
        app: ChartFastAPI = request.app
        token = await app.oauth.discord.authorize_access_token(request)
        if not token:
            return JSONResponse(
                {"error": "OAuth failed"}, status_code=status.HTTP_403_FORBIDDEN
            )

        user_resp = await app.oauth.discord.get("users/@me", token=token)
        if user_resp.status_code != 200:
            return JSONResponse(
                {"error": "Failed to fetch user"}, status_code=status.HTTP_403_FORBIDDEN
            )
        user_data = user_resp.json()

        guilds_resp = await app.oauth.discord.get("users/@me/guilds", token=token)
        if guilds_resp.status_code != 200:
            return JSONResponse(
                {"error": "Failed to fetch guilds"},
                status_code=status.HTTP_403_FORBIDDEN,
            )
        guilds_data = guilds_resp.json()

        sonolus_id = session.sonolus_id
        expires_at = int(time.time()) + token.get("expires_in", 3600)
        query, args = accounts.generate_add_oauth_query(
            sonolus_id,
            token["access_token"],
            token["refresh_token"],
            expires_at,
            "discord",
        )
        await app.db.execute(query, *args)
        query, args = accounts.generate_link_discord_id_query(
            sonolus_id, discord_id=user_data["id"]
        )

        return JSONResponse({"user": user_data, "guilds": guilds_data, "token": token})
