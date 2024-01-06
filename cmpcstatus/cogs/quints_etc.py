from discord import Message
from discord.ext import commands
from discord.ext.commands import Cog, Context

from cmpcstatus.constants import ROLE_DEVELOPER


class Quints(Cog):
    qualifiers = {
        5: "QUINTS",
        6: "SEX",
        7: "SEPTS",
    }

    @staticmethod
    def consecutive_digits(number: int) -> int:
        digit = number % 10
        consecutive = 1
        while number > 9:
            number //= 10
            if number % 10 != digit:
                break
            consecutive += 1

        return consecutive

    async def quints(self, message: Message, message_id: int):
        consecutive = self.consecutive_digits(message_id)

        qual = self.qualifiers.get(consecutive)
        if qual is None:
            return

        await message.channel.send(
            f'{message.author.name} sent "{message.content[5:]}..." with Message ID: {message.id} (***{qual}***)'
        )

    @Cog.listener()
    async def on_message(self, message: Message):
        await self.quints(message, message.id)

    @commands.command(hidden=True)
    @commands.has_role(ROLE_DEVELOPER)
    async def test_quints(self, ctx: Context, message_id: int):
        await self.quints(ctx.message, message_id)
