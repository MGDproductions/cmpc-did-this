#!/usr/bin/env python

import asyncio
import datetime
import json
import logging
import random
import sys
import urllib.parse
from io import BytesIO
from typing import Optional
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

CLOCK = True
FISHGAMINGWEDNESDAY = True
WELCOME = True

FISH_TEXT_CHANNEL = 875297517351358474
MOD_ROLE = 725356663850270821
MEMBER_ROLE = 932977796492427276
FISH_ROLE = 875359516131209256
GENERAL_CHANNEL = 714154159590473801
CLOCK_VOICE_CHANNEL = 753467367966638100
EGGYBOI_GUILD = 714154158969716780

GREEN = discord.Color.green()
RED = discord.Color.red()
BLUE = discord.Color.blue()

SAD_CAT_EMOJI = discord.PartialEmoji.from_str('<:sad_cat:770191103310823426>')
AMSTERDAM = ZoneInfo('Europe/Amsterdam')
WEDNESDAY = 3
COMMAND_PREFIX = [
    'random ',  # space is needed
    'cmpc.',
    'c.',
    '$',
]


# CONFIG
def config_object_hook(obj: dict, fp: str = 'config.template.json') -> dict:
    with open(fp) as file:
        template: dict = json.load(file)
    if not isinstance(template, dict):
        raise TypeError(f'template: Expected dict, got {type(template)}')
    # make this more efficient when I move it to its own library
    # also add namedtuple or class?
    for key in obj.keys():
        if key not in template:
            raise ValueError(f'Unexpected key: {key}')
    for key in template.keys():
        if key not in obj:
            raise ValueError(f'Missing key: {key}')
    return obj


def load_config(fp: str = 'config.json') -> dict:
    with open(fp) as file:
        return json.load(file, object_hook=config_object_hook)


profanity_intercept = [':3']
profanity.load_censor_words()
profanity.add_censor_words(profanity_intercept)


def profanity_predict(pwords: list[str]) -> list[bool]:
    profanity_array = [profanity.contains_profanity(x) for x in pwords]
    return profanity_array


class CmpcDidThis(commands.Bot):
    def __init__(self, *args, **kwargs):
        self.config = load_config()
        self.conn: Optional[aiosqlite.Connection] = None
        self.session: Optional[aiohttp.ClientSession] = None
        self.tasks: list[tasks.Loop] = []
        if CLOCK:
            self.tasks.append(self.clock)
        if FISHGAMINGWEDNESDAY:
            self.tasks.extend(
                (
                    self.fgw_start,
                    self.fgw_end,
                    self.fgw_end_final,
                )
            )
        super().__init__(*args, **kwargs)

    # SETUP
    async def setup_hook(self):
        self.session = aiohttp.ClientSession()

        self.conn = await aiosqlite.connect('db.sqlite3')
        await self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS lb (
                id INTEGER NOT NULL PRIMARY KEY,
                stamp REAL NOT NULL,
                user INTEGER NOT NULL,
                word TEXT NOT NULL
            );
            """
        )
        await self.conn.commit()

        print('done')  # this line is needed to work with ptero

    async def on_ready(self):
        # start task loops
        for t in self.tasks:
            if not t.is_running():
                t.start()
        # upload slash commands
        server = self.get_guild(EGGYBOI_GUILD)
        self.tree.copy_global_to(guild=server)
        await self.tree.sync(guild=server)
        # set activity
        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching, name='the cmpc discord'
            )
        )
        print(f'Connected to discord as: {self.user}')

    async def close(self):
        print('Closing bot instance')
        await super().close()
        await self.conn.close()
        await self.session.close()
        for t in self.tasks:
            t.stop()
        print('Closed gracefully')

    # EVENTS
    async def process_profanity(self, message: Message) -> int:
        lower = message.content.casefold()
        mwords = lower.split()
        profanity_array = profanity_predict(mwords)

        swears = []
        for i, word in enumerate(mwords):
            if profanity_array[i] or word in profanity_intercept:
                swears.append(word)
        if not swears:
            return 0

        timestamp = message.created_at.timestamp()
        await self.conn.executemany(
            'INSERT INTO lb (id, stamp, user, word) VALUES (?, ?, ?, ?);',
            (
                (
                    message.id,
                    timestamp,
                    message.author.id,
                    word,
                )
                for word in swears
            ),
        )
        await self.conn.commit()

        return len(swears)

    async def on_member_join(self, member: Member):
        role = utils.get(member.guild.roles, id=MEMBER_ROLE)
        await member.add_roles(role)

        if not WELCOME:
            return
        name = member.name
        welcome_message = f'{name} joined'
        print(welcome_message)

        channel = self.get_channel(GENERAL_CHANNEL)
        async with channel.typing():
            # create image
            newline = '\n' if len(name) > 10 else ' '
            text = f'Welcome!{newline}{name}'
            image = Image.open('assets/bg.png', formats=['PNG'])
            draw = ImageDraw.Draw(image)
            draw.font = ImageFont.truetype('assets/Berlin Sans FB Demi Bold.ttf', 40)
            _, _, width, height = draw.textbbox((0, 0), text)
            position = (
                (image.width - width) / 2,
                (image.height - height) / 2,
            )
            draw.text(
                position,
                text,
                fill='white',
                stroke_width=3,
                stroke_fill='black',
            )

            # send image
            filename = 'cmpcwelcome.png'
            fp = BytesIO()
            image.save(fp, 'PNG')
            fp.seek(0)
            file = discord.File(fp, filename=filename)
            embed = Embed(title=welcome_message, color=RED)
            embed.set_image(url=f'attachment://{filename}')
            await channel.send(content=member.mention, file=file, embed=embed)

    async def on_member_remove(self, member):
        channel = self.get_channel(GENERAL_CHANNEL)
        await channel.send(
            f'{SAD_CAT_EMOJI} *** {member.name} *** left the eggyboi family {SAD_CAT_EMOJI}'
        )

    async def on_message(self, message: Message):
        await self.process_profanity(message)
        await self.process_commands(message)

    # TASKS
    @tasks.loop(
        time=[
            datetime.time(hour=h, minute=m, tzinfo=AMSTERDAM)
            for m in range(0, 60, 10)
            for h in range(24)
        ]
    )
    async def clock(self):
        datetime_amsterdam = datetime.datetime.now(AMSTERDAM)
        ams_time = datetime_amsterdam.strftime('cmpc: %H:%M')
        print(f'time for cmpc: {ams_time}')
        channel = self.get_channel(CLOCK_VOICE_CHANNEL)
        await channel.edit(name=ams_time)

    def wednesday_channel(self, *, day: int) -> Optional[discord.TextChannel]:
        datetime_amsterdam = datetime.datetime.now(AMSTERDAM)
        if datetime_amsterdam.isoweekday() != day:
            return None
        else:
            return self.get_channel(FISH_TEXT_CHANNEL)

    @tasks.loop(time=datetime.time(hour=0, tzinfo=AMSTERDAM))
    async def fgw_start(self):
        # only run on wednesday
        channel = self.wednesday_channel(day=WEDNESDAY)
        if channel is None:
            return

        perms = channel.overwrites_for(channel.guild.default_role)
        perms.update(
            view_channel=True,
            send_messages=True,
            create_public_threads=True,
            create_private_threads=True,
            send_messages_in_threads=True,
        )
        await channel.set_permissions(
            channel.guild.default_role, overwrite=perms, reason='fgw_start'
        )
        await channel.send(
            f'<@&{FISH_ROLE}>', file=discord.File('assets/fishgamingwednesday.mp4')
        )
        print('fish gaming wednesday started')

    @tasks.loop(time=datetime.time(hour=0, tzinfo=AMSTERDAM))
    async def fgw_end(self):
        print('here')
        # only run on thursday (end of wednesday)
        channel = self.wednesday_channel(day=WEDNESDAY + 1)
        if channel is None:
            return

        # set channel to read-only
        perms = channel.overwrites_for(channel.guild.default_role)
        perms.update(
            send_messages=False,
            create_public_threads=False,
            create_private_threads=False,
            send_messages_in_threads=False,
        )
        await channel.set_permissions(
            channel.guild.default_role, overwrite=perms, reason='fgw_end'
        )

        # create countdown message
        embed = Embed(title='Fish gaming wednesday has ended.', color=BLUE)
        filename = 'fgwends.png'
        embed.set_image(url=f'attachment://{filename}')
        file = discord.File(f'assets/{filename}', filename=f'{filename}')
        message = await channel.send(embed=embed, file=file)

        # edit message until countdown ends
        embed.add_field(name='', value='')
        for i in range(5, 0, -1):
            s = 's' if i != 1 else ''
            name = f'In {i} minute{s} this channel will be hidden.'
            embed.set_field_at(0, name=name, value='** **', inline=False)
            await message.edit(embed=embed)
            await asyncio.sleep(60)

        # leave a final message
        embed.remove_field(0)
        await message.edit(embed=embed)

    @tasks.loop(time=datetime.time(hour=0, minute=5, tzinfo=AMSTERDAM))
    async def fgw_end_final(self):
        # only run on thursday (end of wednesday)
        channel = self.wednesday_channel(day=WEDNESDAY + 1)
        if channel is None:
            return

        # hide channel
        perms = channel.overwrites_for(channel.guild.default_role)
        perms.update(view_channel=False)
        await channel.set_permissions(
            channel.guild.default_role, overwrite=perms, reason='fgw_end_final'
        )


# BOT SETUP
class CmpcDidThisHelp(commands.DefaultHelpCommand):
    async def send_bot_help(self, mapping: dict, /):
        ctx = self.context
        embed = Embed(title='cmpc did this commands', color=GREEN)
        pairs = (
            ('random word', 'gives you a random word'),
            ('random game', 'gives you a random game'),
            ('random gif', 'gives you a random gif'),
            ('random capybara', 'gives you a random capybara'),
            (
                'random gif {search term}',
                'gives you a random gif that matches your search term example: random gif cat',
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
    command_prefix=command_prefix, intents=INTENTS, help_command=CmpcDidThisHelp()
)


@bot.hybrid_command(hidden=True)
@commands.has_role(MOD_ROLE)
async def backfill_database(ctx: Context, channel: discord.TextChannel):
    await ctx.send('Loading history')
    count = 0
    swears = 0
    ignored = 0
    async for message in channel.history():
        count += 1
        try:
            swears += await ctx.bot.process_profanity(message)
        except aiosqlite.IntegrityError:
            ignored += 1
    await ctx.send(f'Messages {count} ignored {ignored} swears {swears}')


# COMMANDS
# lock bicking lawyer
@bot.hybrid_command(aliases=('lbl',))
async def leaderblame(ctx: Context, word: str):
    """whodunnit?"""
    query = 'SELECT user, COUNT(*) AS num FROM lb WHERE word = ? GROUP BY user ORDER BY num DESC LIMIT 10;'
    arg = (word,)
    thumb = None
    title = word
    async with ctx.bot.conn.execute_fetchall(query, arg) as rows:
        total = sum(r[1] for r in rows)

    content_list = []
    for r in rows:
        user = ctx.bot.get_user(r[0])
        mention = '<@0>' if user is None else user.mention
        content_list.append(mention)
    content = '\n'.join(content_list)
    embed = Embed(title=title, description=content)
    embed.set_footer(text=f'Total {total}', icon_url=thumb)

    await ctx.send(embed=embed)


@bot.hybrid_command(aliases=('lb',))
async def leaderboard(ctx: Context, person: Optional[Member]):
    # idk how this works but it sure does
    # or, in sql language:
    # IDK HOW this, WORKS BUT (it) SURE DOES
    if person is not None:
        query = 'SELECT word, COUNT(*) AS num FROM lb WHERE user = ? GROUP BY word ORDER BY num DESC LIMIT 10;'
        arg = (person.id,)
        thumb = person.avatar.url
        title = person.name
    else:
        query = 'SELECT word, COUNT(*) AS num FROM lb GROUP BY word ORDER BY num DESC LIMIT 10;'
        arg = ()
        thumb = ctx.guild.icon.url
        title = ctx.guild.name

    async with ctx.bot.conn.execute_fetchall(query, arg) as rows:
        total = sum(r[1] for r in rows)
        content = '\n'.join(f'{r[0]} ({r[1]})' for r in rows)
    embed = Embed(title=title, description=content)
    embed.set_footer(text=f'Total {total}', icon_url=thumb)

    await ctx.send(embed=embed)


@bot.hybrid_command(name='capybara', aliases=('capy',))
async def random_capybara(ctx: Context):
    """gives you a random capybara"""
    async with ctx.typing():
        async with ctx.bot.session.get('https://api.capy.lol/v1/capybara') as response:
            fp = BytesIO(await response.content.read())
        embed = Embed(title='capybara for u!', color=RED)
        filename = 'capybara.png'
        file = discord.File(fp, filename=filename)
        embed.set_image(url=f'attachment://{filename}')
    await ctx.send(embed=embed, file=file)


@bot.hybrid_command(name='game')
async def random_game(ctx: Context):
    """gives you a random game"""
    async with ctx.bot.session.get(
        'https://store.steampowered.com/explore/random/'
    ) as response:
        shorten = str(response.url).removesuffix('?snr=1_239_random_')
    await ctx.send(shorten)


@bot.hybrid_command(name='gif', aliases=('g',))
async def random_gif(ctx: Context, *, search: Optional[str]):
    """gives you a random gif"""
    async with ctx.typing():
        if search is None:
            search = random.choice(common_words)
        search = urllib.parse.quote_plus(search.encode(encoding='utf-8'))

        # https://developers.google.com/tenor/guides/endpoints
        # I love the new Google State!
        search_url = (
            'https://tenor.googleapis.com/v2/search?key={}&q={}&random=true&limit=1'
        )
        search_random = search_url.format(ctx.bot.config['tenor_token'], search)
        async with ctx.bot.session.get(search_random) as request:
            request.raise_for_status()
            random_json = await request.json()
        results = random_json['results']
        gif = results[0]
        url = gif['url']

    await ctx.send(url)


@bot.hybrid_command(name='number')
async def random_number(
    ctx: Context, startnumber: Optional[int], endnumber: Optional[int]
):
    """gives you a random number"""
    randomnumber = random.randint(startnumber, endnumber)
    await ctx.send(f'{randomnumber}')


@bot.hybrid_command(name='word')
async def random_word(ctx: Context):
    """gives you a random word"""
    return await ctx.send(random.choice(common_words))


@bot.hybrid_command(hidden=True)
@commands.is_owner()
async def say(ctx: Context, *, text: str):
    return await ctx.send(text)


@bot.hybrid_command(hidden=True)
async def testconn(ctx: Context):
    return await ctx.send('hi there dude!')


@bot.hybrid_command(hidden=True)
# @commands.has_role(MOD_ROLE)
@commands.is_owner()
async def shutdown(ctx: Context):
    # works with pterodactyl?
    print('Received shutdown order')
    await ctx.send('Shutting down')
    sys.exit()


def main():
    print('Connecting to discord...')
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter(logging.BASIC_FORMAT)
    bot.run(bot.config['discord_token'], log_handler=handler, log_formatter=formatter)


if __name__ == '__main__':
    main()
