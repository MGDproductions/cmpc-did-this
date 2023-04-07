import asyncio
import datetime
import json
import os
import random
import sys
import textwrap
from io import BytesIO
from typing import Optional

import aiohttp
import aiosqlite
import discord
import profanity_check
import pytz
from PIL import Image, ImageFont, ImageDraw
from discord.ext import commands, tasks
from discord.utils import get


with open("assets/common-words.txt") as f:
    words = f.read().split('\n')

with open('config.json') as config_file:
    data = json.load(config_file)

apikey = data['tenor_api_key']
intents = discord.Intents.all()
intents.members = True
intents.messages = True
fishgaming = True
fishrestarting = True
birthday = False


class CmpcDidThis(commands.Bot):
    def __init__(self, *args, **kwargs):
        self.conn: Optional[aiosqlite.Connection] = None
        self.session: Optional[aiohttp.ClientSession] = None
        super().__init__(*args, **kwargs)

    async def on_ready(self):
        if self.conn is None:
            self.conn = await aiosqlite.connect('db.sqlite3')
            await self.conn.execute(
                """
                CREATE TABLE IF NOT EXISTS lb (
                    time INTEGER,
                    user INTEGER,
                    word TEXT
                );
                """
            )
            await self.conn.commit()
        if self.session is None:
            self.session = aiohttp.ClientSession()
        await bot.change_presence(
            activity=discord.Activity(type=discord.ActivityType.watching, name="the cmpc discord"))
        if data['clock'] and not clock.is_running():
            clock.start()
        if data['fishgamingwednesday'] and not fish.is_running():
            fish.start()

        print(f'Connected to discord as: {bot.user}')
        print('done')  # this line is needed to work with ptero

    async def close(self):
        await super().close()
        await self.conn.close()
        await self.session.close()


bot = CmpcDidThis(command_prefix=['cmpc.', 'Cmpc.', 'CMPC.'], intents=intents)
bot.remove_command('help')


@bot.command()
async def leaderboard(ctx: commands.Context, person: Optional[discord.User] = None):
    # todo more functionality
    async with bot.conn.execute_fetchall(
            'SELECT word, user FROM lb ORDER BY time DESC LIMIT :count ;', {'count': 10}
    ) as rows:
        if not rows:
            return await ctx.send('Nothing to report')
        message = '\n'.join(str(r) for r in rows)
    await ctx.send(message)


intercept = [
    ':3'
]


async def process_profanity(message: discord.Message):
    lower = message.content.casefold()
    mwords = lower.split()
    profanity_array = profanity_check.predict(mwords)

    swears = []
    for i, word in enumerate(mwords):
        if profanity_array[i] or word in intercept:
            swears.append(word)

    if not swears:
        return

    timestamp = message.created_at.timestamp()
    user = message.author.id
    await bot.conn.executemany(
        'INSERT INTO lb (time, user, word) VALUES (?, ?, ?);',
        ((timestamp, user, word,) for word in swears),
    )
    await bot.conn.commit()


@bot.event
async def on_member_join(member):
    role = get(member.guild.roles, id=932977796492427276)
    await member.add_roles(role)
    if data['welcome']:
        print(member.name + " joined")
        strip_width, strip_height = 471, 155
        unwrapped = "Welcome! " + member.name
        text = "\n".join(textwrap.wrap(unwrapped, width=19))
        background = Image.open('assets/bg.png').convert('RGBA')
        font = ImageFont.truetype("assets/Berlin Sans FB Demi Bold.ttf", 40)
        draw = ImageDraw.Draw(background)
        _left, _top, text_width, text_height = draw.textbbox((0, 0), text, font=font)
        position = ((strip_width-text_width)/2, (strip_height-text_height)/2)
        draw.text(position, text, color=(255, 255, 255), font=font, stroke_width=3, stroke_fill='black')
        channel = bot.get_channel(714154159590473801)
        savestring = "cmpcwelcome" + str(random.randint(0, 100000)) + ".png"
        rgb_im = background.convert('RGB')
        rgb_im.save(savestring, "PNG")
        embed = discord.Embed(title=member.name + " joined!", color=0xff0000)
        file = discord.File(savestring, filename=savestring)
        embed.set_image(url=("attachment://" + savestring))
        await channel.send("<@" + str(member.id) + ">")
        await channel.send(file=file, embed=embed)
        os.remove(savestring)


@bot.event
async def on_member_remove(member):
    channel = bot.get_channel(714154159590473801)
    sad_cat = '<:sad_cat:770191103310823426>'
    await channel.send(f"{sad_cat}*** {member.name} ***left the eggyboi family {sad_cat}")


@bot.event
async def on_message(message):
    await process_profanity(message)

    if message.author == bot.user:
        return

    if message.content.startswith('random word'):
        word = random.choice(words)
        await message.channel.send(word)

    if message.content.startswith('cmpc.say'):
        if message.author.id == 416525692772286464:
            await message.channel.send(message.content[9:])

    if message.content.startswith('$testconn'):
        await message.channel.send('hi there dude!')

    if message.content.startswith('random game'):
        async with bot.session as session:
            async with session.get('http://store.steampowered.com/explore/random/') as r:
                shorten = str(r.url).replace('?snr=1_239_random_', '')
        await message.channel.send(shorten)

    if message.content.startswith('random number'):
        try:
            splitmessage = message.content.split()
            startnumber = splitmessage[2]
            endnumber = splitmessage[3]
            randomnumber = random.randint(int(startnumber), int(endnumber))
            await message.channel.send(randomnumber)
        except (IndexError, ValueError):
            await message.channel.send("There is an error in your command.")

    if message.content.startswith('cmpc.help'):
        embed = discord.Embed(title="cmpc did this commands", color=0x00ff00)
        embed.add_field(name="random word", value="gives you a random word", inline=False)
        embed.add_field(name="random game", value="gives you a random game", inline=False)
        embed.add_field(name="random gif", value="gives you a random gif", inline=False)
        embed.add_field(name="random capybara", value="gives you a random capybara", inline=False)
        embed.add_field(
            name="random gif {search term}",
            value="gives you a random gif that matches your search term example: random gif cat", inline=False
        )
        await message.channel.send(embed=embed)
        
    if message.content.startswith("random capybara"):
        async with bot.session as session:
            async with session.get("https://api.capy.lol/v1/capybara") as response:
                img_bytes = BytesIO(await response.content.read())
        embed = discord.Embed(title="capybara for u!", color=0xff0000)
        filename = 'capybara.png'
        file = discord.File(img_bytes, filename=filename)
        embed.set_image(url=("attachment://" + filename))
        await message.channel.send(file=file, embed=embed)

    if message.content.startswith("random gif"):
        message_random = message.content
        split_random = message_random.split()

        if len(split_random) > 2:
            search_words = split_random[2:]
        else:
            search_words = random.choice(words)
        search_random = "https://api.tenor.com/v1/random?key={}&q={}&limit=1&media_filter=basic".format(
            apikey, search_words
        )
        async with bot.session as session:
            async with session.get(search_random) as random_request:
                if random_request.ok:
                    try:
                        random_json = await random_request.json()
                        results = random_json['results']
                        gif = results[0]
                        url = gif['url']

                        await message.channel.send(url)
                    except Exception as e:
                        await message.channel.send("{} I couldn't find a gif!".format(message.author.mention))
                        print(e)

    await bot.process_commands(message)


@tasks.loop(seconds=60)
async def clock():
    amsterdam = pytz.timezone('Europe/Amsterdam')
    datetime_amsterdam = datetime.datetime.now(amsterdam)
    ams_time = datetime_amsterdam.strftime("%H:%M")
    minute_check = datetime_amsterdam.minute
    if minute_check % 10 == 0:
        print(f"time for cmpc:{ams_time}")
        channel = bot.get_channel(753467367966638100)
        ctime = "cmpc: " + ams_time
        await channel.edit(name=ctime)


@tasks.loop(seconds=60)
async def fish():
    global fishgaming
    global fishrestarting
    datetime_gmt = datetime.datetime.now()
    weekday = datetime_gmt.isoweekday()
    channel = bot.get_channel(875297517351358474)
    if weekday == 3:
        if fishrestarting and not fishgaming:
            perms = channel.overwrites_for(channel.guild.default_role)
            perms.update(
                view_channel=True,
                send_messages=True,
                create_public_threads=True,
                create_private_threads=True,
                send_messages_in_threads=True
            )
            await channel.set_permissions(channel.guild.default_role, overwrite=perms)
            await channel.send("<@&875359516131209256>")
            fishgaming = True
            print("fish gaming wednesday started")
            await channel.send(file=discord.File(r'fishgamingwednesday.mp4'))
        else:
            fishgaming = True
    if weekday != 3:
        if fishgaming:
            fishrestarting = False

            embed = discord.Embed(title="Fish gaming wednesday has ended.", color=0x69CCE7)
            embed.set_image(url=("attachment://" + "fgwends.png"))
            file = discord.File("fgwends.png", filename="assets/fgwends.png")
            embed.add_field(name="In 5 minutes this channel will be hidden.", value="** **", inline=False)
            message = await channel.send(file=file, embed=embed)

            # set channel to read-only, then wait five minutes
            perms = channel.overwrites_for(channel.guild.default_role)
            perms.update(
                send_messages=False,
                create_public_threads=False,
                create_private_threads=False,
                send_messages_in_threads=False
            )
            await channel.set_permissions(channel.guild.default_role, overwrite=perms)

            for i in range(4, 1, -1):
                await asyncio.sleep(60)
                embed.fields[0].name = f"In {i} minutes this channel will be hidden."
                await message.edit(embed=embed)

            await asyncio.sleep(60)
            embed.fields[0].name = "In 1 minute this channel will be hidden."
            await message.edit(embed=embed)
            await asyncio.sleep(60)

            # hide channel
            perms = channel.overwrites_for(channel.guild.default_role)
            perms.update(
                view_channel=False
            )
            await channel.set_permissions(channel.guild.default_role, overwrite=perms)
            embed6 = discord.Embed(title="Fish gaming wednesday has ended.", color=0x69CCE7)
            embed6.set_image(url=("attachment://" + "fgwends.png"))
            await message.edit(embed=embed6)
            fishgaming = False


def author_is_mod(interaction) -> bool:
    # mod role
    return get(interaction.author.roles, id=725356663850270821) is not None


@bot.command(hidden=True)
@commands.check(author_is_mod)
async def shutdown(ctx: commands.Context, restart: bool = True):
    print('Received shutdown order')
    if restart:
        message = 'Restarting'
        exit_code = 7
    else:
        if not ctx.bot.is_owner(ctx.author):
            return
        message = 'Shutting down'
        exit_code = 0
    await ctx.send(message)
    sys.exit(exit_code)


def main():
    print("Connecting to discord...")
    bot.run(data['bot_token'])


if __name__ == '__main__':
    main()
