import asyncio
import datetime
import json
import os
import random
import sys
import textwrap
from io import BytesIO
from typing import Optional, Union
from pathlib import Path

import aiohttp
import aiosqlite
import discord
import pytz
from better_profanity import profanity
from discord import Embed, File, Member, Message, utils
from discord.ext import commands, tasks
from PIL import Image, ImageDraw, ImageFont

from words import common_words

PathLike = Union[str, Path]


def load_config(fp: PathLike = 'config.json') -> dict:
    with open(fp) as file:
        return json.load(file)


intents = discord.Intents.all()
intents.members = True
intents.messages = True
fishgaming = True
fishrestarting = True
birthday = False


def author_is_mod(interaction) -> bool:
    # mod role
    return utils.get(interaction.author.roles, id=725356663850270821) is not None


def profanity_predict(pwords: list[str]) -> list[bool]:
    profanity_array = [profanity.contains_profanity(x) for x in pwords]
    return profanity_array


profanity_intercept = [':3']
# need to differ between slurs and normal profanity.
# encrypt database entries?
profanity.load_censor_words()
profanity.add_censor_words(profanity_intercept)


class CmpcDidThis(commands.Bot):
    def __init__(self, *args, **kwargs):
        self.config = load_config()
        self.conn: Optional[aiosqlite.Connection] = None
        self.session: Optional[aiohttp.ClientSession] = None
        super().__init__(*args, **kwargs)

    async def on_ready(self):
        if self.conn is None:
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
        if self.session is None:
            self.session = aiohttp.ClientSession()
        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching, name='the cmpc discord'
            )
        )
        if self.config['clock'] and not self.clock.is_running():
            self.clock.start()
        if self.config['fishgamingwednesday'] and not self.fish.is_running():
            self.fish.start()

        print(f'Connected to discord as: {self.user}')
        print('done')  # this line is needed to work with ptero

    async def close(self):
        await super().close()
        await self.conn.close()
        await self.session.close()

    # lock bicking lawyer
    @commands.command(aliases=['lbl'])
    async def leaderblame(self, ctx: commands.Context, word: str):
        query = 'SELECT user, COUNT(*) AS num FROM lb WHERE word = ? GROUP BY user ORDER BY num DESC LIMIT 10;'
        arg = (word,)
        thumb = None
        title = word
        async with self.conn.execute_fetchall(query, arg) as rows:
            total = sum(r[1] for r in rows)

        content = '\n'.join(
            f'{utils.get(ctx.guild.members, id=r[0]).mention} ({r[1]})' for r in rows
        )
        embed = Embed(title=title, description=content)
        embed.set_footer(text=f'Total {total}', icon_url=thumb)

        await ctx.send(embed=embed)

    @commands.command(aliases=['lb'])
    async def leaderboard(self, ctx: commands.Context, person: Optional[Member]):
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

        async with self.conn.execute_fetchall(query, arg) as rows:
            total = sum(r[1] for r in rows)
            content = '\n'.join(f'{r[0]} ({r[1]})' for r in rows)
        embed = Embed(title=title, description=content)
        embed.set_footer(text=f'Total {total}', icon_url=thumb)

        await ctx.send(embed=embed)

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
        role = utils.get(member.guild.roles, id=932977796492427276)
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
            channel = self.get_channel(714154159590473801)
            savestring = 'cmpcwelcome' + str(random.randint(0, 100000)) + '.png'
            rgb_im = background.convert('RGB')
            rgb_im.save(savestring, 'PNG')
            embed = Embed(title=member.name + ' joined!', color=0xFF0000)
            file = File(savestring, filename=savestring)
            embed.set_image(url=('attachment://' + savestring))
            await channel.send('<@' + str(member.id) + '>')
            await channel.send(file=file, embed=embed)
            os.remove(savestring)

    async def on_member_remove(self, member):
        channel = self.get_channel(714154159590473801)
        sad_cat = '<:sad_cat:770191103310823426>'
        await channel.send(
            f'{sad_cat}*** {member.name} ***left the eggyboi family {sad_cat}'
        )

    async def on_message(self, message):
        await self.process_profanity(message)

        if message.author == self.user:
            return

        if message.content.startswith('random word'):
            word = random.choice(common_words)
            await message.channel.send(word)

        if message.content.startswith('cmpc.say'):
            if message.author.id == 416525692772286464:
                await message.channel.send(message.content[9:])

        if message.content.startswith('$testconn'):
            await message.channel.send('hi there dude!')

        if message.content.startswith('random game'):
            async with self.session as session:
                async with session.get(
                    'https://store.steampowered.com/explore/random/'
                ) as r:
                    shorten = str(r.url).replace('?snr=1_239_random_', '')
            await message.channel.send(shorten)

        if message.content.startswith('random number'):
            try:
                splitmessage = message.content.split()
                startnumber = splitmessage[2]
                endnumber = splitmessage[3]
                randomnumber = random.randint(int(startnumber), int(endnumber))
                await message.channel.send(str(randomnumber))
            except (IndexError, ValueError):
                await message.channel.send('There is an error in your command.')

        if message.content.startswith('cmpc.help'):
            embed = Embed(title='cmpc did this commands', color=0x00FF00)
            embed.add_field(
                name='random word', value='gives you a random word', inline=False
            )
            embed.add_field(
                name='random game', value='gives you a random game', inline=False
            )
            embed.add_field(
                name='random gif', value='gives you a random gif', inline=False
            )
            embed.add_field(
                name='random capybara',
                value='gives you a random capybara',
                inline=False,
            )
            embed.add_field(
                name='random gif {search term}',
                value='gives you a random gif that matches your search term example: random gif cat',
                inline=False,
            )
            await message.channel.send(embed=embed)

        if message.content.startswith('random capybara'):
            async with self.session as session:
                async with session.get('https://api.capy.lol/v1/capybara') as response:
                    img_bytes = BytesIO(await response.content.read())
            embed = Embed(title='capybara for u!', color=0xFF0000)
            filename = 'capybara.png'
            file = File(img_bytes, filename=filename)
            embed.set_image(url=('attachment://' + filename))
            await message.channel.send(file=file, embed=embed)

        if message.content.startswith('random gif'):
            message_random = message.content
            split_random = message_random.split()

            if len(split_random) > 2:
                search_words = split_random[2:]
            else:
                search_words = random.choice(common_words)
            search_random = 'https://api.tenor.com/v1/random?key={}&q={}&limit=1&media_filter=basic'.format(
                self.config['tenor_api_key'], search_words
            )
            async with self.session as session:
                async with session.get(search_random) as random_request:
                    if random_request.ok:
                        try:
                            random_json = await random_request.json()
                            results = random_json['results']
                            gif = results[0]
                            url = gif['url']

                            await message.channel.send(url)
                        except Exception as e:
                            await message.channel.send(
                                "{} I couldn't find a gif!".format(
                                    message.author.mention
                                )
                            )
                            print(e)

        await self.process_commands(message)

    @tasks.loop(seconds=60)
    async def clock(self):
        amsterdam = pytz.timezone('Europe/Amsterdam')
        datetime_amsterdam = datetime.datetime.now(amsterdam)
        ams_time = datetime_amsterdam.strftime('%H:%M')
        minute_check = datetime_amsterdam.minute
        if minute_check % 10 == 0:
            print(f'time for cmpc:{ams_time}')
            channel = self.get_channel(753467367966638100)
            ctime = 'cmpc: ' + ams_time
            await channel.edit(name=ctime)

    @tasks.loop(seconds=60)
    async def fish(self):
        global fishgaming
        global fishrestarting
        datetime_gmt = datetime.datetime.now()
        weekday = datetime_gmt.isoweekday()
        channel = self.get_channel(875297517351358474)
        if weekday == 3:
            if fishrestarting and not fishgaming:
                perms = channel.overwrites_for(channel.guild.default_role)
                perms.update(
                    view_channel=True,
                    send_messages=True,
                    create_public_threads=True,
                    create_private_threads=True,
                    send_messages_in_threads=True,
                )
                await channel.set_permissions(
                    channel.guild.default_role, overwrite=perms
                )
                await channel.send('<@&875359516131209256>')
                fishgaming = True
                print('fish gaming wednesday started')
                await channel.send(file=File(r'fishgamingwednesday.mp4'))
            else:
                fishgaming = True
        if weekday != 3:
            if fishgaming:
                fishrestarting = False

                embed = Embed(title='Fish gaming wednesday has ended.', color=0x69CCE7)
                embed.set_image(url=('attachment://' + 'fgwends.png'))
                file = File('fgwends.png', filename='assets/fgwends.png')
                embed.add_field(
                    name='In 5 minutes this channel will be hidden.',
                    value='** **',
                    inline=False,
                )
                message = await channel.send(file=file, embed=embed)

                # set channel to read-only, then wait five minutes
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

                for i in range(4, 1, -1):
                    await asyncio.sleep(60)
                    embed.fields[
                        0
                    ].name = f'In {i} minutes this channel will be hidden.'
                    await message.edit(embed=embed)

                await asyncio.sleep(60)
                embed.fields[0].name = 'In 1 minute this channel will be hidden.'
                await message.edit(embed=embed)
                await asyncio.sleep(60)

                # hide channel
                perms = channel.overwrites_for(channel.guild.default_role)
                perms.update(view_channel=False)
                await channel.set_permissions(
                    channel.guild.default_role, overwrite=perms
                )
                embed6 = Embed(title='Fish gaming wednesday has ended.', color=0x69CCE7)
                embed6.set_image(url=('attachment://' + 'fgwends.png'))
                await message.edit(embed=embed6)
                fishgaming = False

    @commands.command(hidden=True)
    @commands.check(author_is_mod)
    async def shutdown(self, ctx: commands.Context, restart: bool = True):
        # works with pterodactyl
        print('Received shutdown order')
        if restart:
            message = 'Restarting'
            exit_code = 7
        else:
            if not await self.is_owner(ctx.author):
                print('No')
                return
            message = 'Shutting down'
            exit_code = 0
        await ctx.send(message)
        sys.exit(exit_code)


def main():
    # todo make better
    bot = CmpcDidThis(command_prefix=['c.', 'cmpc.', 'Cmpc.', 'CMPC.'], intents=intents)
    bot.remove_command('help')
    print('Connecting to discord...')
    bot.run(bot.config['bot_token'])


if __name__ == '__main__':
    main()
