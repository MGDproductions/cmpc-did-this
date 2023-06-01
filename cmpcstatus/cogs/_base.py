from typing import TYPE_CHECKING

from discord.ext import commands

if TYPE_CHECKING:
    from cmpcstatus.bot import Bot


class BotCog(commands.Cog):
    def __init__(self, bot: "Bot", *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.bot = bot
