#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
Problems for database.
'''
from flask import Blueprint
from flask.ext.sqlalchemy import SQLAlchemy

modname = __name__.split('.')[-1]
blueprint = Blueprint(modname, __name__, template_folder='templates')
problems_db = SQLAlchemy()

# Must come later as we use blueprint in views
from . import views
from . import models


@blueprint.record_once
def on_load(state):
    problems_db.init_app(state.app)
    with state.app.test_request_context():
        problems_db.create_all()
        problems_db.session.commit()
