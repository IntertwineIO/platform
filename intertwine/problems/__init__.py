#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
Problems for database.
'''
from flask import Blueprint
from flask.ext.sqlalchemy import SQLAlchemy

modname = __name__.split('.')[-1]
blueprint = Blueprint(modname, __name__, template_folder='templates',
                      static_folder='static')
problems_db = SQLAlchemy()

# Must come later as we use blueprint in views
from . import views
from . import models


@blueprint.record_once
def on_load(state):
    # Sets up problems database tables
    problems_db.init_app(state.app)
    with state.app.app_context():
        models.BaseProblemModel.metadata.create_all(bind=problems_db.engine)
        problems_db.session.commit()
