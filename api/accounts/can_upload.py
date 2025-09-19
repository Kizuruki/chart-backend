import json
import time
from core import ChartFastAPI

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from database import accounts
from helpers.session import get_session, Session

router = APIRouter()

raise NotImplementedError()


@router.get("/")
async def main(
    request: Request,
    session: Session = get_session(
        enforce_auth=True,
        enforce_type="external",
        allow_banned_users=False,
    ),
):
    app: ChartFastAPI = request.app
    pool = app.db

    user = await session.user()
    oauth = json.loads(user.oauth_details)
    discord_oauth = oauth.get("discord")

    if not discord_oauth:
        return JSONResponse(content={}, status_code=403)

    now = int(time.time())

    if now >= discord_oauth.get("expires_at", 0):
        refreshed = await refresh_discord_token(session.sonolus_id, discord_oauth, app)
        if not refreshed:
            query = accounts.delete_oauth(session.sonolus_id, "discord")
            async with app.db_acquire() as conn:
                await conn.execute(query)
            return JSONResponse(content={}, status_code=403)
        token = refreshed
    else:
        token = discord_oauth

    user_resp = await app.oauth.discord.get("users/@me", token=token)
    if user_resp.status_code != 200:
        # Assume manually unlinked
        query = accounts.delete_oauth(session.sonolus_id, "discord")
        async with app.db_acquire() as conn:
            await conn.execute(query)
        return JSONResponse(content={}, status_code=403)
    user_data = await user_resp.json()

    guilds_resp = await app.oauth.discord.get("users/@me/guilds", token=token)
    if guilds_resp.status_code != 200:
        return JSONResponse(content={}, status_code=403)
    guilds_data = await guilds_resp.json()

    required_guild = app.config["oauth"]["required-discord-server"]
    in_guild = any(guild["id"] == required_guild for guild in guilds_data)

    return JSONResponse(
        {
            "id": user_data["id"],
            "username": f"{user_data['username']}",
            "avatar": user_data["avatar"],
            "in_guild": in_guild,
        }
    )


async def refresh_discord_token(sonolus_id: str, oauth: dict, app: ChartFastAPI):
    """Refresh Discord token using app.oauth.discord."""
    try:
        token = await app.oauth.discord.refresh_token(
            token_url="https://discord.com/api/v10/oauth2/token",
            refresh_token=oauth["refresh_token"],
            client_id=app.discord_client_id,
            client_secret=app.discord_client_secret,
        )
    except Exception:
        return None

    now = int(time.time())
    refreshed = {
        "access_token": token["access_token"],
        "refresh_token": token.get("refresh_token", oauth["refresh_token"]),
        "expires_at": now + token.get("expires_in", 3600),
    }

    query = accounts.add_oauth(
        sonolus_id,  # TODO: convert these to OAuth()
        refreshed["access_token"],
        refreshed["refresh_token"],
        refreshed["expires_at"],
        "discord",
    )
    pool = app.db
    async with pool.acquire() as conn:
        await conn.execute(query)

    return refreshed
