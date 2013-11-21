# coding: utf-8
# python3
from __future__ import absolute_import, print_function, unicode_literals, division

import re
from jinja2 import evalcontextfilter, Markup, escape

_paragraph_re = re.compile(r'(?:\r\n|\r|\n){2,}')


@evalcontextfilter
def nl2br(eval_ctx, value):
    _paragraph_re = re.compile(r'(?:\r\n|\r(?!\n)|\n){2,}')
    result = u'\n\n'.join(u'%s   ' % p.replace(u'\r\n', u'<br/>') for p in _paragraph_re.split(value))
    if eval_ctx.autoescape:
        result = Markup(result)
    return result


def format_date(value, format='%d.%m.%Y'):
    return value.strftime(format)
