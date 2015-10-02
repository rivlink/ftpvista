OTHERS = 0
VIDEOS = 1
AUDIOS = 2
IMAGES = 3
ARCHIVES = 4
DISKIMAGES = 5

# Classes
SPAN_CLASS = {}
SPAN_CLASS[str(OTHERS)] = "icon-file"
SPAN_CLASS[str(VIDEOS)] = "icon-video"
SPAN_CLASS[str(AUDIOS)] = "icon-music"
SPAN_CLASS[str(IMAGES)] = "icon-image"
SPAN_CLASS[str(ARCHIVES)] = "icon-archive"
SPAN_CLASS[str(DISKIMAGES)] = "icon-diskimage"

# Extensions categories
EXT = {}
EXT[str(VIDEOS)] = ['avi', 'mpg', 'mkv', 'wmv', 'mp4', 'mov', '3gp', '3gp2', 'mpeg', 'mpg', 'mpg2', 'ogm']
EXT[str(AUDIOS)] = ['mp3', 'wma', 'cda', 'ogg', 'flac', 'aac', 'aiff', 'm4a', 'wav']
EXT[str(IMAGES)] = ['jpep', 'jpg', 'gif', 'png', 'bmp', 'tiff', 'psd']
EXT[str(DISKIMAGES)] = ['iso', 'bin', 'cue', 'img', 'mds', 'mdf', 'nrg']
EXT[str(ARCHIVES)] = ['rar', 'tar', 'tgz', 'tz', 'yz', 'zz', 'xz', 'war', 'jar', 'ace', 'zip', '7z', 'gz', 'gzip', 'bz', 'bzip', 'bz2', 'bzip2', 'r00', 'r01', 'deb', 'rpm']
