from django import template
from ftpvistasite.models import Correspondence

register = template.Library()


@register.filter
def ipwithname(ip):
    corresp = Correspondence.getbyip(ip)
    if corresp is None:
        return ip
    return str(corresp)
