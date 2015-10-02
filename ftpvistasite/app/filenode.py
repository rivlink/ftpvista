from . import const as c
from os import path


class FileNode:
    """
    sFTP
    sURL
    sFilename
    sDate
    sSize
    bIsOnline
    bAudio
    """

    def __init__(self, sFTP, sURL, sFilename, sDate, sSize, bIsOnline):
        self.sFTP = sFTP
        self.sURL = sURL
        self.sFilename = sFilename
        self.sDate = sDate
        self.sSize = sSize
        self.bIsOnline = bIsOnline
        self.bAudio = False
        FileNode.correspondences = None

    def getDate(self):
        return self.sDate

    def getFilename(self):
        return self.sFilename

    def getSize(self):
        return self.sSize

    def getURL(self):
        return self.sURL

    def getFolderURL(self):
        return path.dirname(self.sURL)

    def getServerURL(self):
        return "ftp://" + self.sFTP

    def getServer(self):
        return self.sFTP

    def isOnline(self):
        return self.bIsOnline

    def isAudio(self):
        return self.bAudio

    def getIconClass(self):
        root, ext = path.splitext(self.sFilename)
        lext = ext[1:].lower()
        for key in c.EXT:
            if lext in c.EXT[key]:
                return c.SPAN_CLASS[key]
        return c.SPAN_CLASS[str(c.OTHERS)]


class AudioFileNode(FileNode):
    """
    sFTP
    sURL
    sFilename
    sDate
    sSize
    bIsOnline
    sArtist
    sAlbum
    sTitle
    sYear
    bAudio
    """

    def __init__(self, sFTP, sURL, sFilename, sDate, sSize, bIsOnline, sArtist, sAlbum, sTitle, sYear):
        FileNode.__init__(self, sFTP, sURL, sFilename, sDate, sSize, bIsOnline)
        self.sArtist = sArtist
        self.sAlbum = sAlbum
        self.sTitle = sTitle
        self.sYear = sYear
        self.bAudio = True

    def getArtist(self):
        return self.sArtist

    def getAlbum(self):
        return self.sAlbum

    def getTitle(self):
        return self.sTitle

    def getYear(self):
        return self.sYear
