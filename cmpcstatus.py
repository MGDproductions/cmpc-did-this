#!/usr/bin/env python

import asyncio
import datetime
import logging
import platform
import random
import subprocess
import sys
import tomllib
import urllib.parse
from io import BytesIO
from tempfile import TemporaryFile
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

ENABLE_BIRTHDAY = True
ENABLE_CLOCK = True
ENABLE_FISH = True
ENABLE_PROFANITY = True
ENABLE_READY_MESSAGE = True
ENABLE_WELCOME = True

PATH_CONFIG = "config.toml"
PATH_DATABASE = "db.sqlite3"

GUILD_EGGYBOI = 714154158969716780
ROLE_DEVELOPER = 741317598452645949
ROLE_FISH = 875359516131209256
ROLE_MEMBER = 932977796492427276
ROLE_MODS = 725356663850270821

TEXT_CHANNEL_BIRTHDAY = 982687737503182858
TEXT_CHANNEL_FISH = 875297517351358474
TEXT_CHANNEL_GENERAL = 714154159590473801
TEXT_CHANNEL_BOT_COMMANDS = 736664393630220289
VOICE_CHANNEL_CLOCK = 753467367966638100

CHANNEL_PERMISSIONS_OPEN = {"view_channel": True, "send_messages": True}
CHANNEL_PERMISSIONS_LOCKED = {"view_channel": True, "send_messages": False}
CHANNEL_PERMISSIONS_HIDDEN = {"view_channel": False, "send_messages": False}

COLOUR_GREEN = discord.Color.green()
COLOUR_RED = discord.Color.red()
COLOUR_BLUE = discord.Color.blue()

EMOJI_BIBI_PARTY = discord.PartialEmoji.from_str("<:bibi_party:857659475687374898>")
EMOJI_SAT_CAT = discord.PartialEmoji.from_str("<:sad_cat:770191103310823426>")
EMOJI_SKULL = discord.PartialEmoji.from_str("💀")

MENTION_NONE = discord.AllowedMentions.none()

TZ_AMSTERDAM = ZoneInfo("Europe/Amsterdam")
TZ_LONDON = ZoneInfo("Europe/London")
ISO_WEEKDAY_WEDNESDAY = 3
ISO_WEEKDAY_THURSDAY = 4
CLOCK_TIMES = [
    datetime.time(hour=h, minute=m, tzinfo=TZ_AMSTERDAM)
    for m in range(0, 60, 10)
    for h in range(24)
]
TIME_MIDNIGHT = datetime.time(hour=0, tzinfo=TZ_AMSTERDAM)
TIME_FGW_START = TIME_MIDNIGHT
TIME_FGW_LOCK = TIME_MIDNIGHT
TIME_FGW_END = datetime.time(hour=0, minute=5, tzinfo=TZ_AMSTERDAM)
TIME_BIRTHDAY_START = TIME_MIDNIGHT
TIME_BIRTHDAY_END = TIME_MIDNIGHT
DATE_BIRTHDAY_MONTH = 6
DATE_BIRTHDAY_DAY = 5
# how many seconds in a minute
COUNTDOWN_MINUTE = 60

PROFANITY_INTERCEPT = (":3",)
PROFANITY_ROWS_DEFAULT = 5
PROFANITY_ROWS_MAX = 100
PROFANITY_ROWS_INLINE = False

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
            F" Drop them in this chat before he wakes up!{EMOJI_BIBI_PARTY}{EMOJI_BIBI_PARTY}{EMOJI_BIBI_PARTY}",
            file=file,
        )


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


def command_prefix(bot_: CmpcDidThis, message: Message) -> list[str]:
    prefix_lengths = {p: len(p) for p in COMMAND_PREFIX}
    longest = max(prefix_lengths.values())
    message_start = message.content[:longest]
    possible = message_start.casefold()
    for prefix, length in prefix_lengths.items():
        if possible.startswith(prefix):
            return [message_start[:length]]
    return commands.when_mentioned(bot_, message)


# wraps the library to make it easier to swap out
# if I want to switch to the ml one
def profanity_predict(words: list[str]) -> list[bool]:
    profanity_array = [
        (w in PROFANITY_INTERCEPT or profanity.contains_profanity(w)) for w in words
    ]
    return profanity_array


class ProfanityLeaderboard(BotCog):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.conn: Optional[aiosqlite.Connection] = None
        self.profanity_intercept = PROFANITY_INTERCEPT
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

    @commands.Cog.listener(name="on_message")
    async def process_profanity(self, message: Message) -> int:
        """Return the number of swears added to the database."""
        lower = message.content.casefold()
        mwords = lower.split()
        profanity_array = profanity_predict(mwords)
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

    class ProfanityConverter(commands.Converter[str]):
        async def convert(self, ctx: Context, argument: str) -> str:
            word = argument.casefold()
            check = profanity_predict([word])[0]
            if not check:
                raise commands.BadArgument("Not a swear! L boomer.")
            return word

    async def get_total(
        self, author_id: int = None, word: ProfanityConverter = None
    ) -> int:
        # ¿Quieres?
        if author_id is not None:
            query = "SELECT COUNT(*) FROM lb WHERE author_id=:author_id"
        elif word is not None:
            query = "SELECT COUNT(*) FROM lb WHERE word=:word"
        else:
            query = "SELECT COUNT(*) FROM lb"

        arg = {"author_id": author_id, "word": word}
        async with self.conn.execute_fetchall(query, arg) as rows:
            total = rows[0][0]
        return total

    @staticmethod
    def limit_rows(rows: Optional[int]) -> tuple[int, bool]:
        if rows is None:
            rows = PROFANITY_ROWS_DEFAULT
            inline = PROFANITY_ROWS_INLINE
        else:
            rows = min(rows, PROFANITY_ROWS_MAX)
            inline = not PROFANITY_ROWS_INLINE
        return rows, inline

    @commands.hybrid_command(aliases=("leaderboard", "lb"))
    async def leaderboard_person(
        self, ctx: Context, person: Optional[Member], rows: Optional[int]
    ):
        embed = discord.Embed()
        rows, inline = self.limit_rows(rows)
        arg = {"rows": rows}

        if person is not None:
            where = "WHERE author_id=:author_id"
            arg["author_id"] = person.id
            embed.set_author(name=person.name, icon_url=person.display_avatar.url)
            total = await self.get_total(author_id=person.id, word=None)
        else:
            where = ""
            guild = ctx.guild
            icon_url = guild.icon.url if guild.icon is not None else None
            embed.set_author(name=guild.name, icon_url=icon_url)
            total = await self.get_total()

        embed.set_footer(text=f"Total: {total}")
        query = f"""
                SELECT word, COUNT(*) AS num FROM lb
                {where}
                GROUP BY word ORDER BY num DESC
                LIMIT :rows;
                """
        async with self.conn.execute_fetchall(query, arg) as rows:
            for word, count in rows:
                embed.add_field(name=count, value=word, inline=inline)

        await ctx.send(embed=embed, allowed_mentions=MENTION_NONE)

    # lock bicking lawyer
    @commands.hybrid_command(aliases=("leaderblame", "lbl"))
    async def leaderboard_word(
        self,
        ctx: Context,
        word: Optional[ProfanityConverter],
        rows: Optional[int],
    ):
        """whodunnit?"""
        embed = discord.Embed()
        guild = ctx.guild
        icon_url = guild.icon.url if guild.icon is not None else None
        rows, inline = self.limit_rows(rows)
        arg = {"rows": rows}

        if word is not None:
            where = "WHERE word=:word"
            arg["word"] = word
            embed.set_author(name=word, icon_url=icon_url)
            total = await self.get_total(author_id=None, word=word)
        else:
            where = ""
            embed.set_author(name=guild.name, icon_url=icon_url)
            total = await self.get_total()

        embed.set_footer(text=f"Total: {total}")
        query = f"""
                SELECT author_id, COUNT(*) AS num FROM lb
                {where}
                GROUP BY author_id ORDER BY num DESC
                LIMIT :rows
                """
        async with self.conn.execute_fetchall(query, arg) as rows:
            for author_id, count in rows:
                member = utils.get(guild.members, id=author_id)
                mention = f"<@{author_id}>" if member is None else member.mention
                embed.add_field(name=count, value=mention, inline=inline)
        await ctx.send(embed=embed, allowed_mentions=MENTION_NONE)

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
            status_message = await ctx.send(f"Loading history {c.mention}")
            count = 0
            swears = 0
            ignored = 0

            async def update_status():
                await status_message.edit(
                    content=f"Messages {count}, ignored {ignored}, swears {swears} in {c.mention}"
                )

            async for message in c.history(limit=limit, around=around):
                count += 1
                try:
                    swears += await self.process_profanity(message)
                except aiosqlite.IntegrityError:
                    ignored += 1
                if count % 1000 == 0:
                    await update_status()
            await update_status()
            await ctx.send(f"Loaded history {c.mention}")

    @commands.command(hidden=True)
    @commands.has_role(ROLE_DEVELOPER)
    async def trim_database(self, ctx: Context):
        """Remove entries with deleted users."""
        await ctx.send("Trimming")
        async with self.conn.execute_fetchall(
            "SELECT DISTINCT author_id FROM lb"
        ) as rows:
            author_ids = frozenset(r[0] for r in rows)
        await ctx.send(f"Database {len(author_ids)}")

        member_ids = frozenset(m.id for m in ctx.guild.members)
        await ctx.send(f"Guild {len(member_ids)}")
        # set magic
        missing_author_ids = author_ids - (member_ids & author_ids)
        await ctx.send(f"Removing {len(missing_author_ids)}")

        await self.conn.executemany(
            "DELETE FROM lb WHERE author_id=:author_id",
            parameters=({"author_id": a} for a in missing_author_ids),
        )
        await self.conn.commit()
        await ctx.send("Done trimming")


# COMMANDS
class BasicCommands(BotCog):
    @commands.hybrid_command(name="capybara", aliases=("capy",))
    async def random_capybara(self, ctx: Context):
        """gives you a random capybara"""
        async with ctx.typing():
            async with ctx.bot.session.get(
                "https://api.capy.lol/v1/capybara"
            ) as response:
                fp = BytesIO(await response.content.read())
            embed = Embed(title="capybara for u!", color=COLOUR_RED)
            filename = "capybara.png"
            file = discord.File(fp, filename=filename)
            embed.set_image(url=f"attachment://{filename}")
        await ctx.send(embed=embed, file=file)

    @commands.hybrid_command(name="cat")
    async def random_cat(self, ctx: Context):
        """gives you a random cat"""
        async with ctx.typing():
            async with ctx.bot.session.get("https://cataas.com/cat") as response:
                fp = BytesIO(await response.content.read())
            embed = Embed(title="cat for u!", color=COLOUR_RED)
            filename = "cat.png"
            file = discord.File(fp, filename=filename)
            embed.set_image(url=f"attachment://{filename}")
        await ctx.send(embed=embed, file=file)

    @commands.hybrid_command(name="game")
    async def random_game(self, ctx: Context):
        """gives you a random game"""
        async with ctx.bot.session.get(
            "https://store.steampowered.com/explore/random/"
        ) as response:
            shorten = str(response.url).removesuffix("?snr=1_239_random_")
        await ctx.send(shorten)

    @commands.hybrid_command(name="gif", aliases=("g",))
    async def random_gif(self, ctx: Context, *, search: Optional[str]):
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
            search_random = search_url.format(self.bot.config.tenor_token, search)
            async with ctx.bot.session.get(search_random) as request:
                request.raise_for_status()
                random_json = await request.json()
            results = random_json["results"]
            gif = results[0]
            url = gif["url"]

        await ctx.send(url)

    @commands.hybrid_command(name="number")
    async def random_number(self, ctx: Context, startnumber: int, endnumber: int):
        """gives you a random number"""
        randomnumber = random.randint(startnumber, endnumber)
        await ctx.send(f"{randomnumber}")

    @commands.hybrid_command(name="word")
    async def random_word(self, ctx: Context):
        """gives you a random word"""
        return await ctx.send(random.choice(common_words))

    @commands.command(hidden=True)
    async def testconn(self, ctx: Context):
        return await ctx.send("hi there dude!")

    @commands.command(hidden=True)
    @commands.is_owner()
    async def say(self, ctx: Context, *, text: str):
        return await ctx.send(text)

    @commands.hybrid_command(aliases=("code", "git", "github"))
    async def source(self, ctx: Context, upload: bool = False):
        """Send the source code for this boy."""
        message = await ctx.send("https://github.com/MDproductions-dev/cmpc-did-this")

        if upload:
            async with ctx.typing():
                with TemporaryFile() as file:
                    subprocess.run(["git", "archive", "--format=zip", "HEAD"], stdout=file)
                    file.seek(0)
                    discord_file = discord.File(file, filename="source.zip")
                    await message.reply(file=discord_file)

    async def ping_url(self, url: str):
        async with self.bot.session.head(url) as r:
            r.raise_for_status()

    @commands.hybrid_command(aliases=("http", "httpcat"))
    async def http_cat(self, ctx: Context, status_code: int):
        url = f"https://http.cat/{status_code}.jpg"
        await self.ping_url(url)
        await ctx.send(url)

    @commands.hybrid_command(aliases=("httpdog",))
    async def http_dog(self, ctx: Context, status_code: int):
        url = f"https://httpstatusdogs.com/img/{status_code}.jpg"
        await self.ping_url(url)
        await ctx.send(url)

    # todo? command to invoke another command and delete the invoking message
    # @commands.command(hidden=True)
    # @commands.has_role(MOD_ROLE)
    # async def hide(ctx: Context, *, invocation):
    #     message = ctx.
    #     return await bot.process_commands()


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
    async def ptero(self, ctx: Context, signal: Literal["restart", "stop"] = "restart"):
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
    async def git_last(self, ctx: Context):
        stdout = subprocess.check_output(["git", "log", "--max-count=1"], text=True)
        await ctx.send(f"```{stdout}```")


def main():
    bot = CmpcDidThis(
        case_insensitive=True,
        command_prefix=command_prefix,
        intents=INTENTS,
        help_command=BotHelpCommand(),
    )
    log.info("Connecting to discord...")
    # remove fancy ass shell colour that looks dumb in dark theme
    bot_log_formatter = logging.Formatter(logging.BASIC_FORMAT)
    bot.run(bot.config.discord_token, log_formatter=bot_log_formatter)


if __name__ == "__main__":
    main()
