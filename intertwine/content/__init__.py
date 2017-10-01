#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

from flask import Blueprint
from alchy import Manager
from alchy.model import extend_declarative_base

from . import models


modname = __name__.split('.')[-1]
blueprint = Blueprint(modname, __name__, template_folder='templates',
                      static_folder='static')

content_db = Manager(Model=models.BaseContentModel)

# Attach query property to BaseProblemModel
extend_declarative_base(models.BaseContentModel, session=content_db.session)

# Must come later as we use blueprint and query property in views
from . import views


@blueprint.record_once
def on_load(state):
    # Set up database tables
    content_db.config.update(state.app.config)
    content_db.create_all()
