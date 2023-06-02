import asyncio
import datetime
import logging
from typing import Mapping

import discord
from discord import Embed
from discord.ext import tasks

from cmpcstatus.cogs._base import BotCog
from cmpcstatus.constants import (
    CHANNEL_PERMISSIONS_HIDDEN,
    CHANNEL_PERMISSIONS_LOCKED,
    CHANNEL_PERMISSIONS_OPEN,
    COLOUR_BLUE,
    COUNTDOWN_MINUTE,
    DATE_BIRTHDAY_DAY,
    DATE_BIRTHDAY_MONTH,
    EMOJI_BIBI_PARTY,
    ISO_WEEKDAY_THURSDAY,
    ISO_WEEKDAY_WEDNESDAY,
    ROLE_FISH,
    TEXT_CHANNEL_BIRTHDAY,
    TEXT_CHANNEL_FISH,
    TIME_BIRTHDAY_START,
    TIME_FGW_END,
    TIME_FGW_LOCK,
    TIME_FGW_START,
    TZ_AMSTERDAM,
)
from cmpcstatus.util import get_asset

log = logging.getLogger(__name__)
# todo change back
COUNTDOWN_MINUTE = 2

class FishGamingWednesday(BotCog):
    # todo allow changing channel name and description
    name = "fish gaming wednesday"

    start_filename = "fgw.mp4"
    # todo change back
    #      add TESTING constant to handle that?
    # start_message = f"<@&{ROLE_FISH}>"
    start_message = f"<@329885271787307008>"
    end_filename = "fgwends.png"
    end_message = "Fish gaming wednesday has ended."

    start_time = TIME_FGW_START
    lock_time = TIME_FGW_LOCK
    end_time = TIME_FGW_END

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.tasks = (
            self.event_start,
            self.event_lock,
            self.event_end,
        )

    async def cog_load(self):
        for t in self.tasks:
            t.start()

    async def cog_unload(self):
        for t in self.tasks:
            t.stop()

    @staticmethod
    async def update_permissions(
        channel: discord.TextChannel, permissions: Mapping[str, bool], reason: str
    ):
        perms = channel.overwrites_for(channel.guild.default_role)
        perms.update(**permissions)
        await channel.set_permissions(
            channel.guild.default_role, overwrite=perms, reason=reason
        )

    @staticmethod
    def is_today(day: int) -> bool:
        datetime_amsterdam = datetime.datetime.now(TZ_AMSTERDAM)
        result = datetime_amsterdam.isoweekday() == day
        log.info("day-of-week check %d : %s : %s", day, datetime_amsterdam, result)
        return result

    def is_start_date(self) -> bool:
        return True
        # return self.is_today(ISO_WEEKDAY_WEDNESDAY)

    def is_end_date(self) -> bool:
        return True
        # return self.is_today(ISO_WEEKDAY_THURSDAY)

    def get_channel(self) -> discord.TextChannel:
        channel = self.bot.get_channel(TEXT_CHANNEL_FISH)
        if channel is None:
            raise ValueError(f"Could not find channel {TEXT_CHANNEL_FISH}")
        return channel

    @tasks.loop(time=start_time)
    async def event_start(self):
        # only run on wednesday
        if not self.is_start_date():
            return
        log.info(f"%s started", self.name)
        channel = self.get_channel()

        # open channel
        await self.update_permissions(
            channel, CHANNEL_PERMISSIONS_OPEN, f"{self.name} start"
        )

        with get_asset(self.start_filename) as path:
            await channel.send(self.start_message, file=discord.File(path))

    @tasks.loop(time=lock_time)
    async def event_lock(self):
        # only run on thursday (end of wednesday)
        if not self.is_end_date():
            return
        log.info(f"%s ending", self.name)
        channel = self.get_channel()

        # set channel to read-only
        await self.update_permissions(
            channel, CHANNEL_PERMISSIONS_LOCKED, f"{self.name} lock"
        )

        # create countdown message
        embed = Embed(title=self.end_message, color=COLOUR_BLUE)
        embed.set_image(url=f"attachment://{self.end_filename}")
        with get_asset(self.end_filename) as path:
            file = discord.File(path, filename=self.end_filename)
            message = await channel.send(embed=embed, file=file)

        # edit message until countdown ends
        embed.add_field(name="", value="")
        for i in range(5, 0, -1):
            s = "s" if i != 1 else ""
            name = f"In {i} minute{s} this channel will be hidden."
            embed.set_field_at(0, name=name, value="** **", inline=False)
            await message.edit(embed=embed)
            await asyncio.sleep(COUNTDOWN_MINUTE)

        # leave a final message
        embed.remove_field(0)
        await message.edit(embed=embed)

    @tasks.loop(time=end_time)
    async def event_end(self):
        if not self.is_end_date():
            return
        log.info("%s ended", self.name)
        channel = self.get_channel()

        # hide channel
        await self.update_permissions(
            channel, CHANNEL_PERMISSIONS_HIDDEN, f"{self.name} end"
        )


class Birthday(BotCog):
    async def cog_load(self):
        self.birthday_start.start()

    async def cog_unload(self):
        self.birthday_start.stop()

    @staticmethod
    def is_date(month: int, day: int) -> bool:
        datetime_amsterdam = datetime.datetime.now(TZ_AMSTERDAM)
        result = (month, day) == (datetime_amsterdam.month, datetime_amsterdam.day)
        log.info("date check %d-%d : %s : %s", month, day, datetime_amsterdam, result)
        return result

    @tasks.loop(time=TIME_BIRTHDAY_START)
    async def birthday_start(self):
        if not self.is_date(DATE_BIRTHDAY_MONTH, DATE_BIRTHDAY_DAY):
            return
        log.info("Marcel's birthday started")
        channel = self.bot.get_channel(TEXT_CHANNEL_BIRTHDAY)

        perms = channel.overwrites_for(channel.guild.default_role)
        perms.update(**CHANNEL_PERMISSIONS_OPEN)
        await channel.set_permissions(
            channel.guild.default_role, overwrite=perms, reason="birthday_start"
        )

        with get_asset("birthday.mp4") as path:
            file = discord.File(path)
            await channel.send(
                f"{EMOJI_BIBI_PARTY}{EMOJI_BIBI_PARTY}{EMOJI_BIBI_PARTY} "
                "@everyone It's Marcel's birthday today!"
                " As a birthday gift he wants all the cat pictures in the world."
                " Drop them in this chat before he wakes up!"
                f"{EMOJI_BIBI_PARTY}{EMOJI_BIBI_PARTY}{EMOJI_BIBI_PARTY}",
                file=file,
            )
