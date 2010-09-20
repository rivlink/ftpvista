import const as c
from search_filter import SearchFilterFileTypes
"""
    A file node.
    Used in file tree.
"""

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
        self.bAudio = False;
    
    def getDate(self):
        return self.sDate
    
    def getFilename(self):
        return self.sFilename
    
    def getSpan(self):
        if self.isAudio():
            return (self.sFilename.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;") + "<span class=\"audio_span\"> | <span class=\"audio_label\">Artiste:</span> " + self.sArtist.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;") + " | <span class=\"audio_label\">Album:</span> " + self.sAlbum.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;") + " | <span class=\"audio_label\">Titre:</span> " + self.sTitle.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;") + "</span>")
        else:
            return self.sFilename.replace(">", "&gt;").replace("&", "&amp;").replace("<", "&lt;")
    
    def getSize(self):
        return self.sSize
    
    def getURL(self):
        return self.sURL
    
    def getEscapedURL(self):
        return self.sURL.replace("&", "&amp;")
    
    def getServerURL(self):
        return "ftp://" + self.sFTP
    
    #TODO: Put this in a "config" file
    def getServer(self):
        if (self.sFTP.startswith("10.83.75")):
            return "Tadeus (" + self.sFTP + ")"
        if (self.sFTP.startswith("10.83.49")):
            return "Magne (" + self.sFTP + ")"
        if (self.sFTP.startswith("10.8.39")):
            return "Dustri (" + self.sFTP + ")"
        if (self.sFTP.startswith("10.82.42")):
            return "Boko (" + self.sFTP + ")"
        if (self.sFTP.startswith("10.11.20")):
            return "Zaure (" + self.sFTP + ")"
        return self.sFTP
    
    def isOnline(self):
        return self.bIsOnline
    
    def isAudio(self):
        return self.bAudio
    
    def getSpanClass(self):
        const = SearchFilterFileTypes.getFileType(self.sFilename)
        
        if const == c.OTHERS:
            return c.SPAN_CLASS_OTHERS
        elif const == c.VIDEOS:
            return c.SPAN_CLASS_VIDEOS
        elif const == c.AUDIOS:
            return c.SPAN_CLASS_AUDIOS
        elif const == c.IMAGES:
            return c.SPAN_CLASS_IMAGES
        elif const == c.ARCHIVES:
            return c.SPAN_CLASS_ARCHIVES
        elif const == c.DISKIMAGES:
            return c.SPAN_CLASS_DISKIMAGES

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
        self.bAudio = True;