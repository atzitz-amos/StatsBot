import discord


class Fetcher:

    def __init__(self, channel: discord.TextChannel):
        self.channel = channel

    def fetch(self, start, end):
        print("Fetching...", start, end)
        while True:
            try:
                return self.channel.history(limit=None, before=end, after=start)
            except WindowsError:
                continue
