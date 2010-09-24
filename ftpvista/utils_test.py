# -*- coding: utf-8 -*-


from utils import *
import chardet

strings = ['', u'', 'bleh', u'bleh', '(les 7 jours de P\xc3\xa9ki)n',
           u'Micka\xebl the turtle', u'Aupr\xe8s de mon arbre']


#print u'Aupr\xe8s de mon arbre'.encode('utf_8')
for s in strings:
    #encoding_guess = chardet.detect(s)
    #print('decoding (%s,%f)' % (encoding_guess['encoding'],
                                #encoding_guess['confidence']))
    #print unicode(s,"unicode_escape" ).encode('utf-8')
    print (decode_text(s))
