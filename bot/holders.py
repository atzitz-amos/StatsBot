class IndexingHolder:
    indexes = {}

    @staticmethod
    def fromChannel(channel):
        return IndexingHolder.indexes[channel.guild.id][channel.id]


class ClientHolder:
    client = None


class FilenameCounterHolder:
    counter = 0
