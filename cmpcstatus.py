#!/usr/bin/env python

import asyncio
import datetime
import json
import logging
import os
import random
import sys
import textwrap
from io import BytesIO
from pathlib import Path
from typing import Optional, Union
from urllib.parse import quote_plus
from zoneinfo import ZoneInfo

import aiohttp
import aiosqlite
import discord
from better_profanity import profanity
from discord import Embed, File, Member, Message, utils
from discord.ext import commands, tasks
from discord.ext.commands import Context
from PIL import Image, ImageDraw, ImageFont

from assets.words import common_words

# config
INTENTS = discord.Intents.default()
INTENTS.members = True
INTENTS.message_content = True
BIRTHDAY = False
CLOCK = True
FISHGAMINGWEDNESDAY = True
WELCOME = True
FISH_TEXT_CHANNEL = 875297517351358474
MOD_ROLE = 725356663850270821
MEMBER_ROLE = 932977796492427276
FISH_ROLE = 875359516131209256
GENERAL_CHANNEL = 714154159590473801
CLOCK_VOICE_CHANNEL = 753467367966638100
GREEN = discord.Color.green()
RED = discord.Color.red()
SAD_CAT_EMOJI = discord.PartialEmoji.from_str('<:sad_cat:770191103310823426>')
AMSTERDAM = ZoneInfo('Europe/Amsterdam')
# order is very important
# longest ones first
COMMAND_PREFIX = [
    'random ',  # space is needed
    'cmpc.',
    'c.',
    '$',
]

PathLike = Union[str, Path]


def config_object_hook(obj: dict, fp: PathLike = 'config.template.json') -> dict:
    with open(fp) as file:
        template: dict = json.load(file)
    if not isinstance(template, dict):
        raise TypeError(f'template: Expected dict, got {type(template)}')
    # make this more efficient when I move it to its own library
    for key in obj.keys():
        if key not in template:
            raise ValueError(f'Unexpected key: {key}')
    for key in template.keys():
        if key not in obj:
            raise ValueError(f'Missing key: {key}')
    return obj


def load_config(fp: PathLike = 'config.json') -> dict:
    with open(fp) as file:
        return json.load(file, object_hook=config_object_hook)


profanity_intercept = [':3']
# need to differ between slurs and normal profanity.
# encrypt database entries?
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
        super().__init__(*args, **kwargs)

    async def setup_hook(self):
        self.conn = await aiosqlite.connect('db.sqlite3')
        await self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS lb (
                time INTEGER NOT NULL,
                user INTEGER NOT NULL,
                word TEXT NOT NULL
            );
            """
        )
        await self.conn.commit()

        self.session = aiohttp.ClientSession()
        if CLOCK:
            self.clock.start()
        if FISHGAMINGWEDNESDAY:
            self.fish.start()

        print('done')  # this line is needed to work with ptero

    async def on_ready(self):
        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching, name='the cmpc discord'
            )
        )
        print(f'Connected to discord as: {self.user}')

    async def close(self):
        await super().close()
        for closeable in (self.conn, self.session):
            if closeable is not None:
                await closeable.close()
        for task in (self.clock, self.fish):
            if task.is_running():
                task.stop()

    async def process_profanity(self, message: Message):
        lower = message.content.casefold()
        mwords = lower.split()
        profanity_array = profanity_predict(mwords)

        swears = []
        for i, word in enumerate(mwords):
            if profanity_array[i] or word in profanity_intercept:
                swears.append(word)

        if not swears:
            return

        timestamp = message.created_at.timestamp()
        user = message.author.id
        await self.conn.executemany(
            'INSERT INTO lb (time, user, word) VALUES (?, ?, ?);',
            (
                (
                    timestamp,
                    user,
                    word,
                )
                for word in swears
            ),
        )
        await self.conn.commit()

    async def on_member_join(self, member):
        role = utils.get(member.guild.roles, id=MEMBER_ROLE)
        await member.add_roles(role)
        if self.config['welcome']:
            print(member.name + ' joined')
            strip_width, strip_height = 471, 155
            unwrapped = 'Welcome! ' + member.name
            text = '\n'.join(textwrap.wrap(unwrapped, width=19))
            background = Image.open('assets/bg.png').convert('RGBA')
            font = ImageFont.truetype('assets/Berlin Sans FB Demi Bold.ttf', 40)
            draw = ImageDraw.Draw(background)
            _left, _top, text_width, text_height = draw.textbbox(
                (0, 0), text, font=font
            )
            position = (
                (strip_width - text_width) / 2,
                (strip_height - text_height) / 2,
            )
            draw.text(
                position,
                text,
                color=(255, 255, 255),
                font=font,
                stroke_width=3,
                stroke_fill='black',
            )
            channel = self.get_channel(GENERAL_CHANNEL)
            savestring = 'cmpcwelcome' + str(random.randint(0, 100000)) + '.png'
            rgb_im = background.convert('RGB')
            rgb_im.save(savestring, 'PNG')
            embed = Embed(title=member.name + ' joined!', color=RED)
            file = File(savestring, filename=savestring)
            embed.set_image(url=('attachment://' + savestring))
            await channel.send('<@' + str(member.id) + '>')
            await channel.send(file=file, embed=embed)
            os.remove(savestring)

    async def on_member_remove(self, member):
        channel = self.get_channel(GENERAL_CHANNEL)
        await channel.send(
            f'{SAD_CAT_EMOJI}*** {member.name} ***left the eggyboi family {SAD_CAT_EMOJI}'
        )

    async def on_message(self, message: Message):
        await self.process_profanity(message)
        await self.process_commands(message)

    @tasks.loop(
        time=[datetime.time(minute=n, tzinfo=AMSTERDAM) for n in range(0, 60, 10)]
    )
    async def clock(self):
        datetime_amsterdam = datetime.datetime.now(AMSTERDAM)
        ams_time = datetime_amsterdam.strftime('cmpc: %H:%M')
        print(f'time for cmpc: {ams_time}')
        channel = self.get_channel(CLOCK_VOICE_CHANNEL)
        if channel is not None:
            await channel.edit(name=ams_time)

    @tasks.loop(time=datetime.time(hour=0))
    async def fgw_start(self):
        # only run on wednesday
        datetime_amsterdam = datetime.datetime.now(AMSTERDAM)
        if datetime_amsterdam.day != 3:
            return

        channel = self.get_channel(FISH_TEXT_CHANNEL)
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
        await channel.send(f'<@&{FISH_ROLE}>', file=File(r'fishgamingwednesday.mp4'))
        print('fish gaming wednesday started')

    @tasks.loop(time=datetime.time(hour=0))
    async def fgw_end(self):
        # only run on thursday (end of wednesday)
        datetime_amsterdam = datetime.datetime.now(AMSTERDAM)
        if datetime_amsterdam.day != 4:
            return
        channel = self.get_channel(FISH_TEXT_CHANNEL)

        # set channel to read-only
        perms = channel.overwrites_for(channel.guild.default_role)
        perms.update(
            send_messages=False,
            create_public_threads=False,
            create_private_threads=False,
            send_messages_in_threads=False,
        )
        await channel.set_permissions(
            channel.guild.default_role, overwrite=perms
        )

        def countdown_text(n: int) -> str:
            s = 's' if n != 1 else ''
            return f'In {n}n minute{s} this channel will be hidden.'

        # create countdown message
        embed = Embed(title='Fish gaming wednesday has ended.', color=0x69CCE7)
        embed.set_image(url=('attachment://' + 'fgwends.png'))
        file = File('fgwends.png', filename='assets/fgwends.png')
        embed.add_field(
            name=countdown_text(5),
            value='** **',
            inline=False,
        )
        message = await channel.send(embed=embed, file=file)

        # edit message until countdown ends
        for i in range(5, 0, -1):
            await asyncio.sleep(60)
            embed.fields[0].name = countdown_text(i)
            await message.edit(embed=embed)

        # leave a final message
        embed.remove_field(0)
        await message.edit(embed=embed)

    @tasks.loop(time=datetime.time(hour=0, minute=5))
    async def fgw_end_final(self):
        # only run on thursday (end of wednesday)
        datetime_amsterdam = datetime.datetime.now(AMSTERDAM)
        if datetime_amsterdam.day != 4:
            return
        channel = self.get_channel(FISH_TEXT_CHANNEL)

        # hide channel
        perms = channel.overwrites_for(channel.guild.default_role)
        perms.update(view_channel=False)
        await channel.set_permissions(
            channel.guild.default_role, overwrite=perms
        )


class CmpcDidThisHelp(commands.DefaultHelpCommand):
    async def send_bot_help(self, mapping, /):
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


def command_prefix(bot_: CmpcDidThis, message: discord.Message) -> list[str]:
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


@bot.hybrid_command(name='word')
async def random_word(ctx: Context):
    return await ctx.send(random.choice(common_words))


@bot.hybrid_command()
@commands.is_owner()
async def say(ctx: Context, *, text: str):
    return await ctx.send(text)


@bot.hybrid_command()
async def testconn(ctx: Context):
    return await ctx.send('hi there dude!')


@bot.hybrid_command(name='game')
async def random_game(ctx: Context):
    async with ctx.bot.session.get(
        'https://store.steampowered.com/explore/random/'
    ) as response:
        shorten = str(response.url).removesuffix('?snr=1_239_random_')
    await ctx.send(shorten)


@bot.hybrid_command(name='number')
async def random_number(
    ctx: Context, startnumber: Optional[int], endnumber: Optional[int]
):
    randomnumber = random.randint(startnumber, endnumber)
    await ctx.send(f'{randomnumber}')


@bot.hybrid_command(name='capybara', aliases=('capy',))
async def capybara(ctx: Context):
    async with ctx.bot.session.get('https://api.capy.lol/v1/capybara') as response:
        img_bytes = BytesIO(await response.content.read())
    embed = Embed(title='capybara for u!', color=RED)
    filename = 'capybara.png'
    file = File(img_bytes, filename=filename)
    embed.set_image(url=('attachment://' + filename))
    await ctx.send(file=file, embed=embed)


@bot.hybrid_command(name='gif', aliases=('g',))
async def random_gif(ctx: Context, *, search: Optional[str]):
    if search is None:
        search = random.choice(common_words)
    search = quote_plus(search.encode(encoding='utf-8'))

    # https://developers.google.com/tenor/guides/endpoints
    # I love the new Google State!
    search_random = (
        'https://tenor.googleapis.com/v2/search?key={}&q={}&random=true&limit=1'.format(
            ctx.bot.config['tenor_token'], search
        )
    )
    async with ctx.bot.session.get(search_random) as request:
        request.raise_for_status()
        random_json = await request.json()
    results = random_json['results']
    gif = results[0]
    url = gif['url']

    await ctx.send(url)


# lock bicking lawyer
@bot.hybrid_command(aliases=('lbl',))
async def leaderblame(ctx: commands.Context, word: str):
    query = 'SELECT user, COUNT(*) AS num FROM lb WHERE word = ? GROUP BY user ORDER BY num DESC LIMIT 10;'
    arg = (word,)
    thumb = None
    title = word
    async with ctx.bot.conn.execute_fetchall(query, arg) as rows:
        total = sum(r[1] for r in rows)

    content = '\n'.join(
        f'{utils.get(ctx.guild.members, id=r[0]).mention} ({r[1]})' for r in rows
    )
    embed = Embed(title=title, description=content)
    embed.set_footer(text=f'Total {total}', icon_url=thumb)

    await ctx.send(embed=embed)


@bot.hybrid_command(aliases=('lb',))
async def leaderboard(ctx: commands.Context, person: Optional[Member]):
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


@bot.hybrid_command(hidden=True)
@commands.has_role(MOD_ROLE)
async def shutdown(ctx: commands.Context, restart: bool = True):
    # works with pterodactyl
    print('Received shutdown order')
    if restart:
        message = 'Restarting'
        exit_code = 7
    else:
        if not await ctx.bot.is_owner(ctx.author):
            print('No')
            return
        message = 'Shutting down'
        exit_code = 0
    await ctx.send(message)
    sys.exit(exit_code)


def main():
    print('Connecting to discord...')
    bot.run(bot.config['discord_token'], log_level=logging.WARNING)


if __name__ == '__main__':
    main()
