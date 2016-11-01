#!/usr/bin/env python
# -*- coding: utf-8 -*-
from flask import redirect

from . import blueprint


@blueprint.route('/', methods=['GET'])
def render():
    permanent_redirect = 301
    # temporary_redirect = 302
    path = "/communities/homelessness/us/tx/austin"
    return redirect(path, code=permanent_redirect)
