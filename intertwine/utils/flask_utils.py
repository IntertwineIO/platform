#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

from flask import request


def json_requested():
    '''
    JSON requested

    Why check if json has a higher quality than HTML and not just go
    with the best match? Because some browsers accept on */* and we
    don't want to deliver JSON to an ordinary browser.

    This snippet by Armin Ronacher can be used freely for anything you
    like. Consider it public domain.
    '''
    accept_mimetypes = request.accept_mimetypes
    best = accept_mimetypes.best_match(['application/json', 'text/html'])
    return (best == 'application/json' and
            accept_mimetypes[best] > accept_mimetypes['text/html'])
