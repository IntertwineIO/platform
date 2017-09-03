#!/usr/bin/env python
# -*- coding: utf8 -*-

"""
urlnorm.py - URL normalization routines

urlnorm normalizes a URL by:
  * lowercasing the scheme and hostname
  * converting the hostname to IDN format
  * taking out default port if present (e.g., http://www.foo.com:80/)
  * collapsing the path (./, ../, //, etc)
  * removing the last character in the hostname if it is '.'
  * unescaping any percent escape sequences (where possible)
  * uppercase percent escape (ie: %3f => %3F)
  * converts spaces to %20
  * converts ip encoded as an integer to dotted quad notation

Available functions:
  norm - given a URL (string), returns a normalized URL
  norm_netloc
  norm_path
  unquote_path
  unquote_params
  unquote_qs
  unquote_fragment


CHANGES:
1.1.5 - Now works with python 3.5
1.1.4 - unescape " " in params, query string, and fragments
1.1.3 - don't escape " " in path
1.1.2 - leave %20 as %20, collate ' ' to %20, leave '+' as '+'
1.1 - collate %20 and ' ' to '+'
1.1 - fix unescaping of parameters
1.1 - added int2ip
1.0.1 - fix problem unescaping %23 and %20 in query string
1.0 - new release
0.94 - idna handling, unescaping querystring, fragment, add ws + wss ports
0.92 - unknown schemes now pass the port through silently
0.91 - general cleanup
     - changed dictionaries to lists where appropriate
     - more fine-grained authority parsing and normalisation
"""
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import re
import sys

try:
    from urllib.parse import urlparse, urlunparse
except ImportError:
    from urlparse import urlparse, urlunparse


__license__ = """
Copyright (c) 1999-2002 Mark Nottingham <mnot@pobox.com>
Copyright (c) 2010 Jehiah Czebotar <jehiah@gmail.com>

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

# also update in setup.py
__version__ = "1.1.5"

# Python version compatibilities
if sys.version_info < (3,):
    bytes = str

    def b(x):
        return x

else:
    unicode = str
    unichr = chr

    def b(x):
        return x.encode("utf-8")


class InvalidUrl(Exception):
    pass


_server_authority = re.compile('^(?:([^\@]+)\@)?([^\:\[\]]+|\[[a-fA-F0-9\:\.]+\])(?:\:(.*?))?$')
_default_port = {'http': '80',
                 'itms': '80',
                 'ws': '80',
                 'https': '443',
                 'wss': '443',
                 'gopher': '70',
                 'news': '119',
                 'snews': '563',
                 'nntp': '119',
                 'snntp': '563',
                 'ftp': '21',
                 'telnet': '23',
                 'prospero': '191',
                 }
_relative_schemes = set(['http',
                         'https',
                         'ws',
                         'wss',
                         'itms',
                         'news',
                         'snews',
                         'nntp',
                         'snntp',
                         'ftp',
                         'file',
                         ''
                         ])

params_unsafe_list = set('?=+%#;')
qs_unsafe_list = set('?&=+%#')
fragment_unsafe_list = set('+%#')
path_unsafe_list = set('/?;%+#')
_hextochr = dict(('%02x' % i, chr(i)) for i in range(256))
_hextochr.update(('%02X' % i, chr(i)) for i in range(256))


def unquote_path(s):
    return unquote_safe(s, path_unsafe_list)


def unquote_params(s):
    return unquote_safe(s, params_unsafe_list)


def unquote_qs(s):
    return unquote_safe(s, qs_unsafe_list)


def unquote_fragment(s):
    return unquote_safe(s, fragment_unsafe_list)


def unquote_safe(s, unsafe_list):
    """unquote percent escaped string except for percent escape sequences that are in unsafe_list"""
    # note: this builds utf8 raw strings, then does a .decode('utf8') at the end.
    # as a result it's doing .encode('utf8') on each block of the string as it's processed.
    res = _utf8(s).split(b('%'))
    for i in range(1, len(res)):
        item = res[i]
        try:
            raw_chr = _hextochr[item[:2]]
            if raw_chr in unsafe_list or ord(raw_chr) < 20:
                # leave it unescaped (but uppercase the percent escape)
                res[i] = b('%') + item[:2].upper() + item[2:]
            else:
                res[i] = raw_chr + item[2:]
        except KeyError:
            res[i] = b('%') + item
        except UnicodeDecodeError:
            # note: i'm not sure what this does
            res[i] = unichr(int(item[:2], 16)) + item[2:]
    o = b('').join(res)
    return _unicode(o)


def norm(url):
    """given a string URL, return its normalized/unicode form"""
    url = _unicode(url)  # operate on unicode strings
    url_tuple = urlparse(url)
    normalized_tuple = norm_tuple(*url_tuple)
    return urlunparse(normalized_tuple)


def norm_tuple(scheme, netloc, path, parameters, query, fragment):
    """given individual url components, return its normalized form"""
    scheme = str(scheme).lower()
    if not scheme:
        raise InvalidUrl('missing URL scheme')
    netloc = norm_netloc(scheme, netloc)
    if not netloc:
        raise InvalidUrl('missing netloc')
    path = norm_path(scheme, path)
    # TODO: put query in sorted order; or at least group parameters together
    # Note that some websites use positional parameters or the name part of a query so this would break the internet
    # query = urlencode(parse_qs(query, keep_blank_values=1), doseq=1)
    parameters = unquote_params(parameters)
    query = unquote_qs(query)
    fragment = unquote_fragment(fragment)
    return (scheme, netloc, path, parameters, query, fragment)


def norm_path(scheme, path):
    if scheme in _relative_schemes:
        # resolve `/../` and `/./` and `//` components in path as appropriate
        i = 0
        parts = []
        start = 0
        while i < len(path):
            if path[i] == "/" or i == len(path) - 1:
                chunk = path[start:i + 1]
                start = i + 1
                if chunk in ["", "/", ".", "./"]:
                    # do nothing
                    pass
                elif chunk in ["..", "../"]:
                    if len(parts):
                        parts = parts[:len(parts) - 1]
                    else:
                        parts.append(chunk)
                else:
                    parts.append(chunk)
            i += 1
        path = "/" + ("".join(parts))
    path = unquote_path(path)
    if not path:
        return '/'
    return path


def int2ip(ipnum):
    assert isinstance(ipnum, int)
    ip1 = ipnum >> 24
    ip2 = ipnum >> 16 & 0xFF
    ip3 = ipnum >> 8 & 0xFF
    ip4 = ipnum & 0xFF
    return "%d.%d.%d.%d" % (ip1, ip2, ip3, ip4)


def norm_netloc(scheme, netloc):
    if not netloc:
        return netloc
    match = _server_authority.match(netloc)
    if not match:
        raise InvalidUrl('no host in netloc %r' % netloc)

    userinfo, host, port = match.groups()
    # catch a few common errors:
    if host.isdigit():
        try:
            host = int2ip(int(host))
        except TypeError:
            raise InvalidUrl('host %r does not escape to a valid ip' % host)
    if host[-1] == '.':
        host = host[:-1]

    # bracket check is for ipv6 hosts
    if '.' not in host and not (host[0] == '[' and host[-1] == ']'):
        raise InvalidUrl('host %r is not valid' % host)

    authority = str(host).lower()
    if 'xn--' in authority:
        subdomains = [_idn(subdomain) for subdomain in authority.split('.')]
        authority = '.'.join(subdomains)

    if userinfo:
        authority = "%s@%s" % (userinfo, authority)
    if port and port != _default_port.get(scheme, None):
        authority = "%s:%s" % (authority, port)
    return authority


def _idn(subdomain):
    if subdomain.startswith('xn--'):
        try:
            subdomain = subdomain.decode('idna')
        except UnicodeError:
            raise InvalidUrl('Error converting subdomain %r to IDN' % subdomain)
    return subdomain


def _utf8(value):
    if isinstance(value, unicode):
        return value.encode("utf-8")
    assert isinstance(value, bytes)
    return value


def _unicode(value):
    if isinstance(value, bytes):
        return value.decode("utf-8")
    assert isinstance(value, unicode)
    return value
