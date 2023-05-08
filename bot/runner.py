import time

import discord

from bot import saves
from bot.fetcher import Fetcher
from bot.holders import IndexingHolder, ClientHolder
from bot.indexer import Indexer
from bot.processor import TriggerProcessor

bot = discord.Bot(intents=discord.Intents.all())


@bot.event
async def on_ready():
    ClientHolder.client = bot
    guild = bot.guilds[0]
    print(guild)
    results = {}

    for channel in guild.channels:
        perf = time.perf_counter()
        if not isinstance(channel, discord.TextChannel):
            continue
        try:
            save = await saves.load(
                f"saves/guild-{str(guild).replace(' ', '_')}/channel-{str(channel).replace(' ', '_')}.save")
            print("Found save file on", save.last_indexed)
        except Exception:
            save = saves.SaveState(channel)

        async for msg in channel.history(limit=1, oldest_first=True):
            index = Indexer(Fetcher(channel), save, msg.created_at)
            await index.index()
            results[channel.id] = index
            print("Indexing on channel", channel, "has completed in",
                  time.perf_counter() - perf, "seconds"
                                              ". Retrieved", len(index.messages), "messages.")
    IndexingHolder.indexes[guild.id] = results
    print("Indexing has completed")


@bot.event
async def on_message(msg):
    if msg.author.id == bot.user.id:
        return
    IndexingHolder.fromChannel(msg.channel).pushMessage(msg)

    await TriggerProcessor.invoke(msg.channel, msg.content)


bot.run("MTEwMjMwMzU3NTc2MzMyOTA4Ng.GlIb5w.RqCM3sl80f8V1gSnIrQgs7aRGWYDgWRVAWq3nI")
