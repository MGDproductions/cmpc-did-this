import datetime

from discord import TextChannel

from cmpcstatus.cogs.events import EventCog
from cmpcstatus.constants import ISO_WEEKDAY_THURSDAY, TESTING, TZ_AMSTERDAM, TEXT_CHANNEL_GENERAL, USER_JMCB

ROLE_GAMING_GANG = 785222184309489665
TIME_EPIC_FREE_GAME = datetime.time(hour=17, tzinfo=TZ_AMSTERDAM)


class EpicFreeGame(EventCog):
    channel_id = TEXT_CHANNEL_GENERAL

    start_time = TIME_EPIC_FREE_GAME
    if TESTING:
        mention = F"<@{USER_JMCB}>"
    else:
        mention = f"<@&{ROLE_GAMING_GANG}>"
    start_message = f"{mention} new free game <https://store.epicgames.com/>"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # only need the start routine
        self.tasks = (self.event_start,)

    def is_start_date(self) -> bool:
        return self.is_today(ISO_WEEKDAY_THURSDAY)

    async def send_start_message(self, channel: TextChannel):
        await channel.send(self.start_message)
