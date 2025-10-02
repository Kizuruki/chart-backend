import re, datetime

import aiohttp
from typing import Optional, List, Dict


class WebhookMessage:
    def __init__(
        self,
        url: str,
        avatar_url: Optional[str] = None,
        username: Optional[str] = None,
        content: Optional[str] = None,
    ):
        if avatar_url.strip() == "":
            avatar_url = None
        if username.strip() == "":
            username = None
        self.url = url
        self.avatar_url = avatar_url
        self.username = username
        self.content = content
        self.embeds = []

    def add_embed(self, embed: "WebhookEmbed") -> "WebhookMessage":
        self.embeds.append(embed)
        return self

    async def send(self) -> str:
        return await discord_send(
            self.url, self.embeds, self.avatar_url, self.username, self.content
        )


class WebhookEmbed:
    def __init__(self):
        self.content: Optional[str] = None
        self.title: Optional[str] = None
        self.description: Optional[str] = None
        self.fields: List[Dict[str, Optional[str]]] = []
        self.footer_text: Optional[str] = None
        self.footer_icon_url: Optional[str] = None
        self.thumbnail_url: Optional[str] = None
        self.color: Optional[str] = None
        self.timestamp: bool = False

    def set_content(self, content: str) -> "WebhookEmbed":
        self.content = content
        return self

    def set_title(self, title: str) -> "WebhookEmbed":
        self.title = title
        return self

    def set_description(self, description: str) -> "WebhookEmbed":
        self.description = description
        return self

    def add_field(self, name: str, value: str, inline: bool = False) -> "WebhookEmbed":
        self.fields.append({"name": name, "value": value, "inline": inline})
        return self

    def set_footer(self, text: str, icon_url: Optional[str] = None) -> "WebhookEmbed":
        self.footer_text = text
        self.footer_icon_url = icon_url
        return self

    def set_timestamp(self, timestamp: Optional[bool] = True) -> "WebhookEmbed":
        self.timestamp = timestamp
        return self

    def set_thumbnail(self, image_url: str) -> "WebhookEmbed":
        self.thumbnail_url = image_url
        return self

    def set_color(self, hex_or_name: str) -> "WebhookEmbed":
        color_map = {
            "RED": "#FF0000",
            "GREEN": "#00FF00",
            "YELLOW": "#FFFF00",
            "BLUE": "#0000FF",
            "ORANGE": "#FFA500",
            "PURPLE": "#800080",
            "WHITE": "#FFFFFF",
            "BLACK": "#000000",
        }

        if not isinstance(hex_or_name, str):
            raise ValueError("Color must be a string.")

        hex_or_name = hex_or_name.strip().upper()

        if hex_or_name in color_map:
            hex_value = color_map[hex_or_name]
        else:
            if not hex_or_name.startswith("#"):
                hex_or_name = f"#{hex_or_name}"

            if not re.match(r"^#[0-9A-F]{6}$", hex_or_name):
                raise ValueError(f"Invalid hex color: {hex_or_name}")

            hex_value = hex_or_name

        self.color = hex_value
        return self


def hex_to_decimal_color(hex_color: str) -> int:
    if not hex_color:
        return None
    hex_color = hex_color.strip().lstrip("#").upper()
    if len(hex_color) != 6:
        raise ValueError(f"Invalid hex color: {hex_color}")
    return int(hex_color, 16)


async def discord_send(
    url: str,
    embeds: List[WebhookEmbed],
    avatar_url: Optional[str] = None,
    username: Optional[str] = None,
    content: Optional[str] = None,
) -> str:
    serialized_embeds = []

    for embed_obj in embeds:
        embed = {}

        if embed_obj.title:
            embed["title"] = embed_obj.title
        if embed_obj.description:
            embed["description"] = embed_obj.description
        if embed_obj.fields:
            embed["fields"] = embed_obj.fields
        if embed_obj.footer_text:
            embed["footer"] = {"text": embed_obj.footer_text}
            if embed_obj.footer_icon_url:
                embed["footer"]["icon_url"] = embed_obj.footer_icon_url
        if embed_obj.timestamp:
            embed["timestamp"] = datetime.datetime.now(
                datetime.timezone.utc
            ).isoformat()
        if embed_obj.thumbnail_url:
            embed["thumbnail"] = {"url": embed_obj.thumbnail_url}
        if embed_obj.color:
            embed["color"] = hex_to_decimal_color(embed_obj.color)

        if embed == {}:
            embed["title"] = "​"
        serialized_embeds.append(embed)

    payload = {
        "username": username,
        "avatar_url": avatar_url,
        "content": content,
        "embeds": serialized_embeds,
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload) as response:
            return await response.text()
