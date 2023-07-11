import datetime
import logging
import re
from typing import NamedTuple

import discord
import discord.ext.tasks
from bs4 import BeautifulSoup, Tag

from ._base import BotCog
from cmpcstatus.constants import (
    ISO_WEEKDAY_THURSDAY,
    TESTING,
    TZ_AMSTERDAM,
    TEXT_CHANNEL_GENERAL,
    USER_JMCB,
)

ROLE_GAMING_GANG = 785222184309489665
TIME_EPIC_FREE_GAME = datetime.time(hour=17, tzinfo=TZ_AMSTERDAM)
RE_GAME1 = re.compile(
    r"Free Games, 1 of 2, Free Now, (.+), Free Now - [A-Z][a-z]{2} \d{2} at \d{2}:\d{2} (AM|PM), \d{4}"
)
URL_BASE = "https://store.epicgames.com"


log = logging.getLogger(__name__)


class Game(NamedTuple):
    name: str
    url: str
    image_url: str


class EpicFreeGame(BotCog):
    channel_id = TEXT_CHANNEL_GENERAL

    start_time = TIME_EPIC_FREE_GAME
    if TESTING:
        mention = f"<@{USER_JMCB}>"
    else:
        mention = f"<@&{ROLE_GAMING_GANG}>"
    start_message = f"{mention} new free game <{URL_BASE}>"

    @staticmethod
    def parse_game(tag: Tag) -> Game:
        title_tag = tag.find("div", attrs={"data-testid": "offer-title-info-title"})
        name = title_tag.text

        url_loc = tag.attrs["href"]
        url = URL_BASE + url_loc

        img_tag = tag.find("img")
        image_url = img_tag.attrs["src"]

        game = Game(name=name, url=url, image_url=image_url)
        return game

    @staticmethod
    def embed_from_game(game: Game) -> discord.Embed:
        embed = discord.Embed(title=game.name, url=game.url)
        embed.set_image(url=game.image_url)
        return embed

    async def get_free_game(self) -> Game:
        async with self.bot.session.get(f"{URL_BASE}/en-US/") as response:
            text = await response.text()

        soup = BeautifulSoup(text, features="html.parser")
        game1_tag = soup.find("a", attrs={"aria-label": RE_GAME1})
        game1 = self.parse_game(game1_tag)

        return game1

    @staticmethod
    def is_today(day: int) -> bool:
        datetime_amsterdam = datetime.datetime.now(TZ_AMSTERDAM)
        result = datetime_amsterdam.isoweekday() == day
        log.info("day-of-week check %d : %s : %s", day, datetime_amsterdam, result)
        return result

    def is_start_date(self) -> bool:
        return self.is_today(ISO_WEEKDAY_THURSDAY)

    @discord.ext.tasks.loop(time=TIME_EPIC_FREE_GAME)
    async def send_reminder(self):
        if not TESTING and not self.is_start_date():
            return
        log.info("sending EGS free game cry")

        game = await self.get_free_game()
        embed = self.embed_from_game(game)

        channel = self.bot.get_channel(self.channel_id)
        await channel.send(self.start_message, embed=embed)
