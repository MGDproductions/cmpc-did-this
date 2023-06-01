#!/usr/bin/env python

import logging
import sys

from cmpcstatus.bot import BotHelpCommand, CmpcDidThis, command_prefix
from cmpcstatus.constants import INTENTS

log = logging.getLogger(__name__)
log.addHandler(logging.StreamHandler(sys.stdout))
log.setLevel(logging.INFO)


# todo send message on shutdown


def main():
    bot = CmpcDidThis(
        case_insensitive=True,
        command_prefix=command_prefix,
        intents=INTENTS,
        help_command=BotHelpCommand(),
    )
    # TODO
    # add default cogs
    # await self.add_cog(BasicCommands(self))
    # await self.add_cog(DeveloperCommands(self))
    # if ENABLE_BIRTHDAY:
    #     await self.add_cog(Birthday(self))
    # if ENABLE_FISH:
    #     await self.add_cog(FishGamingWednesday(self))
    # if ENABLE_PROFANITY:
    #     await self.add_cog(ProfanityLeaderboard(self))
    log.info("Connecting to discord...")
    # remove fancy ass shell colour that looks dumb in dark theme
    bot_log_formatter = logging.Formatter(logging.BASIC_FORMAT)
    bot.run(bot.config.discord_token, log_formatter=bot_log_formatter)


if __name__ == "__main__":
    main()
