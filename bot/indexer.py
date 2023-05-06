import asyncio
import datetime
from datetime import timedelta
from queue import Queue, Empty

import pytz

from bot.holders import ClientHolder

END = -1


class Indexer:

    def __init__(self, fetcher, saves, date: datetime.datetime):
        self.fetcher = fetcher
        self.savestate = saves

        self.till = date
        self.delta = timedelta(days=1)

        self.input = Queue()

        self.messages = {} if not self.savestate.loaded else self.savestate.messages
        self.by_datetime = {} if not self.savestate.loaded else self.savestate.by_datetime
        self.by_author = {} if not self.savestate.loaded else self.savestate.by_author

    async def index(self, allocated_threads=24):
        """
            TILL: 1st message if not save else last_save
            CURRENT: datetime.now()
        """
        tasks = []
        current = pytz.utc.localize(datetime.datetime.now())
        while current >= (self.till if not self.savestate.loaded else pytz.utc.localize(self.savestate.last_indexed)):
            self.input.put(current)
            current -= self.delta
        for _ in range(min(allocated_threads, self.input.qsize())):
            tasks.append(asyncio.create_task(self.process()))

        [self.input.put(END) for _ in range(min(allocated_threads, self.input.qsize()))]
        await asyncio.gather(*tasks)
        self.dump()

    async def process(self):
        print("Starting process", asyncio.current_task().get_name())
        while True:
            try:
                task = self.input.get()
            except Empty:
                print(f"[Task {asyncio.current_task().get_name()}]", "Queue is empty, awaiting END")
                continue
            self.input.task_done()
            if task == END:
                print(f"[Task {asyncio.current_task().get_name()}]", "Stopping")
                return
            async for message in self.fetcher.fetch(task - self.delta, task):
                if message.author.id != ClientHolder.client.user.id:
                    self.messages[str(message.id)] = (
                        message.created_at.timestamp(), message.author.id, message.content, message.id)

                    if str(message.created_at.date()) not in self.by_datetime:
                        self.by_datetime[str(message.created_at.date())] = []
                    self.by_datetime[str(message.created_at.date())].append(message.id)

                    if str(message.author.id) not in self.by_author:
                        self.by_author[str(message.author.id)] = []
                    self.by_author[str(message.author.id)].append(message.id)

                    print(f"[{asyncio.current_task().get_name()}] Retrieved", message.content, "by", message.author,
                          f"[{len(self.messages)}th message]")

    def dump(self):
        self.savestate.dumpAdd(messages=self.messages, by_datetime=self.by_datetime, by_author=self.by_author)

    def pushMessage(self, message):
        self.messages[str(message.id)] = (
            message.created_at.timestamp(), message.author.id, message.content, message.id)

        author = str(message.author.id)
        date = str(message.created_at.date())

        if date not in self.by_datetime:
            self.by_datetime[date] = []
        self.by_datetime[date].append(message.id)
        if author not in self.by_author:
            self.by_author[author] = []
        self.by_author[author].append(message.id)

        self.savestate.dumpAdd(messages=self.messages, by_datetime=self.by_datetime, by_author=self.by_author)
