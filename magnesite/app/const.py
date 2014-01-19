OTHERS = 0
VIDEOS = 1
AUDIOS = 2
IMAGES = 3
ARCHIVES = 4
DISKIMAGES = 5

"""
    Classes
"""
SPAN_CLASS_OTHERS = u"file"
SPAN_CLASS_VIDEOS = u"video"
SPAN_CLASS_AUDIOS = u"music"
SPAN_CLASS_IMAGES = u"image"
SPAN_CLASS_ARCHIVES = u"archive"
SPAN_CLASS_DISKIMAGES = u"diskimage"

"""
    Extensions regex
"""
EXT = {}
EXT[str(VIDEOS)] = [u'avi', u'mpg', u'mkv', u'wmv', u'mp4', u'mov', u'3gp', u'3gp2', u'mpeg', u'mpg', u'mpg2', u'ogm']
EXT[str(AUDIOS)] = [u'mp3', u'wma', u'cda', u'ogg', u'flac', u'aac', u'aiff', u'm4a', u'wav']
EXT[str(IMAGES)] = [u'jpep', u'jpg', u'gif', u'png', u'bmp', u'tiff', u'psd']
EXT[str(DISKIMAGES)] = [u'iso', u'bin', u'cue', u'img', u'mds', u'mdf', u'nrg']
EXT[str(ARCHIVES)] = [u'rar', u'tar', u'tgz', u'tz', u'yz', u'zz', u'xz', u'war', u'jar', u'ace', u'zip', u'7z', u'gz', u'gzip', u'bz', u'bzip', u'bz2', u'bzip2', u'r00', u'r01', u'deb', u'rpm']
