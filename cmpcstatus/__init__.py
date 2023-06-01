#!/usr/bin/env python

import logging
import sys

from cmpcstatus.bot import BotCog, BotHelpCommand, CmpcDidThis, command_prefix
from cmpcstatus.constants import INTENTS

log = logging.getLogger(__name__)
log.addHandler(logging.StreamHandler(sys.stdout))
log.setLevel(logging.INFO)


def main():
    bot = CmpcDidThis(
        case_insensitive=True,
        command_prefix=command_prefix,
        intents=INTENTS,
        help_command=BotHelpCommand(),
    )
    log.info("Connecting to discord...")
    # remove fancy ass shell colour that looks dumb in dark theme
    bot_log_formatter = logging.Formatter(logging.BASIC_FORMAT)
    bot.run(bot.config.discord_token, log_formatter=bot_log_formatter)


if __name__ == "__main__":
    main()
