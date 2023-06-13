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
    token = bot_instance.config.discord_token
    bot_instance.run(token)


if __name__ == "__main__":
    main()
