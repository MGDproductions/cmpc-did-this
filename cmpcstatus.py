#!/usr/bin/env python

import asyncio
import datetime
import json
import logging
import random
import sys
import urllib.parse
from io import BytesIO
from typing import Literal, Optional
from zoneinfo import ZoneInfo

import aiohttp
import aiosqlite
import discord
from better_profanity import profanity
from discord import Embed, Member, Message, utils
from discord.ext import commands, tasks
from discord.ext.commands import Context
from PIL import Image, ImageDraw, ImageFont

from assets.words import common_words

# CONSTANTS
INTENTS = discord.Intents.default()
INTENTS.members = True
INTENTS.message_content = True

ENABLE_CLOCK = True
ENABLE_FISH = True
ENABLE_WELCOME = True

PATH_CONFIG = "config.json"
PATH_DATABASE = "db.sqlite3"

GUILD_EGGYBOI = 714154158969716780
ROLE_DEVELOPER = 741317598452645949
ROLE_FISH = 875359516131209256
ROLE_MEMBER = 932977796492427276
ROLE_MODS = 725356663850270821
TEXT_CHANNEL_FISH = 875297517351358474
TEXT_CHANNEL_GENERAL = 714154159590473801
VOICE_CHANNEL_CLOCK = 753467367966638100

COLOUR_GREEN = discord.Color.green()
COLOUR_RED = discord.Color.red()
COLOUR_BLUE = discord.Color.blue()
EMOJI_SAT_CAT = discord.PartialEmoji.from_str("<:sad_cat:770191103310823426>")
EMOJI_SKULL = discord.PartialEmoji.from_str("💀")

TZ_AMSTERDAM = ZoneInfo("Europe/Amsterdam")
DAY_WEDNESDAY = 3
DAY_THURSDAY = 4
CLOCK_TIMES = [
    datetime.time(hour=h, minute=m, tzinfo=TZ_AMSTERDAM)
    for m in range(0, 60, 10)
    for h in range(24)
]
FGW_START_TIME = datetime.time(hour=0, tzinfo=TZ_AMSTERDAM)
FGW_END_TIME = datetime.time(hour=0, tzinfo=TZ_AMSTERDAM)
FGW_HIDE_TIME = datetime.time(hour=0, minute=5, tzinfo=TZ_AMSTERDAM)
# how many seconds in a minute
COUNTDOWN_MINUTE = 60

COMMAND_PREFIX = [
    "random ",  # space is needed
    "cmpc.",
    "c.",
    "$",
]


log = logging.getLogger(__name__)
log.addHandler(logging.StreamHandler(sys.stdout))
log.setLevel(logging.INFO)


# CONFIG
class BotConfig:
    discord_token: str
    tenor_token: str
    ptero_address: str
    ptero_server_id: str
    ptero_token: str


def load_config(fp: str = PATH_CONFIG) -> BotConfig:
    with open(fp) as file:
        obj = json.load(file)
    config = BotConfig()
    for k, v in obj.items():
        setattr(config, k, v)
    return config


async def tags(message: Message):
    t = message.content.casefold()
    for k, v in {
        "el muchacho": "https://youtu.be/GdtuG-j9Xog",
        "make that the cat wise": "https://cdn.discordapp.com/attachments/"
        "736664393630220289/1098942081248010300/image.png",
    }.items():
        if k == t:
            await message.channel.send(v)


class CmpcDidThis(commands.Bot):
    def __init__(self, *args, **kwargs):
        self.config = load_config()
        self.session: Optional[aiohttp.ClientSession] = None
        self.tasks: list[tasks.Loop] = []
        if ENABLE_CLOCK:
            self.tasks.append(self.clock)
        if ENABLE_FISH:
            self.tasks.extend(
                (
                    self.fgw_start,
                    self.fgw_end,
                    self.fgw_hide,
                )
            )
        super().__init__(*args, **kwargs)

    # SETUP
    async def setup_hook(self):
        # set up http session
        self.session = aiohttp.ClientSession()

        # add default cogs
        await self.add_cog(ProfanityLeaderboard())
        await self.add_cog(DeveloperCommands())

        print("done")  # this line is needed to work with ptero

    async def on_ready(self):
        # start task loops
        for t in self.tasks:
            if not t.is_running():
                t.start()
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

    async def close(self):
        log.info("Closing bot instance")
        await super().close()
        await self.session.close()
        for t in self.tasks:
            t.stop()
        log.info("Closed gracefully")

    # EVENTS
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
        await tags(message)

    # TASKS
    @tasks.loop(time=CLOCK_TIMES)
    async def clock(self):
        datetime_amsterdam = datetime.datetime.now(TZ_AMSTERDAM)
        ams_time = datetime_amsterdam.strftime("cmpc: %H:%M")
        log.debug(f"time for cmpc: %s", ams_time)
        channel = self.get_channel(VOICE_CHANNEL_CLOCK)
        await channel.edit(name=ams_time)

    def wednesday_channel(self, *, day: int) -> Optional[discord.TextChannel]:
        datetime_amsterdam = datetime.datetime.now(TZ_AMSTERDAM)
        log.info("day-of-week check %d : %s", day, datetime_amsterdam)
        if datetime_amsterdam.isoweekday() != day:
            log.info("Not doing fgw routine")
            return None
        else:
            log.info("Doing fgw routine")
            return self.get_channel(TEXT_CHANNEL_FISH)

    @tasks.loop(time=FGW_START_TIME)
    async def fgw_start(self):
        # only run on wednesday
        channel = self.wednesday_channel(day=DAY_WEDNESDAY)
        if channel is None:
            return

        log.info("fish gaming wednesday started")
        perms = channel.overwrites_for(channel.guild.default_role)
        perms.update(
            view_channel=True,
            send_messages=True,
        )
        await channel.set_permissions(
            channel.guild.default_role, overwrite=perms, reason="fgw_start"
        )
        await channel.send(
            f"<@&{ROLE_FISH}>", file=discord.File("assets/fishgamingwednesday.mp4")
        )

    @tasks.loop(time=FGW_END_TIME)
    async def fgw_end(self):
        # only run on thursday (end of wednesday)
        channel = self.wednesday_channel(day=DAY_THURSDAY)
        if channel is None:
            return

        log.info("fish gaming wednesday ending")

        # set channel to read-only
        perms = channel.overwrites_for(channel.guild.default_role)
        perms.update(
            send_messages=False,
        )
        await channel.set_permissions(
            channel.guild.default_role, overwrite=perms, reason="fgw_end"
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

    @tasks.loop(time=FGW_HIDE_TIME)
    async def fgw_hide(self):
        channel = self.wednesday_channel(day=DAY_THURSDAY)
        if channel is None:
            return

        log.info("fish gaming wednesday ended")

        # hide channel
        perms = channel.overwrites_for(channel.guild.default_role)
        perms.update(view_channel=False)
        await channel.set_permissions(
            channel.guild.default_role, overwrite=perms, reason="fgw_end_final"
        )


# BOT SETUP
class BotHelpCommand(commands.DefaultHelpCommand):
    async def send_bot_help(self, mapping: dict, /):
        ctx = self.context
        embed = Embed(title="cmpc did this commands", color=COLOUR_GREEN)
        pairs = (
            ("random word", "gives you a random word"),
            ("random game", "gives you a random game"),
            ("random gif", "gives you a random gif"),
            ("random capybara", "gives you a random capybara"),
            (
                "random gif {search term}",
                "gives you a random gif that matches your search term example: random gif cat",
            ),
        )
        for name, value in pairs:
            embed.add_field(name=name, value=value, inline=False)
        await ctx.send(embed=embed)


def command_prefix(bot_: CmpcDidThis, message: Message) -> list[str]:
    prefix_lengths = {p: len(p) for p in COMMAND_PREFIX}
    longest = max(prefix_lengths.values())
    message_start = message.content[:longest]
    possible = message_start.casefold()
    for prefix, length in prefix_lengths.items():
        if possible.startswith(prefix):
            return [message_start[:length]]
    return commands.when_mentioned(bot_, message)


bot = CmpcDidThis(
    case_insensitive=True,
    command_prefix=command_prefix,
    intents=INTENTS,
    help_command=BotHelpCommand(),
)


class ProfanityLeaderboard(commands.Cog):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.conn: Optional[aiosqlite.Connection] = None
        self.profanity_intercept = (":3",)
        profanity.load_censor_words()
        profanity.add_censor_words(self.profanity_intercept)

    async def cog_load(self):
        self.conn = await aiosqlite.connect(PATH_DATABASE)
        await self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS lb (
                message_id INTEGER NOT NULL,
                created_at REAL NOT NULL,
                author_id INTEGER NOT NULL,
                word TEXT NOT NULL,
                position INTEGER NOT NULL,
                PRIMARY KEY (message_id, position)
            );
            """
        )
        await self.conn.commit()

    async def cog_unload(self):
        await self.conn.close()

    @commands.Cog.listener()
    async def on_message(self, message: Message):
        await self.process_profanity(message)

    async def process_profanity(self, message: Message) -> int:
        lower = message.content.casefold()
        mwords = lower.split()
        profanity_array = self.profanity_predict(mwords)
        swears = {i: word for i, word in enumerate(mwords) if profanity_array[i]}
        if not swears:
            return 0

        timestamp = message.created_at.timestamp()
        await self.conn.executemany(
            """
            INSERT INTO lb (message_id, created_at, author_id, word, position)
            VALUES (:message_id, :created_at, :author_id, :word, :position);
            """,
            (
                {
                    "message_id": message.id,
                    "created_at": timestamp,
                    "author_id": message.author.id,
                    "word": word,
                    "position": position,
                }
                for position, word in swears.items()
            ),
        )
        await self.conn.commit()

        return len(swears)

    # wraps the library to make it easier to swap out
    # if I want to switch to the ml one
    def profanity_predict(self, words: list[str]) -> list[bool]:
        profanity_array = [
            (x in self.profanity_intercept or profanity.contains_profanity(x))
            for x in words
        ]
        return profanity_array

    class ProfanityConverter(commands.Converter[str]):
        def __init__(self, cog: "ProfanityLeaderboard"):
            self.cog = cog

        async def convert(self, ctx: Context, argument: str) -> str:
            word = argument.casefold()
            check = self.cog.profanity_predict([word])[0]
            if not check:
                raise commands.BadArgument("Not a swear! L boomer.")
            return word

    # lock bicking lawyer
    @commands.hybrid_command(aliases=("lbl",))
    async def leaderblame(self, ctx: Context, word: ProfanityConverter):
        """whodunnit?"""

        query = """
                SELECT author_id, COUNT(*) AS num FROM lb
                WHERE word=:word
                GROUP BY author_id ORDER BY num DESC
                LIMIT 10;
                """
        arg = {"word": word}
        thumb = None
        title = word
        async with ctx.bot.conn.execute_fetchall(query, arg) as rows:
            # todo: complete total, not just limit 10
            #       fix for main leaderboard command too
            total = sum(r[1] for r in rows)

        content_list = []
        for r in rows:
            user = ctx.bot.get_user(r[0])
            mention = "<@0>" if user is None else user.mention
            content_list.append(f"{mention} ({r[1]})")
        content = "\n".join(content_list)
        embed = Embed(title=title, description=content)
        embed.set_footer(text=f"Total {total}", icon_url=thumb)

        await ctx.send(embed=embed)

    @commands.hybrid_command(aliases=("lb",))
    async def leaderboard(self, ctx: Context, person: Optional[Member]):
        # idk how this works but it sure does
        # or, in sql language:
        # IDK HOW this, WORKS BUT (it) SURE DOES
        if person is not None:
            query = """
                    SELECT word, COUNT(*) AS num FROM lb
                    WHERE author_id=:author_id
                    GROUP BY word ORDER BY num DESC
                    LIMIT 10;
                    """
            arg = {"author_id": person.id}
            thumb = person.avatar.url
            title = person.name
        else:
            query = """
                    SELECT word, COUNT(*) AS num FROM lb
                    GROUP BY word ORDER BY num DESC
                    LIMIT 10;
                    """
            arg = ()
            thumb = ctx.guild.icon.url
            title = ctx.guild.name

        async with ctx.bot.conn.execute_fetchall(query, arg) as rows:
            total = sum(r[1] for r in rows)
            content = "\n".join(f"{r[0]} ({r[1]})" for r in rows)
        embed = Embed(title=title, description=content)
        embed.set_footer(text=f"Total {total}", icon_url=thumb)

        await ctx.send(embed=embed)

    @commands.command(hidden=True)
    @commands.has_role(ROLE_DEVELOPER)
    async def backfill_database(
        self,
        ctx: Context,
        limit: Optional[int],
        around: Optional[Message],
        *channels: discord.TextChannel,
    ):
        for c in channels:
            await ctx.send(f"Loading history {c.mention}")
            count = 0
            swears = 0
            ignored = 0
            async for message in c.history(limit=limit, around=around):
                count += 1
                try:
                    swears += await self.process_profanity(message)
                except aiosqlite.IntegrityError:
                    ignored += 1
            await ctx.send(
                f"Messages {count} ignored {ignored} swears {swears} in {c.mention}"
            )


# COMMANDS
@bot.hybrid_command(name="capybara", aliases=("capy",))
async def random_capybara(ctx: Context):
    """gives you a random capybara"""
    async with ctx.typing():
        async with ctx.bot.session.get("https://api.capy.lol/v1/capybara") as response:
            fp = BytesIO(await response.content.read())
        embed = Embed(title="capybara for u!", color=COLOUR_RED)
        filename = "capybara.png"
        file = discord.File(fp, filename=filename)
        embed.set_image(url=f"attachment://{filename}")
    await ctx.send(embed=embed, file=file)


@bot.hybrid_command(name="game")
async def random_game(ctx: Context):
    """gives you a random game"""
    async with ctx.bot.session.get(
        "https://store.steampowered.com/explore/random/"
    ) as response:
        shorten = str(response.url).removesuffix("?snr=1_239_random_")
    await ctx.send(shorten)


@bot.hybrid_command(name="gif", aliases=("g",))
async def random_gif(ctx: Context, *, search: Optional[str]):
    """gives you a random gif"""
    async with ctx.typing():
        if search is None:
            search = random.choice(common_words)
        search = urllib.parse.quote_plus(search.encode(encoding="utf-8"))

        # https://developers.google.com/tenor/guides/endpoints
        # I love the new Google State!
        search_url = (
            "https://tenor.googleapis.com/v2/search?key={}&q={}&random=true&limit=1"
        )
        search_random = search_url.format(bot.config.tenor_token, search)
        async with ctx.bot.session.get(search_random) as request:
            request.raise_for_status()
            random_json = await request.json()
        results = random_json["results"]
        gif = results[0]
        url = gif["url"]

    await ctx.send(url)


@bot.hybrid_command(name="number")
async def random_number(ctx: Context, startnumber: int, endnumber: int):
    """gives you a random number"""
    randomnumber = random.randint(startnumber, endnumber)
    await ctx.send(f"{randomnumber}")


@bot.hybrid_command(name="word")
async def random_word(ctx: Context):
    """gives you a random word"""
    return await ctx.send(random.choice(common_words))


@bot.command(hidden=True)
async def testconn(ctx: Context):
    return await ctx.send("hi there dude!")


# PRIVILEGED COMMANDS
@bot.command(hidden=True)
@commands.is_owner()
async def say(ctx: Context, *, text: str):
    return await ctx.send(text)


# @bot.command(hidden=True)
# @commands.has_role(MOD_ROLE)
# async def hide(ctx: Context, *, invocation):
#     message = ctx.
#     return await bot.process_commands()


class DeveloperCommands(commands.Cog):
    def cog_check(self, ctx: Context) -> bool:
        # see discord.commands.has_role
        if ctx.guild is None:
            raise commands.NoPrivateMessage
        role = discord.utils.get(ctx.author.roles, id=ROLE_DEVELOPER)
        if role is None:
            raise commands.MissingRole(ROLE_DEVELOPER)
        return True

    @commands.command(hidden=True)
    async def ptero(self, ctx: Context, signal: Literal["restart", "stop"] = "restart"):
        # https://github.com/iamkubi/pydactyl/blob/main/pydactyl/api/client/servers/base.py#L78
        message = f"Sending signal '{signal}'"
        log.info(message)
        await ctx.send(message)

        url = f"{bot.config.ptero_address}/client/servers/{bot.config.ptero_server_id}/power"
        payload = {"signal": signal}
        headers = {"Authorization": f"Bearer {bot.config.ptero_token}"}
        async with bot.session.post(url, json=payload, headers=headers) as response:
            response.raise_for_status()

    @commands.command(hidden=True)
    async def test_event(
        self,
        ctx: Context,
        member: Optional[Member],
        event: Literal["join", "remove"] = "join",
    ):
        log.info("Test event (%s) %s", member, event)
        events = {
            "join": bot.on_member_join,
            "remove": bot.on_member_remove,
        }
        member = member or ctx.author
        await events[event](member)


def main():
    log.info("Connecting to discord...")
    # remove fancy ass shell colour that looks dumb in dark theme
    bot_log_formatter = logging.Formatter(logging.BASIC_FORMAT)
    bot.run(bot.config.discord_token, log_formatter=bot_log_formatter)


if __name__ == "__main__":
    main()
