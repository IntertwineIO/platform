#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
Authentication application for website.
'''
from flask import Blueprint
from flask.ext.login import LoginManager
from flask.ext.sqlalchemy import SQLAlchemy
from flask.ext.security import Security, SQLAlchemyUserDatastore

modname = __name__.split('.')[-1]
blueprint = Blueprint(modname, __name__, template_folder='templates')
login_manager = LoginManager()
auth_db = SQLAlchemy()

# Must come later as we use blueprint in views
from . import views
from . import models

auth_users = SQLAlchemyUserDatastore(auth_db, models.User, models.Role)
security = Security()


@blueprint.record_once
def on_load(state):
    login_manager.init_app(state.app)
    auth_db.init_app(state.app)
    with state.app.app_context():
        auth_db.create_all()
        auth_db.session.commit()
    security.init_app(app=state.app, datastore=auth_users)
