import logging
import subprocess
import sys
from typing import Literal, Optional

import discord
from discord import Member
from discord.ext import commands
from discord.ext.commands import Context

from cmpcstatus.cogs import BotCog
from cmpcstatus.cogs.epic import EpicFreeGame
from cmpcstatus.cogs.events import EventCog
from cmpcstatus.constants import ROLE_DEVELOPER


log = logging.getLogger(__name__)


class DeveloperCommands(BotCog):
    def cog_check(self, ctx: Context) -> bool:
        # see discord.commands.has_role
        if ctx.guild is None:
            raise commands.NoPrivateMessage
        role = discord.utils.get(ctx.author.roles, id=ROLE_DEVELOPER)
        if role is None:
            raise commands.MissingRole(ROLE_DEVELOPER)
        return True

    @commands.command(hidden=True)
    async def ptero(
        self,
        ctx: Context,
        signal: Literal["start", "stop", "restart", "kill"] = "restart",
    ):
        # https://github.com/iamkubi/pydactyl/blob/main/pydactyl/api/client/servers/base.py#L78
        message = f"Sending signal '{signal}'"
        log.info(message)
        await ctx.send(message)

        config = self.bot.config
        url = (
            f"{config.ptero_address}/api/client/servers/{config.ptero_server_id}/power"
        )
        payload = {"signal": signal}
        headers = {"Authorization": f"Bearer {config.ptero_token}"}
        async with self.bot.session.post(
            url, json=payload, headers=headers
        ) as response:
            response.raise_for_status()

    @commands.command(hidden=True)
    async def exit(self, ctx: Context):
        await ctx.send("OK")
        sys.exit()

    @commands.command(hidden=True)
    async def test_event(
        self,
        ctx: Context,
        member: Optional[Member],
        event: Literal["join", "remove"] = "join",
    ):
        log.info("Test event (%s) %s", member, event)
        events = {
            "join": self.bot.on_member_join,
            "remove": self.bot.on_member_remove,
        }
        member = member or ctx.author
        await events[event](member)

    @commands.command(hidden=True)
    async def test_fish(
        self, ctx: Context, event: Literal["start", "lock", "end"], name: str
    ):
        await ctx.send("Getting cog")
        cog = self.bot.get_cog(name)
        if cog is None:
            raise ValueError(f"No cog with name: {name}")
        if not isinstance(cog, EventCog):
            raise TypeError(f"Not an event cog: {name}")
        await ctx.send("Got cog")

        events = {
            "start": cog.event_start,
            "lock": cog.event_lock,
            "end": cog.event_end,
        }
        requested_event = events[event]
        await requested_event()
        await ctx.send("Called event")

    @commands.command(hidden=True)
    async def test_epic(self, ctx: Context):
        name = "EpicFreeGame"

        await ctx.send("Getting cog")
        cog = self.bot.get_cog(name)
        if not isinstance(cog, EpicFreeGame):
            raise TypeError(f"Not an event cog: {name}")
        await ctx.send("Got cog")

        await cog.send_reminder()
        await ctx.send("Called event")

    @commands.command(hidden=True)
    async def git_last(self, ctx: Context):
        stdout = subprocess.check_output(["git", "log", "--max-count=1"], text=True)
        await ctx.send(f"```{stdout}```")
