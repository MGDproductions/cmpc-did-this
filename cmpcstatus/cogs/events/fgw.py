import datetime
import logging

from cmpcstatus.cogs.events._base import EventCog
from cmpcstatus.constants import (
    ISO_WEEKDAY_THURSDAY,
    ISO_WEEKDAY_WEDNESDAY,
    ROLE_FISH,
    TESTING,
    TEXT_CHANNEL_FISH,
    TIME_FGW_END,
    TIME_FGW_LOCK,
    TIME_FGW_START,
    TZ_AMSTERDAM,
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
        mention = "<@329885271787307008>"
    else:
        mention = f"<@&{ROLE_FISH}>"
    start_filename = "fgw.mp4"
    start_message = f"{mention}"
    end_filename = "fgwends.png"
    end_message = f"{name} has ended."

    start_time = TIME_FGW_START
    lock_time = TIME_FGW_LOCK
    end_time = TIME_FGW_END

    @staticmethod
    def is_today(day: int) -> bool:
        datetime_amsterdam = datetime.datetime.now(TZ_AMSTERDAM)
        result = datetime_amsterdam.isoweekday() == day
        log.info("day-of-week check %d : %s : %s", day, datetime_amsterdam, result)
        return result

    def is_start_date(self) -> bool:
        return self.is_today(ISO_WEEKDAY_WEDNESDAY)

    def is_end_date(self) -> bool:
        return self.is_today(ISO_WEEKDAY_THURSDAY)
