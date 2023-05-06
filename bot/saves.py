import datetime
import os

import aiofiles as aiofiles

from bot.holders import ClientHolder


async def load(filename):
    d = {}
    async with aiofiles.open(filename, mode="r") as reader:
        for arg in (await reader.read()).split("\n"):
            if arg:
                k, v = arg.split(":", 1)
                d[k] = eval(v)
    guild = await ClientHolder.client.fetch_guild(d.pop("guild"))
    inst = SaveState(await guild.fetch_channel(d.pop("channel")))
    for k, v in d.items():
        if k == "last_indexed":
            v = datetime.datetime.fromtimestamp(float(v))
        setattr(inst, k, v)
    return inst


class SaveState:

    def __init__(self, channel):
        self.channel = channel
        self.guild = channel.guild.id
        self.last_indexed = datetime.datetime.now()
        self.messages = {}
        self.by_datetime = {}
        self.by_author = {}

    def __del__(self):
        print("Deleting SaveState, dumping into file", "save-" + str(self.last_indexed))
        # self.dump()

    def dump(self, messages=None, by_datetime=None, by_author=None):
        self.set(messages=messages, by_datetime=by_datetime, by_author=by_author)
        print("Dumping...")
        self.last_indexed = datetime.datetime.now()

        path = "saves/guild-" + str(self.channel.guild).replace(" ", "_")
        if not os.path.exists(path):
            os.mkdir(path)

        with open(path + "/channel-" + str(self.channel).replace(" ", "_") + ".save", "w+") as io:
            attrs = self._transform_attrs()
            text = ""
            for k, v in attrs.items():
                text += k + ":" + str(v) + "\n"
            io.write(text)
        print("Done!")

    def set(self, messages=None, by_datetime=None, by_author=None):
        if messages:
            self.messages = messages
        if by_datetime:
            self.by_datetime = by_datetime
        if by_author:
            self.by_author = by_author

    def dumpAdd(self, messages=None, by_datetime=None, by_author=None):
        self.extend(messages=messages, by_datetime=by_datetime, by_author=by_author)
        self.dump()

    def extend(self, messages=None, by_datetime=None, by_author=None):
        if messages:
            self.messages.update(**messages)
        if by_datetime:
            self.by_datetime.update(**by_datetime)
        if by_author:
            self.by_author.update(**by_author)

    def _transform_attrs(self):
        d = {}
        for k, v in self.__dict__.items():
            if k == "channel":
                d[k] = v.id
            elif k == "last_indexed":
                d[k] = v.timestamp()
            else:
                d[k] = v
        return d

    @property
    def loaded(self):
        return len(self.messages) != 0
