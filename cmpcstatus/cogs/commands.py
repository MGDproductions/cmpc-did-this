import random
import subprocess
import urllib.parse
from io import BytesIO
from tempfile import TemporaryFile
from typing import Literal, Optional

import discord
from discord import Embed, Member
from discord.ext import commands
from discord.ext.commands import Context

from assets.words import common_words
from cmpcstatus import BotCog, log
from cmpcstatus.constants import COLOUR_RED, ROLE_DEVELOPER


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
                    subprocess.run(
                        ["git", "archive", "--format=zip", "HEAD"], stdout=file
                    )
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
