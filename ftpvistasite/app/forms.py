from django import forms
import ftpvistasite.app.const as c


class LastForm(forms.Form):
    ft = forms.MultipleChoiceField(choices=(
        (c.VIDEOS, 'Videos'),
        (c.AUDIOS, 'Audios'),
        (c.IMAGES, 'Images'),
        (c.ARCHIVES, 'Archives'),
        (c.DISKIMAGES, 'Images disques')
    ), label='Type de fichiers', widget=forms.SelectMultiple(attrs={'class': 'ft'}))
    os = forms.BooleanField(label='Serveurs online seulement')


class SearchForm(LastForm):
    s = forms.CharField(max_length=100, label='Recherche', widget=forms.TextInput(attrs={'placeholder': 'Recherche'}))
