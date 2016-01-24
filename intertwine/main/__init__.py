#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
Main application for website.  Contains default/non-modified views
'''
from flask import Blueprint

modname = __name__.split('.')[-1]
blueprint = Blueprint(modname, __name__, template_folder='templates')

# Must come later as we use blueprint in views
from . import views
