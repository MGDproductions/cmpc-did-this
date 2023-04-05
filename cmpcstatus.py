import asyncio
import datetime
import json
import os
import random
import textwrap

import aiohttp
import discord
import pytz
from PIL import Image, ImageFont, ImageDraw
from discord.ext.commands import Bot
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
bot = Bot(command_prefix=['cmpc.','Cmpc.','CMPC.'],intents=intents)
bot.remove_command('help')
cmpcoffline = []

@bot.event
async def on_ready():
    print('Connected to discord as: {0.user}'.format(bot))
    print('done')
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="the cmpc discord"))
    loop = asyncio.get_event_loop()
    asyncio.ensure_future(clock())
    asyncio.ensure_future(fish())

@bot.event
async def on_member_join(member):
    role = get(member.guild.roles, id=932977796492427276)
    await member.add_roles(role)
    if data['welcome'] == "true":
        print(member.name + " joined")
        channel = bot.get_channel(816406795210850356)
        strip_width, strip_height = 471, 155
        unwrapped = "Welcome! " + member.name
        text = "\n".join(textwrap.wrap(unwrapped, width=19))
        background = Image.open('assets/bg.png').convert('RGBA')
        font = ImageFont.truetype("assets/Berlin Sans FB Demi Bold.ttf", 40)
        shadowcolor = "black"
        draw = ImageDraw.Draw(background)
        text_width, text_height = draw.textsize(text, font)
        imgWidth,imgHeight = background.size
        x = imgWidth - text_width - 100
        y = imgHeight - text_height - 100
        position = ((strip_width-text_width)/2,(strip_height-text_height)/2)
        draw.text(position, text, color=(255, 255, 255), font=font, stroke_width=3, stroke_fill='black')
        channel = bot.get_channel(714154159590473801)
        savestring = "cmpcwelcome" + str(random.randint(0,100000)) + ".png"
        rgb_im = background.convert('RGB')
        rgb_im.save(savestring,"PNG")
        embed=discord.Embed(title=member.name + " joined!", color=0xff0000)
        file = discord.File(savestring, filename=savestring)
        embed.set_image(url=("attachment://" + savestring))
        await channel.send("<@" + str(member.id) + ">")
        await channel.send(file=file, embed=embed)
        os.remove(savestring)

@bot.event
async def on_member_remove(member):
    channel = bot.get_channel(714154159590473801)
    await channel.send(("<:sad_cat:770191103310823426> ***" + member.name + "*** left the eggyboi family <:sad_cat:770191103310823426>"))

@bot.event
async def on_message(message):

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
        async with aiohttp.ClientSession() as session:
            async with session.get('http://store.steampowered.com/explore/random/') as r:
                shorten = r.url
        await message.channel.send(shorten.replace('?snr=1_239_random_', ''))

    if message.content.startswith('random number'):
        try:
            splitmessage = message.content.split()
            startnumber = splitmessage[2]
            endnumber = splitmessage[3]
            randomnumber = random.randint(int(startnumber), int(endnumber))
            await message.channel.send(randomnumber)
        except:
            await message.channel.send("There is an error in your command.")

    if message.content.startswith('cmpc.help'):
        embed=discord.Embed(title="cmpc did this commands", color=0x00ff00)
        embed.add_field(name="random word", value="gives you a random word", inline=False)
        embed.add_field(name="random game", value="gives you a random game", inline=False)
        embed.add_field(name="random gif", value="gives you a random gif", inline=False)
        embed.add_field(name="random capybara", value="gives you a random capybara", inline=False)
        embed.add_field(name="random gif {search term}", value="gives you a random gif that matches your search term example: random gif cat", inline=False)
        await message.channel.send(embed=embed)
        
    if message.content.startswith("random capybara"):
        img = Image.open(requests.get("https://api.capy.lol/v1/capybara", stream=True).raw)
        savestring = "capybara" + str(random.randint(0,100000)) + ".png"
        rgb_im = img.convert('RGB')
        rgb_im.save(savestring,"PNG")
        embed=discord.Embed(title="capybara for u!", color=0xff0000)
        file = discord.File(savestring, filename=savestring)
        embed.set_image(url=("attachment://" + savestring))
        await message.channel.send(file=file, embed=embed)
        os.remove(savestring)

    if message.content.startswith("random gif"):
        message_random = message.content
        split_random = message_random.split()

        if len(split_random) == 2:
            search_random = "https://api.tenor.com/v1/random?key={}&q={}&limit=1&media_filter=basic".format(apikey, random.choice(words))
        elif len(split_random) >= 3:
            search_random = "https://api.tenor.com/v1/random?key={}&q={}&limit=1&media_filter=basic".format(apikey, split_random[2:])
        async with aiohttp.ClientSession() as session:
            async with session.get(search_random) as random_request:
                if random_request.ok:
                    try:
                        random_json = await random_request.json()
                        results = random_json['results']
                        gif = results[0]
                        url = gif['url']

                        await message.channel.send(url)
                    except:
                        await message.channel.send("{} I couldn't find a gif!".format(message.author.mention))

    await bot.process_commands(message)

async def clock():
    if data['clock'] == "true":
        amsterdam = pytz.timezone('Europe/Amsterdam')
        datetime_amsterdam = datetime.datetime.now(amsterdam)
        ams_time = datetime_amsterdam.strftime("%H:%M")
        minute_check = datetime_amsterdam.strftime("%M")
        if int(minute_check) % 10 == 0:
            print(f"time for cmpc:{ams_time}")
            channel = bot.get_channel(753467367966638100)
            ctime = "cmpc: " + ams_time 
            await channel.edit(name=ctime)
        await asyncio.sleep(60)
        asyncio.ensure_future(clock())
    
async def fish():
    if data['fishgamingwednesday'] == "true":
        global fishgaming
        global fishrestarting
        gmt = pytz.timezone('GMT')
        datetime_gmt = datetime.datetime.now()
        weekday = datetime_gmt.isoweekday()
        channel = bot.get_channel(875297517351358474)
        if weekday == 3:
            if fishgaming == False and fishrestarting != True:
                perms = channel.overwrites_for(channel.guild.default_role)
                perms.send_messages=True
                perms.view_channel=True
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
                perms = channel.overwrites_for(channel.guild.default_role)
                perms.send_messages = False
                await channel.set_permissions(channel.guild.default_role, overwrite=perms)

                embed = discord.Embed(title="Fish gaming wednesday has ended.", color=0x69CCE7)
                embed.set_image(url=("attachment://" + "fgwends.png"))
                file = discord.File("fgwends.png", filename="assets/fgwends.png")
                embed.add_field(name="In 5 minutes this channel will be hidden.", value="** **", inline=False)
                message = await channel.send(file=file, embed=embed)

                for i in range(4, 1, -1):
                    await asyncio.sleep(60)
                    embed.fields[0].name = f"In {i} minutes this channel will be hidden."
                    await message.edit(embed=embed)

                await asyncio.sleep(60)
                embed.fields[0].name = "In 1 minute this channel will be hidden."
                await message.edit(embed=embed)
                await asyncio.sleep(60)

                perms = channel.overwrites_for(channel.guild.default_role)
                perms.view_channel=False
                #not working but needs to be fixed
                #perms.create_public_threads=False
                #perms.create_private_threads=False
                #perms.send_messages_in_threads=False
                await channel.set_permissions(channel.guild.default_role, overwrite=perms)
                embed6=discord.Embed(title="Fish gaming wednesday has ended.", color=0x69CCE7)
                embed6.set_image(url=("attachment://" + "fgwends.png"))
                await message.edit(embed=embed6)
                fishgaming = False
        await asyncio.sleep(60)
        asyncio.ensure_future(fish())
        
# if data['birthday'] == "true":
#     @tasks.loop(minutes=1)
#     async def birthday_update():
#             global birthday
#             cest = pytz.timezone('Europe/London')
#             datetime_cest = datetime.datetime.now(cest)
#             weekday = False
#             channel = bot.get_channel(982687737503182858)
#             if "06-05" in str(datetime_cest):
#                 if birthday == False:
#                     perms = channel.overwrites_for(channel.guild.default_role)
#                     perms.send_messages=True
#                    perms.view_channel=True
#                    await channel.set_permissions(channel.guild.default_role, overwrite=perms)
#                    await channel.send("@everyone It's Marcel's birthday today! As a birthday gift he wants all the cat pictures in the world. Drop them in this chat before he wakes up!")
#                    birthday = True
#                    print("Marcel's birthday started")
#       #              await channel.send(file=discord.File(r'birthday.mp4'))
#            if "06-05" not in str(datetime_cest):
#                if birthday == True:
#                    perms = channel.overwrites_for(channel.guild.default_role)
#                    perms.send_messages=False
#                    await channel.set_permissions(channel.guild.default_role, overwrite=perms)
#                    embed=discord.Embed(title="Marcel's birthday has ended.", color=0x69CCE7)
#                    embed.add_field(name="In 5 minutes this channel will be hidden.", value="** **", inline=False)
#                    message = await channel.send(embed=embed)
#                    await asyncio.sleep(60)
#                    embed2=discord.Embed(title="Marcel's birthday has ended.", color=0x69CCE7)
#                    embed2.add_field(name="In 4 minutes this channel will be hidden.", value="** **", inline=False)
#                    await message.edit(embed=embed2)
#                    await asyncio.sleep(60)
#                    embed3=discord.Embed(title="Marcel's birthday has ended.", color=0x69CCE7)
#                    embed3.add_field(name="In 3 minutes this channel will be hidden.", value="** **", inline=False)
#                    await message.edit(embed=embed3)
#                    await asyncio.sleep(60)
#                    embed4=discord.Embed(title="Marcel's birthday has ended.", color=0x69CCE7)
#                    embed4.add_field(name="In 2 minutes this channel will be hidden.", value="** **", inline=False)
#                    await message.edit(embed=embed4)
#                    await asyncio.sleep(60)
#            #        embed5=discord.Embed(title="Marcel's birthday has ended.", color=0x69CCE7)
#                    embed5.add_field(name="In 1 minute this channel will be hidden.", value="** **", inline=False)
#                    await message.edit(embed=embed5)
#                    await asyncio.sleep(60)
#                    perms = channel.overwrites_for(channel.guild.default_role)
#                    perms.view_channel=False
#                    await channel.set_permissions(channel.guild.default_role, overwrite=perms)
#                    embed6=discord.Embed(title="Marcel's birthday has ended.", color=0x69CCE7)
#                    await message.edit(embed=embed6)
#                    birthday = False
#
#    @birthday_update.before_loop
#    async def before_birthday_update():
#        await bot.wait_until_ready()
#    birthday_update.start()
#
# @tasks.loop(minutes=10)
# async def countdown():
#     difference = datetime.datetime(2021, 7, 4, 18, 0, 0) - datetime.datetime.now()
#     count_hours, rem = divmod(difference.seconds, 3600)
#     count_minutes, count_seconds = divmod(rem, 60)
#     channel = bot.get_channel(858737401048465420)
#     channel2 = bot.get_channel(858737233112727552)
#     if difference.days < 0:
#         await channel.delete()
#         await channel2.edit(name="Goodbye cmpc.")
#         countdown.cancel()
#     countdowntime = (str(count_hours) + "h " + str(count_minutes) + "m ")
#     print(countdowntime)
#     await channel.edit(name=countdowntime)
#
# @countdown.before_loop
# async def before_countdown():
#     await bot.wait_until_ready()
#     countdown.start()


def main():
    print("Connecting to discord...")
    bot.run(data['bot_token'])


if __name__ == '__main__':
    main()
