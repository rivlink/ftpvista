from django import template
from django.utils.translation import ugettext, ungettext

register = template.Library()

@register.filter
def filesizeformat2(bytes):
    try:
        bytes = float(bytes)
    except (TypeError,ValueError,UnicodeDecodeError):
        return "0 octets"

    if bytes < 1024:
        return ungettext("%(size)d octet", "%(size)d octets", bytes) % {'size': bytes}
    if bytes < 1048576: # 1024 * 1024
        return ugettext("%.1f Ko") % (bytes / 1024)
    if bytes < 1073741824: # 1024 * 1024 * 1024
        return ugettext("%.1f Mo") % (bytes / (1048576)) # 1024 * 1024
    if bytes < 1099511627776: # 1024 * 1024 * 1024 * 1024
        return ugettext("%.1f Go") % (bytes / (1073741824)) # 1024 * 1024 * 1024
    return ugettext("%.1f To") % (bytes / (1099511627776)) # 1024 * 1024 * 1024 * 1024
filesizeformat2.is_safe = True