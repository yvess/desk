import re
from jinja2 import pass_eval_context
from jinja2.utils import markupsafe 

_paragraph_re = re.compile(r'(?:\r\n|\r|\n){2,}')


@pass_eval_context
def nl2br(eval_ctx, value):
    _paragraph_re = re.compile(r'(?:\r\n|\r(?!\n)|\n){2,}')
    result = '\n\n'.join('%s   ' % p.replace('\r\n', '<br/>') for p in _paragraph_re.split(value))
    if eval_ctx.autoescape:
        result = markupsafe.Markup(result)
    return result


def format_date(value, format='%d.%m.%Y'):
    return value.strftime(format)
