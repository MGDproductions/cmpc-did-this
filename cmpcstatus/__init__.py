import logging
import sys

from cmpcstatus.bot import Bot, BotHelpCommand, command_prefix
from cmpcstatus.constants import INTENTS

log = logging.getLogger(__name__)
log.addHandler(logging.StreamHandler(sys.stdout))
log.setLevel(logging.INFO)


def main():
    bot_instance = Bot(
        case_insensitive=True,
        command_prefix=command_prefix,
        intents=INTENTS,
        help_command=BotHelpCommand(),
    )

    log.info("Connecting to discord...")
    # remove fancy ass shell colour that looks dumb in dark theme
    formatter = logging.Formatter(logging.BASIC_FORMAT)
    token = bot_instance.config.discord_token
    bot_instance.run(token, log_formatter=formatter)


if __name__ == "__main__":
    main()
