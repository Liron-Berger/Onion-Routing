import os

XML_LAYOUT = (
    '<Statistics>'
        '<connection_number>%s</connection_number>'
        '%s'
    '</Statistics>'
)

CONNECTION_BLOCK_LAYOUT = (
    '<connection>'
        '<num>%s</num>'
        '<server>%s</server>'
        '<in>%s</in>'
        '<partner>%s</partner>'
        '<out>%s</out>'
    '</connection>'
)

class XML(object):
    def __init__(
        self,
        path,
        connections,
    ):
        self._path = path
        self._fd = os.open(path, os.O_RDWR)
        self._connections = connections
        
    def close(self):
        os.close(self._fd)
        
    def update(
        self,
    ):
        os.lseek(self._fd, 0, os.SEEK_SET)
        os.write(self._fd, " "*os.stat(self._path).st_size)
        os.lseek(self._fd, 0, os.SEEK_SET)

        connections = ""
        for c in self._connections:
            connections += CONNECTION_BLOCK_LAYOUT % (
                c.fileno(),
                self._connections[c]["in"]["fd"],
                self._connections[c]["in"]["bytes"],
                self._connections[c]["out"]["fd"],
                self._connections[c]["out"]["bytes"],
            )
        xml = XML_LAYOUT % (
            len(self._connections),
            connections,
        )

        os.write(self._fd, xml)
