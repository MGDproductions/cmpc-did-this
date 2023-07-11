import datetime
from zoneinfo import ZoneInfo

import discord

# bot API intents
INTENTS = discord.Intents.default()
INTENTS.members = True
INTENTS.message_content = True

# bot features
ENABLE_BIRTHDAY = True
ENABLE_CLOCK = True
# todo enable
ENABLE_EPIC = False
ENABLE_FISH = True
ENABLE_PROFANITY = True
ENABLE_READY_MESSAGE = True
ENABLE_WELCOME = True
ENABLE_SLASH_COMMANDS = True

TESTING = True

FONT_SIZE_WELCOME = 40

# file locations
PATH_CONFIG = "config.toml"
PATH_DATABASE = "db.sqlite3"

# discord guild, role, and channel IDs
GUILD_EGGYBOI = 714154158969716780
ROLE_DEVELOPER = 741317598452645949
ROLE_FISH = 875359516131209256
ROLE_MEMBER = 932977796492427276
ROLE_MODS = 725356663850270821

USER_JMCB = 329885271787307008

TEXT_CHANNEL_FISH = 875297517351358474
# TEXT_CHANNEL_BIRTHDAY = 982687737503182858
TEXT_CHANNEL_BIRTHDAY = TEXT_CHANNEL_FISH
TEXT_CHANNEL_GENERAL = 714154159590473801
TEXT_CHANNEL_BOT_COMMANDS = 736664393630220289
VOICE_CHANNEL_CLOCK = 753467367966638100

# discord channel permissions
CHANNEL_PERMISSIONS_OPEN = {"view_channel": True, "send_messages": True}
CHANNEL_PERMISSIONS_LOCKED = {"view_channel": True, "send_messages": False}
CHANNEL_PERMISSIONS_HIDDEN = {"view_channel": False, "send_messages": False}

# discord colour objects
COLOUR_GREEN = discord.Color.green()
COLOUR_RED = discord.Color.red()
COLOUR_BLUE = discord.Color.blue()

# discord emote objects
EMOJI_BIBI_PARTY = discord.PartialEmoji.from_str("<:bibi_party:857659475687374898>")
EMOJI_SAT_CAT = discord.PartialEmoji.from_str("<:sad_cat:770191103310823426>")
EMOJI_SKULL = discord.PartialEmoji.from_str("💀")

MENTION_NONE = discord.AllowedMentions.none()

# date and time information for events
TZ_AMSTERDAM = ZoneInfo("Europe/Amsterdam")
TZ_LONDON = ZoneInfo("Europe/London")

CLOCK_TIMES = [
    datetime.time(hour=h, minute=m, tzinfo=TZ_AMSTERDAM)
    for m in range(0, 60, 10)
    for h in range(24)
]

TIME_MIDNIGHT = datetime.time(hour=0, tzinfo=TZ_AMSTERDAM)
TIME_FIVE_PAST_MIDNIGHT = datetime.time(hour=0, minute=5, tzinfo=TZ_AMSTERDAM)
TIME_FGW_START = TIME_MIDNIGHT
TIME_FGW_LOCK = TIME_MIDNIGHT
TIME_FGW_END = TIME_FIVE_PAST_MIDNIGHT
TIME_BDAY_START = TIME_MIDNIGHT
TIME_BDAY_LOCK = TIME_MIDNIGHT
TIME_BDAY_END = TIME_FIVE_PAST_MIDNIGHT

DATE_BIRTHDAY_MONTH = 6
DATE_BIRTHDAY_DAY = 5
ISO_WEEKDAY_WEDNESDAY = 3
ISO_WEEKDAY_THURSDAY = 4
# how many seconds in a minute
COUNTDOWN_MINUTE = 60

# profanity config
PROFANITY_INTERCEPT = (":3",)
PROFANITY_ROWS_DEFAULT = 5
PROFANITY_ROWS_MAX = 100
PROFANITY_ROWS_INLINE = False

# bot command prefices
COMMAND_PREFIX = [
    "random ",  # space is needed
    "cmpc.",
    "c.",
    "$",
]
