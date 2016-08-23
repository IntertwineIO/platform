#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
Community database
'''
from flask import Blueprint
from alchy import Manager
from alchy.model import extend_declarative_base

from . import models


modname = __name__.split('.')[-1]
blueprint = Blueprint(modname, __name__, template_folder='templates',
                      static_folder='static')

community_db = Manager(Model=models.BaseCommunityModel)

# Attach query property to base model
extend_declarative_base(models.BaseCommunityModel,
                        session=community_db.session)

# Must come later as we use blueprint and query property in views
from . import views  # TODO: uncomment once view exists


@blueprint.record_once
def on_load(state):
    # Sets up database tables
    community_db.config.update(state.app.config)
    community_db.create_all()
