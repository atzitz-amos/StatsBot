import datetime
import enum
import time

import discord
import pytz

from bot.graphs.creator import overflow, generateBar
from bot.holders import ClientHolder, IndexingHolder


async def createEmbed(title, description="", elapsed=None):
    e = discord.Embed(title=title, description=description, color=0x16cf94)
    e.set_footer(text=f"Stats Bot{' - ' + str(float(round(elapsed, 2))) + 's elapsed' if elapsed else ''}",
                 icon_url="https://cdn.discordapp.com/avatars/907984226564046880/858b16457dd3161b771d9ff010c452a6.webp?size=100")
    return e


async def getMember(guid, uid):
    guild = await ClientHolder.client.fetch_guild(guid)
    return await guild.fetch_member(uid)


class Data(enum.Enum):
    AUTHOR = 0
    DATETIME = 1
    MESSAGES = 2
    CONTENT = 3
    BY = 5


class Filterer:

    def __init__(self):
        self.from_ = None
        self.to = None
        self.contains = None

    def set_from(self, value):
        self.from_ = self._extract_datetime(value) if value else None

    def set_to(self, value):
        self.to = self._extract_datetime(value) if value else None

    def set_contains(self, value):
        self.contains = value

    def _extract_datetime(self, dt):
        try:
            d, m, y = dt.split("-")
            d, m, y = int(d), int(m), int(y)
            return pytz.utc.localize(datetime.datetime(year=y, month=m, day=d))
        except TypeError or ValueError:
            raise ValueError("Wrong date format. Please give dates in format dd-mm-yyyy")

    def validate(self, message):
        flag0, flag1, flag2 = not self.from_, not self.to, not self.contains
        if not flag0:
            dt = pytz.utc.localize(datetime.datetime.fromtimestamp(int(message[0])))
            flag0 = self.from_ <= dt
        if not flag1:
            dt = pytz.utc.localize(datetime.datetime.fromtimestamp(message[0]))
            flag1 = self.to >= dt
        if not flag2:
            flag2 = self.contains in message[2]
        return flag0 and flag1 and flag2


class Mappings:

    def __init__(self, mappings, key, value):
        self.mappings = mappings
        self.key = key
        self.value = value


def command(base, sub):
    def decorator(func):
        async def trigger(channel, b, s, **opts):
            return await func(channel, **opts)

        TriggerProcessor.addTrigger(base, sub, trigger=trigger)

    return decorator


def _fetch_and_filter(index, key, value, filterer=None):
    match key:
        case Data.AUTHOR:
            key_set = set(index.by_author.keys())
            msg_provider = lambda k: list(filter(lambda val: int(k) == val[1], index.messages.values()))
        case Data.DATETIME:
            key_set = set(index.by_datetime.keys())
            msg_provider = lambda k: index.by_datetime[k]
        case Data.CONTENT:
            key_set = set(map(lambda x: x[2], index.messages))
            msg_provider = lambda k: list(filter(lambda val: k in val[2], index.messages.values()))
        case Data.MESSAGES, Data.BY, _:
            raise ValueError(f"Cannot use {key} as key")
    match value:
        case Data.AUTHOR:
            value_provider = lambda msg: msg[1]
        case Data.DATETIME:
            value_provider = lambda msg: msg[0]
        case Data.MESSAGES:
            value_provider = lambda msg: msg[3]
        case Data.CONTENT:
            value_provider = lambda msg: msg[2]
        case _:
            raise ValueError(f"Cannot use {value} as value")
    result = {}
    for key in key_set:
        result[key] = [value_provider(msg) for msg in msg_provider(key) if filterer.validate(msg)]
    return Mappings(result, key, value)


def data(key, value):
    def decorator(func):
        async def trigger(channel, **opts):
            k = key
            if key == Data.BY:
                by = opts.get("by")
                if not by:
                    raise ValueError("Argument `by` must be fulfilled")
                match by:
                    case "author":
                        k = Data.AUTHOR
                    case "datetime":
                        k = Data.DATETIME
                    case "content":
                        k = Data.CONTENT
                    case _:
                        raise ValueError("Argument `by` can only be `author`, `datetime` or `content`")
            filterer = Filterer()
            filterer.set_from(opts.get("from"))
            filterer.set_to(opts.get("to"))
            filterer.set_contains(opts.get("contains"))

            return await func(channel,
                              _fetch_and_filter(IndexingHolder.fromChannel(channel), k, value, filterer=filterer),
                              **opts)

        return trigger

    return decorator


def sorter(func):
    async def trigger(channel, mappings, **opts):
        sorting = opts.get("sortedby", "greater")
        mappings.mappings = dict(sorted(mappings.mappings.items(), key=lambda el: el[1], reverse=sorting == "lower"))
        return await func(channel, mappings, **opts)

    return trigger


class TriggerProcessor:
    triggers = []

    @classmethod
    def addTrigger(cls, base, sub, trigger=None):
        cls.triggers.append((base, sub, trigger))

    @classmethod
    async def invoke(cls, channel, string):
        extracted = cls.extract(string)
        if not extracted:
            return -1
        b, s, opts = extracted
        for base, sub, trigger in cls.triggers:
            if base == b and sub == s:
                if callable(trigger):
                    await trigger(channel, base, sub, **opts)
                break
        return -1

    @classmethod
    def extract(cls, string: str):
        """
            Extract base, sub and options from a string
            -------
            Example
            -------
            !stats messages by datetime sorted count
            --> base='stats'; sub='messages'; options={'by': 'datetime', 'sorted': 'count'}
        """
        if not string.startswith("!"):
            return
        split = string.replace("!", "", 1).split()
        if len(split) < 2:
            return
        base, sub = split[:2]
        options = {}
        i = 2
        while i < len(split):
            value = split[i + 1]
            if value.startswith('"'):
                body = value[1:]
                j = 0
                for part in split[i + 2:]:
                    body += " " + part
                    j += 1
                    if part.endswith('"'):
                        break
                if not body.endswith('"'):
                    value = body[:-1]
                else:
                    options[split[i]] = body[:-1]
                    i += j
            else:
                options[split[i]] = value
            i += 2
        return base, sub, options


@command("stats", "messages")
@data(Data.BY, Data.MESSAGES)
@sorter
async def message_stats(channel, mappings, **opts):
    mappings = mappings.mappings
    start = time.perf_counter()
    if opts.get("by") == "author":
        print(opts)
        x, y = [], []
        for k, v in mappings.items():
            try:
                x.append((await getMember(channel.guild.id, k)).name)
            except discord.NotFound:
                continue
            y.append(len(v))
    elif opts.get("by") == "datetime":
        x, y = list(mappings.keys()), [len(v) for v in mappings.values()]
    return await overflow(channel=channel, embed=await createEmbed("Stats - Messages per Members",
                                                                   elapsed=time.perf_counter() - start),
                          filename="stats_graph_messages_per_members",
                          x=x,
                          y=y,
                          xlabel="Members",
                          ylabel="Messages",
                          title="Messages per Members", creator=generateBar)


@command("stats", "something")
@data(Data.BY, Data.CONTENT)
async def something(c, mappings, **opts):
    print(c, mappings)
