from typing import Optional

import aiosqlite
import discord
from better_profanity import profanity
from discord import Member, Message, utils
from discord.ext import commands
from discord.ext.commands import Context

from cmpcstatus import BotCog
from cmpcstatus.constants import (
    MENTION_NONE,
    PATH_DATABASE,
    PROFANITY_INTERCEPT,
    PROFANITY_ROWS_DEFAULT,
    PROFANITY_ROWS_INLINE,
    PROFANITY_ROWS_MAX,
    ROLE_DEVELOPER,
)


# wraps the library to make it easier to swap out
# if I want to switch to the ml one
# that's machine learning not marxist-leninism thankfully
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
