# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from flask import Blueprint
from alchy import Manager
from alchy.model import extend_declarative_base

from .. import IntertwineModel


modname = __name__.split('.')[-1]
blueprint = Blueprint(modname, __name__, template_folder='templates',
                      static_folder='static')

intertwine_db = Manager(Model=IntertwineModel)

# Attach query property to base model
extend_declarative_base(intertwine_db, session=intertwine_db.session)

# Must come later as we use blueprint and query property in views
from . import views


@blueprint.record_once
def on_load(state):
    # Sets up database tables
    intertwine_db.config.update(state.app.config)
    intertwine_db.create_all()
