import re
from IPy import IP
import geoip2.database
from django import template
from django.contrib.staticfiles.storage import staticfiles_storage

reader = geoip2.database.Reader(staticfiles_storage.path('data\\GeoLite2-Country.mmdb'))

register = template.Library()

@register.filter(name='duration')
def duration(value, arg=99999999999):
    return ', '.join(
        '%d %s' % (num, unit)
        for num, unit in zip([
            (value // d) % m
            for d, m in (
                (604800, arg),
                (86400, 7), (3600, 24),
                (60, 60), (1, 60))
        ], ['wk', 'd', 'hr', 'min', 'sec'])
        if num
    )


@register.filter(name='country_name')
def get_country_name_for_ip(line):
    ipv4_address = re.compile(r"""
            \b((?:25[0-5]|2[0-4]\d|1\d\d|[1-9]\d|\d)\.
            (?:25[0-5]|2[0-4]\d|1\d\d|[1-9]\d|\d)\.
            (?:25[0-5]|2[0-4]\d|1\d\d|[1-9]\d|\d)\.
            (?:25[0-5]|2[0-4]\d|1\d\d|[1-9]\d|\d))\b""", re.X)
    ip = ipv4_address.findall(line)
    if ip:
        ip = ip[0]  # take the 1st ip and ignore the rest
        if IP(ip).iptype() == 'PUBLIC':
            r = reader.country(ip).country
            if r.iso_code and r.name:
                return r.name


@register.filter(name='country_iso_code')
def get_country_iso_code_for_ip(line):
    ipv4_address = re.compile(r"""
            \b((?:25[0-5]|2[0-4]\d|1\d\d|[1-9]\d|\d)\.
            (?:25[0-5]|2[0-4]\d|1\d\d|[1-9]\d|\d)\.
            (?:25[0-5]|2[0-4]\d|1\d\d|[1-9]\d|\d)\.
            (?:25[0-5]|2[0-4]\d|1\d\d|[1-9]\d|\d))\b""", re.X)
    ip = ipv4_address.findall(line)
    if ip:
        ip = ip[0]  # take the 1st ip and ignore the rest
        if IP(ip).iptype() == 'PUBLIC':
            r = reader.country(ip).country
            if r.iso_code and r.name:
                return r.iso_code.lower()