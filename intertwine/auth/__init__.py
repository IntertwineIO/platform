#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
Authentication application for website.
'''
from flask import Blueprint
from flask_admin import Admin
from flask_login import LoginManager
from flask_restless import APIManager
from flask_security import Security, SQLAlchemyUserDatastore
from flask_sqlalchemy import SQLAlchemy

modname = __name__.split('.')[-1]
blueprint = Blueprint(modname, __name__, template_folder='templates')
login_manager = LoginManager()
api_manager = APIManager()
auth_db = SQLAlchemy()
admin = Admin()

# Must come later as we use the auth blueprint in auth views
from . import views
from . import models

auth_users = SQLAlchemyUserDatastore(auth_db, models.User, models.Role)
security = Security()


@blueprint.record_once
def on_load(state):
    login_manager.init_app(state.app)
    auth_db.init_app(state.app)
    with state.app.test_request_context():
        auth_db.create_all()
        auth_db.session.commit()
    # Setup security
    security.init_app(app=state.app, datastore=auth_users)
    # Setup endpoints for CRUD
    api_manager.create_api(models.Role, methods=['GET', 'POST', 'DELETE'])
    api_manager.create_api(models.User, methods=['GET', 'POST', 'DELETE'])
    # Setup Admin Views
    admin.add_view(views.MyAdminView(models.Role, auth_db.session))
    admin.add_view(views.MyAdminView(models.User, auth_db.session))
