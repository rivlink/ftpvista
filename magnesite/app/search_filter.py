import app.const as c
import re

class SearchFilter:
    """
    searchFilterFileTypes
    """
    
    def __init__(self, fileType):
        self.searchFilterFileTypes = SearchFilterFileTypes()

class SearchFilterFileType:
    """
    const
    sText
    sExtensions
    """
    
    """
        Constructor
    """
    def __init__(self, const, sText, sExtensions):
        self.const = const
        self.sText = sText
        self.setExtensions(sExtensions)
        self.selected = True
    
    def getText(self):
        return self.sText
    
    def setText(self, sText):
        self.sText = sText
    
    def getExtensions(self):
        return self.sExtensions
    
    def getValue(self):
        return self.const
    
    def isSelected(self):
        return self.selected
    
    def setSelected(self, select_state):
        self.selected = select_state
    
    def setExtensions(self, sExtensions = None):
        if (sExtensions is None):
            self.sExtensions = "/*/"
        else:
            self.sExtensions = sExtensions

"""
    Represent all elements used in the filter  : "Search by type"
"""
class SearchFilterFileTypes:
    """
        static
    """
    
    aSearchFilterFileType = None

    """
    Initialize aSearchFilterFileType array
    """
    def init(self):
        SearchFilterFileTypes.aSearchFilterFileType = []
        """
        SearchFilterFileTypes.aSearchFilterFileType.append(SearchFilterFileType(
                c.OTHERS,
                u"Autres",
                u'.*'
        ))
        """
        SearchFilterFileTypes.aSearchFilterFileType.append(SearchFilterFileType(
                c.VIDEOS,
                u"Videos",
                u'\.(avi|mkv|mp4|mov|wmv|3gp(2){0,1}|amv|asf|divx|m4v|movie|mpe(g){0,1}|mpg(2){0,1}|ogm|qt|rm(vb){0,1})$'
        ))
        SearchFilterFileTypes.aSearchFilterFileType.append(SearchFilterFileType(
                c.AUDIOS,
                u"Audios",
                u'\.(mp(2|3)|wma|cda|ogg|flac|aac|aiff|m4a|ra(m){0,1}|wav(e){0,1})$'
        ))
        SearchFilterFileTypes.aSearchFilterFileType.append(SearchFilterFileType(
                c.IMAGES,
                u"Images",
                u'\.(jp(e){0,1}g|gif|png|bmp|tiff|psd)$'
        ))
        SearchFilterFileTypes.aSearchFilterFileType.append(SearchFilterFileType(
                c.ARCHIVES,
                u"Archives",
                u'\.(rar|tar|tgz|tz|yz|zz|xz|war|jar|ace|zip|7z|gz(ip){0,1}|bz(ip){0,1}(2){0,1}|r(\d){1,}|deb|rpm)$'
        ))
        SearchFilterFileTypes.aSearchFilterFileType.append(SearchFilterFileType(
                c.DISKIMAGES,
                u"Images disques",
                u'\.(iso|bin|cue|img|md(s|f))$'
        ))
    
    """
    Return a constant corresponding to the filetype of the given path
    
    @param sPath: Path from which the type will be given
    @return: int
    """
    def getFileType(self, sPath):
        aSearchFilterFileType = SearchFilterFileTypes.getFileTypes()
        
        for searchFilterFileType in reversed(aSearchFilterFileType):
            if re.search(searchFilterFileType.getExtensions(), sPath, re.I) != None:
                return searchFilterFileType.getValue()
        return aSearchFilterFileType[0].getValue()
    
    """
    If not, initialize aSearchFilterFileType array, and then return it
    """
    def getFileTypes(self, filter_list=None):
        if (SearchFilterFileTypes.aSearchFilterFileType == None):
            SearchFilterFileTypes.init()
        if filter_list is not None:
            for filter in SearchFilterFileTypes.aSearchFilterFileType:
                if filter_list.count(str(filter.getValue())) == 1:
                    filter.setSelected(True)
                else:
                    filter.setSelected(False)
        return SearchFilterFileTypes.aSearchFilterFileType
    
    """
        static methods
    """
    getFileTypes = classmethod(getFileTypes)
    getFileType = classmethod(getFileType)
    init = classmethod(init)
    
    