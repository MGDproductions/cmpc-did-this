import datetime
import platform
import tomllib
from io import BytesIO
from typing import Optional

import aiohttp
import discord
from PIL import Image, ImageDraw, ImageFont
from discord import Embed, Member, Message, utils
from discord.ext import commands, tasks
from discord.ext.commands import Context

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
    ENABLE_WELCOME,
    GUILD_EGGYBOI,
    PATH_CONFIG,
    ROLE_MEMBER,
    TEXT_CHANNEL_BOT_COMMANDS,
    TEXT_CHANNEL_GENERAL,
    TZ_AMSTERDAM,
    VOICE_CHANNEL_CLOCK,
)
from cmpcstatus import log
from cmpcstatus.cogs.commands import BasicCommands, DeveloperCommands
from cmpcstatus.cogs.profanity import ProfanityLeaderboard
from cmpcstatus.cogs.events import Birthday, FishGamingWednesday


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


class CmpcDidThis(commands.Bot):
    def __init__(self, *args, **kwargs):
        self.config = load_config()
        self.session: Optional[aiohttp.ClientSession] = None
        super().__init__(*args, **kwargs)

    # SETUP
    async def setup_hook(self):
        # set up http session
        self.session = aiohttp.ClientSession()

        # add default cogs
        await self.add_cog(BasicCommands(self))
        await self.add_cog(DeveloperCommands(self))
        if ENABLE_BIRTHDAY:
            await self.add_cog(Birthday(self))
        if ENABLE_FISH:
            await self.add_cog(FishGamingWednesday(self))
        if ENABLE_PROFANITY:
            await self.add_cog(ProfanityLeaderboard(self))

        print("done")  # this line is needed to work with ptero

    async def on_ready(self):
        # start task loops
        if ENABLE_CLOCK:
            if not self.clock.is_running():
                self.clock.start()
        # upload slash commands
        server = self.get_guild(GUILD_EGGYBOI)
        self.tree.copy_global_to(guild=server)
        await self.tree.sync(guild=server)
        # set activity
        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching, name="the cmpc discord"
            )
        )
        log.info(f"Connected to discord as: %s", self.user)

        if ENABLE_READY_MESSAGE:
            ready_channel = self.get_channel(TEXT_CHANNEL_BOT_COMMANDS)
            await ready_channel.send(f"Connected to discord from: `{platform.node()}`")

    async def close(self):
        log.info("Closing bot instance")
        await super().close()
        await self.session.close()
        if self.clock.is_running():
            self.clock.stop()
        log.info("Closed gracefully")

    # EVENTS
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
            image = Image.open("assets/bg.png", formats=["PNG"])
            draw = ImageDraw.Draw(image)
            draw.font = ImageFont.truetype("assets/Berlin Sans FB Demi Bold.ttf", 40)
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

    # TASKS
    @tasks.loop(time=CLOCK_TIMES)
    async def clock(self):
        datetime_amsterdam = datetime.datetime.now(TZ_AMSTERDAM)
        ams_time = datetime_amsterdam.strftime("cmpc: %H:%M")
        log.debug(f"time for cmpc: %s", ams_time)
        channel = self.get_channel(VOICE_CHANNEL_CLOCK)
        await channel.edit(name=ams_time)


class BotCog(commands.Cog):
    def __init__(self, bot: CmpcDidThis, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.bot = bot


def command_prefix(bot_: CmpcDidThis, message: Message) -> list[str]:
    prefix_lengths = {p: len(p) for p in COMMAND_PREFIX}
    longest = max(prefix_lengths.values())
    message_start = message.content[:longest]
    possible = message_start.casefold()
    for prefix, length in prefix_lengths.items():
        if possible.startswith(prefix):
            return [message_start[:length]]
    return commands.when_mentioned(bot_, message)


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
