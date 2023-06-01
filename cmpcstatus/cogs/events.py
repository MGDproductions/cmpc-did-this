import asyncio
import datetime
import logging

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

log = logging.getLogger(__name__)


class FishGamingWednesday(BotCog):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.tasks = (
            self.fgw_start,
            self.fgw_lock,
            self.fgw_end,
        )

    async def cog_load(self):
        for t in self.tasks:
            t.start()

    async def cog_unload(self):
        for t in self.tasks:
            t.stop()

    @staticmethod
    def is_today(day: int) -> bool:
        datetime_amsterdam = datetime.datetime.now(TZ_AMSTERDAM)
        result = datetime_amsterdam.isoweekday() == day
        log.info("day-of-week check %d : %s : %s", day, datetime_amsterdam, result)
        return result

    def get_fish_channel(self) -> discord.TextChannel:
        channel = self.bot.get_channel(TEXT_CHANNEL_FISH)
        if channel is None:
            raise ValueError(f"Could not find channel {TEXT_CHANNEL_FISH}")
        return channel

    @tasks.loop(time=TIME_FGW_START)
    async def fgw_start(self):
        # only run on wednesday
        if not self.is_today(ISO_WEEKDAY_WEDNESDAY):
            return
        log.info("fish gaming wednesday started")
        channel = self.get_fish_channel()

        perms = channel.overwrites_for(channel.guild.default_role)
        perms.update(**CHANNEL_PERMISSIONS_OPEN)
        await channel.set_permissions(
            channel.guild.default_role, overwrite=perms, reason="fgw_start"
        )
        await channel.send(f"<@&{ROLE_FISH}>", file=discord.File("assets/fgw.mp4"))

    @tasks.loop(time=TIME_FGW_LOCK)
    async def fgw_lock(self):
        # only run on thursday (end of wednesday)
        if not self.is_today(ISO_WEEKDAY_THURSDAY):
            return
        log.info("fish gaming wednesday ending")
        channel = self.get_fish_channel()

        # set channel to read-only
        perms = channel.overwrites_for(channel.guild.default_role)
        perms.update(**CHANNEL_PERMISSIONS_LOCKED)
        await channel.set_permissions(
            channel.guild.default_role, overwrite=perms, reason="fgw_lock"
        )

        # create countdown message
        embed = Embed(title="Fish gaming wednesday has ended.", color=COLOUR_BLUE)
        filename = "fgwends.png"
        embed.set_image(url=f"attachment://{filename}")
        file = discord.File(f"assets/{filename}", filename=f"{filename}")
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

    @tasks.loop(time=TIME_FGW_END)
    async def fgw_end(self):
        if not self.is_today(ISO_WEEKDAY_THURSDAY):
            return
        log.info("fish gaming wednesday ended")
        channel = self.get_fish_channel()

        # hide channel
        perms = channel.overwrites_for(channel.guild.default_role)
        perms.update(**CHANNEL_PERMISSIONS_HIDDEN)
        await channel.set_permissions(
            channel.guild.default_role, overwrite=perms, reason="fgw_end"
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

        file = discord.File("assets/birthday.mp4")
        await channel.send(
            f"{EMOJI_BIBI_PARTY}{EMOJI_BIBI_PARTY}{EMOJI_BIBI_PARTY} @everyone It's Marcel's birthday today!"
            " As a birthday gift he wants all the cat pictures in the world."
            f" Drop them in this chat before he wakes up!{EMOJI_BIBI_PARTY}{EMOJI_BIBI_PARTY}{EMOJI_BIBI_PARTY}",
            file=file,
        )
