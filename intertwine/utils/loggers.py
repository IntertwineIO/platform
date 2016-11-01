#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import json
import logging
import sys
from datetime import datetime
from types import FunctionType

import colorama
import pygments
from pygments import highlight
from pygments.style import Style
from pygments.lexers import JsonLexer
from pygments.formatters import Terminal256Formatter, TerminalFormatter


class Unstyled(Style):

    styles = {}


class Solarized256DarkStyle(Style):

    BASE03 = '#002B36'
    BASE02 = '#073642'
    BASE01 = '#586E75'
    BASE00 = '#657B83'
    BASE0 = '#839496'
    BASE1 = '#93A1A1'
    BASE2 = '#EEE8D5'
    BASE3 = '#FDF6E3'
    YELLOW = '#B58900'
    ORANGE = '#CB4B16'
    RED = '#DC322F'
    MAGENTA = '#D33682'
    VIOLET = '#6C71C4'
    BLUE = '#268BD2'
    CYAN = '#2AA198'
    GREEN = '#859900'

    background_color = BASE03

    styles = {
        pygments.token.Keyword: GREEN,
        pygments.token.Keyword.Constant: ORANGE,
        pygments.token.Keyword.Declaration: BLUE,
        pygments.token.Keyword.Namespace: ORANGE,
        pygments.token.Keyword.Reserved: BLUE,
        pygments.token.Keyword.Type: RED,
        pygments.token.Name.Attribute: BASE1,
        pygments.token.Name.Builtin: BLUE,
        pygments.token.Name.Builtin.Pseudo: BLUE,
        pygments.token.Name.Class: BLUE,
        pygments.token.Name.Constant: ORANGE,
        pygments.token.Name.Decorator: BLUE,
        pygments.token.Name.Entity: ORANGE,
        pygments.token.Name.Exception: YELLOW,
        pygments.token.Name.Function: BLUE,
        pygments.token.Name.Tag: BLUE,
        pygments.token.Name.Variable: BLUE,
        pygments.token.String: CYAN,
        pygments.token.String.Backtick: BASE01,
        pygments.token.String.Char: CYAN,
        pygments.token.String.Doc: CYAN,
        pygments.token.String.Escape: RED,
        pygments.token.String.Heredoc: CYAN,
        pygments.token.String.Regex: RED,
        pygments.token.Number: BLUE,
        pygments.token.Operator: BASE1,
        pygments.token.Operator.Word: GREEN,
        pygments.token.Comment: BASE01,
        pygments.token.Comment.Preproc: GREEN,
        pygments.token.Comment.Special: GREEN,
        pygments.token.Generic.Deleted: CYAN,
        pygments.token.Generic.Emph: 'italic',
        pygments.token.Generic.Error: RED,
        pygments.token.Generic.Heading: ORANGE,
        pygments.token.Generic.Inserted: GREEN,
        pygments.token.Generic.Strong: 'bold',
        pygments.token.Generic.Subheading: ORANGE,
        pygments.token.Token: BASE1,
        pygments.token.Token.Other: ORANGE,
    }


class Solarized256Style(Style):
    """
    solarized256
    ------------

    A Pygments style inspired by Solarized's 256 color mode.

    :copyright: (c) 2011 by Hank Gay, (c) 2012 by John Mastro.
    :license: BSD, see LICENSE for more details.

    """
    BASE03 = "#1c1c1c"
    BASE02 = "#262626"
    BASE01 = "#4e4e4e"
    BASE00 = "#585858"
    BASE0 = "#808080"
    BASE1 = "#8a8a8a"
    BASE2 = "#d7d7af"
    BASE3 = "#ffffd7"
    YELLOW = "#af8700"
    ORANGE = "#d75f00"
    RED = "#af0000"
    MAGENTA = "#af005f"
    VIOLET = "#5f5faf"
    BLUE = "#0087ff"
    CYAN = "#00afaf"
    GREEN = "#5f8700"

    background_color = BASE03
    styles = {
        pygments.token.Keyword: GREEN,
        pygments.token.Keyword.Constant: ORANGE,
        pygments.token.Keyword.Declaration: BLUE,
        pygments.token.Keyword.Namespace: ORANGE,
        pygments.token.Keyword.Reserved: BLUE,
        pygments.token.Keyword.Type: RED,
        pygments.token.Name.Attribute: BASE1,
        pygments.token.Name.Builtin: BLUE,
        pygments.token.Name.Builtin.Pseudo: BLUE,
        pygments.token.Name.Class: BLUE,
        pygments.token.Name.Constant: ORANGE,
        pygments.token.Name.Decorator: BLUE,
        pygments.token.Name.Entity: ORANGE,
        pygments.token.Name.Exception: YELLOW,
        pygments.token.Name.Function: BLUE,
        pygments.token.Name.Tag: BLUE,
        pygments.token.Name.Variable: BLUE,
        pygments.token.String: CYAN,
        pygments.token.String.Backtick: BASE01,
        pygments.token.String.Char: CYAN,
        pygments.token.String.Doc: CYAN,
        pygments.token.String.Escape: RED,
        pygments.token.String.Heredoc: CYAN,
        pygments.token.String.Regex: RED,
        pygments.token.Number: CYAN,
        pygments.token.Operator: BASE1,
        pygments.token.Operator.Word: GREEN,
        pygments.token.Comment: BASE01,
        pygments.token.Comment.Preproc: GREEN,
        pygments.token.Comment.Special: GREEN,
        pygments.token.Generic.Deleted: CYAN,
        pygments.token.Generic.Emph: 'italic',
        pygments.token.Generic.Error: RED,
        pygments.token.Generic.Heading: ORANGE,
        pygments.token.Generic.Inserted: GREEN,
        pygments.token.Generic.Strong: 'bold',
        pygments.token.Generic.Subheading: ORANGE,
        pygments.token.Token: BASE1,
        pygments.token.Token.Other: ORANGE,
    }


class CustomFormatter(logging.Formatter):
    '''Modifies the level prefix of the log with the following level
    information:

    !!! - critical
     !  - error
     ?  - warn
        - info
     -  - debug
    '''
    default_prefix = '???'

    color_mapping = {
        logging.CRITICAL: colorama.Fore.MAGENTA,
        logging.ERROR: colorama.Fore.RED,
        logging.WARNING: colorama.Fore.YELLOW,
        logging.DEBUG: colorama.Style.DIM,
    }

    prefix_mapping = {
        logging.CRITICAL: '!!!',
        logging.ERROR: ' ! ',
        logging.WARNING: ' ? ',
        logging.INFO: '   ',
        logging.DEBUG: ' · ',
    }

    def format(self, record):
        # Capture relevant record data
        level = self.prefix_mapping.get(record.levelno) or self.default_prefix
        msg = record.msg
        msecs = datetime.fromtimestamp(record.created).strftime("%Y-%m-%d %H:%M:%S.%f")
        # Setup colors
        color = self.color_mapping.get(record.levelno) or ''
        dim = colorama.Style.DIM
        reset = colorama.Fore.RESET + colorama.Style.RESET_ALL
        name = record.name
        func = record.funcName

        # Setup output
        if '256' in os.environ.get('TERM'):
            formatter = Terminal256Formatter(style=Solarized256DarkStyle)
        else:
            formatter = TerminalFormatter()
        try:
            rmsg = highlight(json.dumps(msg), JsonLexer(), formatter)
        except TypeError:
            pass
        msg = '{color}{level}{reset} {dim}{msecs}|{name}:{func}{reset} {rmsg}'
        data = dict(locals().items())
        msg = msg.format(**data)
        record.msg = msg.rstrip('\n')
        # Dump
        return super(CustomFormatter, self).format(record)


colorama.init()
# logging.basicConfig(level=logging.DEBUG)

formatter = CustomFormatter()
handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(formatter)
handler.level = logging.DEBUG


def log(*dargs, **dkwds):

    dfunc = None
    for arg in dargs:
        if isinstance(arg, FunctionType):
            dfunc = arg
            dargs = list(dargs)
            dargs.pop(0)
            dargs = tuple(dargs)
            break
    info = {}
    if dargs:
        info['dargs'] = dargs
    if dkwds:
        info['dkwds'] = dkwds

    def outer_wrap(*oargs, **okwds):
        if not dfunc:
            oargs = list(oargs)
            func = oargs.pop(0)
            outer_wrap.__doc__ = func.func_doc
            oargs = tuple(oargs)
            func_name = func.__name__
            logger = logging.getLogger(func.__name__)
            logger.level = logging.DEBUG
            logger.addHandler(handler)

            info['func'] = func_name
            if oargs:
                info['oargs'] = oargs
            if okwds:
                info['okwds'] = okwds
            func.func_globals['logger'] = logger

            # when arguments are passed into log, then another wrapper
            #  function is necessary
            def inner_wrap(*iargs, **ikwds):
                if iargs:
                    info['iargs'] = iargs
                if ikwds:
                    info['ikwds'] = ikwds
                rval = func(*iargs, **ikwds)
                if rval:
                    info['returns'] = rval
                logger.info(info)
                return rval

            return inner_wrap

        else:
            func = dfunc
            func_name = func.__name__
            logger = logging.getLogger(func.__name__)
            logger.level = logging.DEBUG
            logger.addHandler(handler)

            func.func_globals['logger'] = logger
            info['func'] = func_name
            if oargs:
                info['oargs'] = oargs
            if okwds:
                info['okwds'] = okwds
            rval = func(*oargs, **okwds)
            if rval:
                info['returns'] = rval
            logger.info(info)
            return rval

    return outer_wrap


def test_log():

    @log
    def foo(bar=None):
        return bar

    @log('dick move')
    def baz(bar=None):
        return bar

    @log(apple='dick move')
    def bak(bar=None):
        return bar

    @log('notta', dick='move')
    def bat(bar=None):
        return bar

    # ----------------------------------------------------------------------
    #  blah
    # ----------------------------------------------------------------------
    foo()
    foo('2')
    foo(bar='3')

    bak()
    bak(4)
    bak(bar='5')

    baz()
    baz(4)
    baz(bar='5')


if __name__ == '__main__':
    test_log()
