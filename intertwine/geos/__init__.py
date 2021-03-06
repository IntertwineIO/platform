# -*- coding: utf-8 -*-
from flask import Blueprint
from alchy import Manager
from alchy.model import extend_declarative_base

from . import models


blueprint = Blueprint(models.Geo.blueprint_name(), __name__,
                      template_folder='templates', static_folder='static')

geo_db = Manager(Model=models.BaseGeoModel)

# Attach query property to base model
extend_declarative_base(models.BaseGeoModel, session=geo_db.session)

# Must come later as we use blueprint and query property in views
from . import views  # noqa


@blueprint.record_once
def on_load(state):
    # Set up database tables
    geo_db.config.update(state.app.config)
    geo_db.create_all()
