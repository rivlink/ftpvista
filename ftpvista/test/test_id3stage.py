from ftpvista.index import FetchID3TagsStage
from ftpvista import tinytag
import os
from os.path import join, getsize, relpath


class TestFetchID3TagsStage(FetchID3TagsStage):

    def _fetch_range(self, arange):
        super(TestFetchID3TagsStage, self)._fetch_range(arange)
        value = self._buffer.getvalue()
        l = len(value)
        m = min(l, 20)
        s = ''
        if l > m:
            s = '...'
        print('\t{} : {}{}'.format(arange, value[0:m], s))


def test(server, path):
    stage = TestFetchID3TagsStage(server)
    for root, _, files in os.walk(path):
        for name in files:
            if name.lower().endswith('.mp3'):
                filepath = join(root, name)
                size = getsize(filepath)
                rpath = '/' + relpath(filepath, path)
                print(rpath)
                stage._fetch_data(rpath, size)
                try:
                    tags = tinytag.ID3(stage._buffer, None)
                    tags.load(tags=True, duration=False, image=False)
                    print('\t' + str(tags))
                except Exception as e:
                    print('\t', e)
