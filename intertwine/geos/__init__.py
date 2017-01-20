# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from flask import Blueprint
from alchy import Manager
from alchy.model import extend_declarative_base

from . import models


modname = __name__.split('.')[-1]
blueprint = Blueprint(modname, __name__, template_folder='templates',
                      static_folder='static')

geo_db = Manager(Model=models.BaseGeoModel)

# Attach query property to base model
extend_declarative_base(models.BaseGeoModel, session=geo_db.session)

# Must come later as we use blueprint and query property in views
from . import views  # noqa


@blueprint.record_once
def on_load(state):
    # Sets up database tables
    geo_db.config.update(state.app.config)
    geo_db.create_all()
