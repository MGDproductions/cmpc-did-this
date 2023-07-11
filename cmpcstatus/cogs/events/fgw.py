import logging

from cmpcstatus.cogs.events import EventCog
from cmpcstatus.constants import (
    ISO_WEEKDAY_THURSDAY,
    ISO_WEEKDAY_WEDNESDAY,
    ROLE_FISH,
    TESTING,
    TEXT_CHANNEL_FISH,
    TIME_FGW_END,
    TIME_FGW_LOCK,
    TIME_FGW_START,
    USER_JMCB,
)

log = logging.getLogger(__name__)


class FishGamingWednesday(EventCog):
    name = "Fish gaming wednesday"
    channel_id = TEXT_CHANNEL_FISH
    channel_name = "fish-gaming-wednesday"
    channel_topic = (
        "conversation doesn't have to be about gaming,"
        " chat that's only accessible on wednesday my dudes (GMT + 1)"
    )

    if TESTING:
        mention = f"<@{USER_JMCB}>"
    else:
        mention = f"<@&{ROLE_FISH}>"
    start_filename = "fgw.mp4"
    start_message = f"{mention}"
    end_filename = "fgwends.png"
    end_message = f"{name} has ended."

    start_time = TIME_FGW_START
    lock_time = TIME_FGW_LOCK
    end_time = TIME_FGW_END

    def is_start_date(self) -> bool:
        return self.is_today(ISO_WEEKDAY_WEDNESDAY)

    def is_end_date(self) -> bool:
        return self.is_today(ISO_WEEKDAY_THURSDAY)
