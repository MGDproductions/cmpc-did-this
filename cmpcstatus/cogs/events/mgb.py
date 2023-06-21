import datetime
import logging

import discord
from discord import TextChannel

from cmpcstatus.cogs.events import EventCog
from cmpcstatus.constants import (
    DATE_BIRTHDAY_DAY,
    DATE_BIRTHDAY_MONTH,
    EMOJI_BIBI_PARTY,
    TESTING,
    TEXT_CHANNEL_BIRTHDAY,
    TIME_BDAY_END,
    TIME_BDAY_LOCK,
    TIME_BDAY_START,
    TZ_AMSTERDAM,
)
from cmpcstatus.util import get_asset

log = logging.getLogger(__name__)


class MarcelGamingBirthday(EventCog):
    name = "Marcel's birthday"
    channel_id = TEXT_CHANNEL_BIRTHDAY
    channel_name = "marcel-gaming-birthday"
    channel_topic = (
        "conversation doesn't have to be about gaming,"
        " chat that's only accessible on birthday my dudes (GMT + 1)"
    )

    if TESTING:
        mention = f"<@329885271787307008>"
    else:
        mention = "@everyone"
    start_filename = "birthday.mp4"
    start_message = (
        f"{EMOJI_BIBI_PARTY}{EMOJI_BIBI_PARTY}{EMOJI_BIBI_PARTY}\n"
        f"{mention} It's Marcel's birthday today!"
        " As a birthday gift he wants all the cat pictures in the world."
        " Drop them in this chat before he wakes up!"
        f"\n{EMOJI_BIBI_PARTY}{EMOJI_BIBI_PARTY}{EMOJI_BIBI_PARTY}"
    )
    end_filename = "mgbends.png"
    end_message = f"{name} has ended."

    start_time = TIME_BDAY_START
    lock_time = TIME_BDAY_LOCK
    end_time = TIME_BDAY_END

    @staticmethod
    def is_date(month: int, day: int) -> bool:
        datetime_amsterdam = datetime.datetime.now(TZ_AMSTERDAM)
        result = (month, day) == (datetime_amsterdam.month, datetime_amsterdam.day)
        log.info("date check %d-%d : %s : %s", month, day, datetime_amsterdam, result)
        return result

    def is_start_date(self) -> bool:
        return self.is_date(DATE_BIRTHDAY_MONTH, DATE_BIRTHDAY_DAY)

    def is_end_date(self) -> bool:
        return self.is_date(DATE_BIRTHDAY_MONTH, DATE_BIRTHDAY_DAY + 1)

    async def send_start_message(self, channel: TextChannel):
        # regular message
        await channel.send(self.start_message)
        # video in the hydraulic press
        for asset in ("press_1.png", "birthday_bounce.webm", "press_1_vertical.png"):
            with get_asset(asset) as path:
                await channel.send(file=discord.File(path))
        await channel.send(
            "damn I put the birthday vido in THE PRESS "
            "and it got squished im fucking sory compressipn gone wrong"
        )
        await channel.send("marcel agming biethday")
        with get_asset("mgb.mp4") as path:
            await channel.send(file=discord.File(path))
