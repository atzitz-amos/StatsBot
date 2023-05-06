import os
import time

import discord.ui
import matplotlib.pyplot as plt
from discord.file import File

from bot.holders import FilenameCounterHolder


def measure(func):
    def _time_it(*args, **kwargs):
        start = int(round(time.time() * 1000))
        return func(*args, **kwargs), int(round(time.time() * 1000)) - start

    return _time_it


@measure
def generateBar(filename, x, y, xlabel="", ylabel="", title=""):
    fig, ax = plt.subplots()

    ax.set(xlabel=xlabel, ylabel=ylabel,
           title=title)
    ax.grid()

    plt.bar(x, y)

    fig.savefig(f"./graphs/{filename}.png")


@measure
def generatePlot(filename, x, y, xlabel="", ylabel="", title=""):
    fig, ax = plt.subplots()

    ax.set(xlabel=xlabel, ylabel=ylabel,
           title=title)
    ax.grid()

    plt.plot(x, y)

    fig.savefig(f"./graphs/{filename}.png")


@measure
def generatePie(filename, values, total, labels):
    sizes = []
    for v in values:
        sizes.append(v / total)

    fig, ax = plt.subplots()

    ax.pie(sizes, explode=[0.01] * len(values), labels=labels, autopct='%1.1f%%',
           shadow=True, startangle=90, labeldistance=1.2)
    ax.axis('equal')

    fig.savefig(f"./graphs/{filename}.png")


async def _sendGraph(channel, embed, filename):
    file = File(f"./graphs/{filename}.png")
    embed.set_image(url=f"attachment://{filename}.png")

    msg = await channel.send(embed=embed, file=file, delete_after=60 * 15)

    os.remove(f"./graphs/{filename}.png")

    return msg


def normalizeFilename(filename, gtype):
    filename += "(" + gtype + ")"
    filename += str(FilenameCounterHolder.counter)
    FilenameCounterHolder.counter += 1
    return filename


async def sendBarGraph(channel, embed, filename, x, y, xlabel="", ylabel="", title=""):
    filename = normalizeFilename(filename, "bar")
    _, exec_time = generateBar(filename, x, y, xlabel, ylabel, title)
    return await _sendGraph(channel, embed, filename)


async def sendPlotGraph(channel, embed, filename, x, y, xlabel="", ylabel="", title=""):
    filename = normalizeFilename(filename, "plot")
    _, exec_time = generatePlot(filename, x, y, xlabel, ylabel, title)
    return await _sendGraph(channel, embed, filename)


async def sendPieGraph(channel, embed, filename, values, total, labels):
    filename = normalizeFilename(filename, "pie")
    _, exec_time = generatePie(filename, values, total, labels)
    return await _sendGraph(channel, embed, filename)


class OverflowView(discord.ui.View):

    def __init__(self, channel, filename, x, y, drange, creator, embed: discord.Embed, kwargs):
        super().__init__()
        self.channel = channel
        self.filename = filename

        self.x = x
        self.y = y

        self.drange = drange
        self.creator = creator

        self.embed = embed

        self.current_range = [0, drange]

        self.page = 0
        self.kwargs = kwargs

    async def send(self):
        filename = normalizeFilename(self.filename, "bar")
        _, exec_time = self.creator(filename, self.x[:self.drange], self.y[:self.drange], **self.kwargs)
        file = File(f"./graphs/{filename}.png")
        self.embed.set_image(url=f"attachment://{filename}.png")

        await self.channel.send(embed=self.embed, file=file, delete_after=60 * 15)

        os.remove(f"./graphs/{filename}.png")

    @discord.ui.button(label="Previous", row=1)
    async def on_previous(self, button, interaction):
        start, end = self.current_range
        self.current_range = [start - self.drange, end - self.drange]
        if self.current_range[0] <= 0:
            self.current_range[0] = 0
            self.current_range[1] = self.drange
            return await interaction.response.edit_message(view=self)
        self.page -= 1
        await self.update(interaction)

    @discord.ui.button(label="Next", disabled=False, row=0)
    async def on_next(self, button, interaction):
        start, end = self.current_range
        self.current_range = [start + self.drange, end + self.drange]
        if self.current_range[1] >= len(self.x):
            self.current_range[0] = len(self.x) - self.drange
            self.current_range[1] = len(self.x)
            return await interaction.response.edit_message(view=self)
        self.page += 1
        await self.update(interaction)

    async def update(self, interaction):
        filename = normalizeFilename(self.filename, "bar")
        start, end = self.current_range

        _, exec_time = self.creator(filename, self.x[start: end + 1], self.y[start: end + 1], **self.kwargs)
        file = File(f"./graphs/{filename}.png")
        self.embed.set_image(url=f"attachment://{filename}.png")

        os.remove(f"./graphs/{filename}.png")

        await interaction.response.edit_message(embed=self.embed, file=file, delete_after=60 * 15, view=self)


D_RANGE = 4


async def overflow(channel, embed, filename, x, y, creator=None, **kw):
    if len(x) < 4:
        return await sendBarGraph(channel, embed, filename, x, y, **kw)
    view = OverflowView(channel, filename, x, y, D_RANGE, creator=creator, **kw)
    await view.send()
