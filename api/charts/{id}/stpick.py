import uuid, io, asyncio
from core import ChartFastAPI

from fastapi import APIRouter, Request, HTTPException, status, UploadFile, Form
from helpers.session import get_session, Session

from database import charts

from helpers.webhook_handler import WebhookMessage, WebhookEmbed
from helpers.sanitizers import sanitize_md
from helpers.urls import url_creator

from helpers.models import ChartStPickData

router = APIRouter()


@router.patch("/")
async def main(
    request: Request,
    id: str,
    data: ChartStPickData,
    session: Session = get_session(
        enforce_auth=True, enforce_type="game", allow_banned_users=False
    ),
):
    if len(id) != 32 or not id.isalnum():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid chart ID."
        )
    app: ChartFastAPI = request.app
    user = await session.user()

    if not user.mod:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="not mod")

    query = charts.set_staff_pick(chart_id=id, value=data.value)

    async with app.db_acquire() as conn:
        result = await conn.fetchrow(query)
        if result:
            if data.value == True:
                if (app.config["discord"]["staff-pick-webhook"]).strip() != "":
                    wmsg = WebhookMessage(
                        app.config["discord"]["staff-pick-webhook"],
                        app.config["discord"]["avatar-url"],
                        app.config["discord"]["username"],
                    )
                    wembeds = [
                        WebhookEmbed()
                        .set_description("# 🏆 新着 StaffPick! / New Staff Pick!")
                        .set_color("PURPLE")
                    ]
                    wembed = (
                        WebhookEmbed()
                        .set_title(sanitize_md(result.title))
                        .set_description(
                            f"- *{sanitize_md(result.artists)}*\n譜面作者 / Charted by: `{sanitize_md(result.author_full)}`\n\n今すぐプレイ！ / Play it now!\n{url_creator(app.config['server']['sonolus-server-url'], 'levels', app.config['server']['sonolus-server-chart-prefix'] + result.id, as_sonolus_open=True)}"
                        )
                        .set_timestamp(True)
                        .set_thumbnail(
                            url_creator(
                                app.s3_asset_base_url,
                                result.author,
                                result.id,
                                result.jacket_file_hash,
                            )
                        )
                        .set_color("YELLOW")
                    )
                    wembeds.append(wembed)
                    for embed in wembeds:
                        wmsg.add_embed(embed)
                    await wmsg.send()
            return {"id": result.id}
        raise HTTPException(
            status=status.HTTP_404_NOT_FOUND,
            detail=f'Chart with ID "{id}" not found for any user!',
        )
