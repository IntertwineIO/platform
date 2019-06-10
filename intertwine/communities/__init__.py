# -*- coding: utf-8 -*-
from flask import Blueprint
from alchy import Manager
from alchy.model import extend_declarative_base

from . import models


blueprint = Blueprint(models.Community.blueprint_name(), __name__,
                      template_folder='templates', static_folder='static')

community_db = Manager(Model=models.BaseCommunityModel)

# Attach query property to base model
extend_declarative_base(models.BaseCommunityModel,
                        session=community_db.session)

# Must come later as we use blueprint and query property in views
from . import views


@blueprint.record_once
def on_load(state):
    # Set up database tables
    community_db.config.update(state.app.config)
    community_db.create_all()
