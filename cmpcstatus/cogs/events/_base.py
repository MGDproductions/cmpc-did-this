import asyncio
import datetime
import logging
from typing import Mapping

import discord
from discord import Embed, TextChannel
from discord.ext import tasks

from cmpcstatus.cogs import BotCog
from cmpcstatus.constants import (
    CHANNEL_PERMISSIONS_HIDDEN,
    CHANNEL_PERMISSIONS_LOCKED,
    CHANNEL_PERMISSIONS_OPEN,
    COLOUR_BLUE,
    COUNTDOWN_MINUTE,
    TESTING,
    TEXT_CHANNEL_FISH,
    TZ_AMSTERDAM,
)
from cmpcstatus.util import get_asset

log = logging.getLogger(__name__)


if TESTING:
    COUNTDOWN_MINUTE = 2


# todo docstrings for everything
def loop(func: tasks.LF, time: datetime.time) -> tasks.Loop:
    event = tasks.Loop(
        func,
        seconds=discord.utils.MISSING,
        minutes=discord.utils.MISSING,
        hours=discord.utils.MISSING,
        time=time,
        count=None,
        reconnect=True,
    )
    return event


class EventCog(BotCog):
    name: str
    channel_id: int
    channel_name: str
    channel_topic: str

    mention: str
    start_filename: str
    start_message: str
    end_filename: str
    end_message: str

    start_time: datetime.time
    lock_time: datetime.time
    end_time: datetime.time

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.event_start = loop(self.event_start, self.start_time)
        self.event_lock = loop(self.event_lock, self.lock_time)
        self.event_end = loop(self.event_end, self.end_time)

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
        channel: TextChannel, permissions: Mapping[str, bool], reason: str
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
        raise NotImplementedError

    def is_end_date(self) -> bool:
        raise NotImplementedError

    def get_channel(self) -> TextChannel:
        channel = self.bot.get_channel(self.channel_id)
        if channel is None:
            raise ValueError(f"Could not find channel {TEXT_CHANNEL_FISH}")
        return channel

    async def send_start_message(self, channel: TextChannel):
        with get_asset(self.start_filename) as path:
            await channel.send(self.start_message, file=discord.File(path))

    async def event_start(self):
        # only run on wednesday
        if not TESTING and not self.is_start_date():
            return
        log.info(f"%s started", self.name)
        channel = self.get_channel()

        # edit channel
        await channel.edit(name=self.channel_name, topic=self.channel_topic)
        # open channel
        await self.update_permissions(
            channel, CHANNEL_PERMISSIONS_OPEN, f"{self.name} start"
        )

        # send start message
        await self.send_start_message(channel)

    async def event_lock(self):
        # only run on thursday (end of wednesday)
        if not TESTING and not self.is_end_date():
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

    async def event_end(self):
        if not TESTING and not self.is_end_date():
            return
        log.info("%s ended", self.name)
        channel = self.get_channel()

        # hide channel
        await self.update_permissions(
            channel, CHANNEL_PERMISSIONS_HIDDEN, f"{self.name} end"
        )
