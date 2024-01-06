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

    @staticmethod
    def truncate_str(string: str, length: int) -> str:
        if len(string) <= length:
            return string
        else:
            return string[:length]

    async def quints(self, message: Message, message_id: int):
        consecutive = self.consecutive_digits(message_id)

        qual = self.qualifiers.get(consecutive)
        if qual is None:
            return

        content = self.truncate_str(message.content, 5)

        await message.channel.send(
            f'{message.author.name} sent "{content}..." with Message ID: {message_id} (***{qual}***)'
        )

    @Cog.listener()
    async def on_message(self, message: Message):
        await self.quints(message, message.id)

    @commands.command(hidden=True)
    @commands.has_role(ROLE_DEVELOPER)
    async def test_quints(self, ctx: Context, message_id: int):
        await self.quints(ctx.message, message_id)
