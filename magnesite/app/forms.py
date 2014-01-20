from django import forms
import app.const as c

class SearchForm(forms.Form):
    s = forms.CharField(max_length=100)
    ft = forms.MultipleChoiceField(choices=(
        (c.VIDEOS, u'Videos'),
        (c.AUDIOS, u'Audios'),
        (c.IMAGES, u'Images'),
        (c.ARCHIVES, u'Archives'),
        (c.DISKIMAGES, u'Images disques')
    ), label=u'Type de fichiers', widget=forms.SelectMultiple(attrs={'class':'ft'}))
    os = forms.BooleanField(label=u'Serveurs online seulement')

