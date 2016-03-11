#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
Main application for website.  Contains default/non-modified views
'''
from flask import Blueprint
from flask_sqlalchemy import SQLAlchemy

modname = __name__.split('.')[-1]
blueprint = Blueprint(modname, __name__, template_folder='templates')


signup_db = SQLAlchemy()

# Must come later as we use blueprint in views
from . import views
from . import models
from . import forms


@blueprint.record_once
def on_load(state):
    signup_db.init_app(state.app)
    with state.app.test_request_context():
        signup_db.create_all()
        signup_db.session.commit()
