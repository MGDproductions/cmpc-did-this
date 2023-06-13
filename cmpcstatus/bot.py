import datetime
import logging
import platform
import tomllib
from io import BytesIO
from typing import Optional

import aiohttp
import discord
from discord import Embed, Member, Message, utils
from discord.ext import commands, tasks
from discord.ext.commands import Context
from PIL import Image, ImageDraw, ImageFont

from cmpcstatus.cogs.commands import BasicCommands, DeveloperCommands
from cmpcstatus.cogs.events import FishGamingWednesday, MarcelGamingBirthday
from cmpcstatus.cogs.profanity import ProfanityLeaderboard
from cmpcstatus.constants import (
    CLOCK_TIMES,
    COLOUR_GREEN,
    COLOUR_RED,
    COMMAND_PREFIX,
    EMOJI_SAT_CAT,
    EMOJI_SKULL,
    ENABLE_BIRTHDAY,
    ENABLE_CLOCK,
    ENABLE_FISH,
    ENABLE_PROFANITY,
    ENABLE_READY_MESSAGE,
    ENABLE_SLASH_COMMANDS,
    ENABLE_WELCOME,
    FONT_SIZE_WELCOME,
    GUILD_EGGYBOI,
    PATH_CONFIG,
    ROLE_MEMBER,
    TESTING,
    TEXT_CHANNEL_BOT_COMMANDS,
    TEXT_CHANNEL_GENERAL,
    TZ_AMSTERDAM,
    VOICE_CHANNEL_CLOCK,
)
from cmpcstatus.util import get_asset

log = logging.getLogger(__name__)


class BotConfig:
    discord_token: str
    tenor_token: str
    ptero_address: str
    ptero_server_id: str
    ptero_token: str


def load_config(fp: str = PATH_CONFIG) -> BotConfig:
    with open(fp, "rb") as file:
        obj = tomllib.load(file)
    config = BotConfig()
    for k, v in obj.items():
        setattr(config, k, v)
    return config


class Bot(commands.Bot):
    def __init__(self, *args, **kwargs):
        self.config = load_config()
        self.session: Optional[aiohttp.ClientSession] = None
        super().__init__(*args, **kwargs)

    async def setup_hook(self):
        # set up http session
        self.session = aiohttp.ClientSession()

        # add default cogs
        self.add_cog(BasicCommands(self))
        self.add_cog(DeveloperCommands(self))
        if ENABLE_BIRTHDAY:
            self.add_cog(MarcelGamingBirthday(self))
        if ENABLE_FISH:
            self.add_cog(FishGamingWednesday(self))
        if ENABLE_PROFANITY:
            self.add_cog(ProfanityLeaderboard(self))

        print("done")  # this line is needed to work with ptero

    async def send_ready_message(self, message: str):
        if ENABLE_READY_MESSAGE:
            ready_channel = self.get_channel(TEXT_CHANNEL_BOT_COMMANDS)
            await ready_channel.send(message)

    async def on_ready(self):
        # start task loops
        if ENABLE_CLOCK:
            if not self.clock.is_running():
                self.clock.start()

        # upload slash commands
        if ENABLE_SLASH_COMMANDS:
            await self.register_application_commands()
            if TESTING:
                server = self.get_guild(GUILD_EGGYBOI)
                await self.register_application_commands(guild=server)

        # set activity
        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching, name="the cmpc discord"
            )
        )

        log.info(f"Connected to discord as: %s", self.user)
        await self.send_ready_message(f"Connected from `{platform.node()}`")

    async def close(self):
        log.info("Closing bot instance")
        await self.send_ready_message(f"Disconnecting from `{platform.node()}`")

        await self.session.close()
        if self.clock.is_running():
            self.clock.stop()
        await super().close()

        log.info("Closed gracefully")

    async def on_command_error(
        self, ctx: Context, exception: commands.errors.CommandError
    ):
        await super().on_command_error(ctx, exception)
        await ctx.send(str(exception))

    async def on_member_join(self, member: Member):
        role = utils.get(member.guild.roles, id=ROLE_MEMBER)
        await member.add_roles(role)

        if not ENABLE_WELCOME:
            return
        name = member.name
        log.info("%s joined", name)

        channel = self.get_channel(TEXT_CHANNEL_GENERAL)
        async with channel.typing():
            # create image
            newline = "\n" if len(name) > 10 else " "
            text = f"Welcome!{newline}{name}"

            with get_asset("bg.png") as path:
                image = Image.open(path, formats=["PNG"])
            with get_asset("Berlin Sans FB Demi Bold.ttf") as path:
                font = ImageFont.truetype(str(path), FONT_SIZE_WELCOME)

            draw = ImageDraw.Draw(image)
            draw.font = font
            _, _, width, height = draw.textbbox((0, 0), text)
            position = (
                (image.width - width) / 2,
                (image.height - height) / 2,
            )
            draw.text(
                position,
                text,
                fill="white",
                stroke_width=3,
                stroke_fill="black",
            )

            # send image
            filename = "cmpcwelcome.png"
            fp = BytesIO()
            image.save(fp, "PNG")
            fp.seek(0)
            file = discord.File(fp, filename=filename)
            embed = Embed(title=f"{name} joined", color=COLOUR_RED)
            embed.set_image(url=f"attachment://{filename}")
            await channel.send(content=member.mention, file=file, embed=embed)

    async def on_member_remove(self, member: Member):
        log.info("%s left", member.name)
        channel = self.get_channel(TEXT_CHANNEL_GENERAL)
        message = await channel.send(
            f"{EMOJI_SAT_CAT} *** {member.name} *** left the eggyboi family {EMOJI_SAT_CAT}"
        )
        await message.add_reaction(EMOJI_SKULL)

    async def on_message(self, message: Message):
        await super().on_message(message)

        t = message.content.casefold()
        for k, v in {
            "el muchacho": "https://youtu.be/GdtuG-j9Xog",
            "make that the cat wise": "https://cdn.discordapp.com/attachments/"
            "736664393630220289/1098942081248010300/image.png",
        }.items():
            if k == t:
                await message.channel.send(v)

    @tasks.loop(time=CLOCK_TIMES)
    async def clock(self):
        datetime_amsterdam = datetime.datetime.now(TZ_AMSTERDAM)
        ams_time = datetime_amsterdam.strftime("cmpc: %H:%M")
        log.debug(f"time for cmpc: %s", ams_time)
        channel = self.get_channel(VOICE_CHANNEL_CLOCK)
        await channel.edit(name=ams_time)


def command_prefix(bot: Bot, message: Message) -> list[str]:
    prefix_lengths = {p: len(p) for p in COMMAND_PREFIX}
    longest = max(prefix_lengths.values())
    message_start = message.content[:longest]
    possible = message_start.casefold()
    for prefix, length in prefix_lengths.items():
        if possible.startswith(prefix):
            return [message_start[:length]]
    return commands.when_mentioned(bot, message)


class BotHelpCommand(commands.DefaultHelpCommand):
    async def send_bot_help(self, mapping: dict, /):
        ctx = self.context
        embed = Embed(title="cmpc did this commands", color=COLOUR_GREEN)
        pairs = (
            ("random word", "gives you a random word"),
            ("random game", "gives you a random game"),
            ("random gif", "gives you a random gif"),
            ("random capybara", "gives you a random capybara"),
            ("random cat", "gives you a random cat"),
            (
                "random gif {search term}",
                "gives you a random gif that matches your search term example: random gif cat",
            ),
        )
        for name, value in pairs:
            embed.add_field(name=name, value=value, inline=False)
        await ctx.send(embed=embed)
