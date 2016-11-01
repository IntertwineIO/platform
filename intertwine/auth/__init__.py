# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from flask import Blueprint
from flask_login import LoginManager
from flask_security import Security, SQLAlchemyUserDatastore
from alchy import Manager
from alchy.model import extend_declarative_base


modname = __name__.split('.')[-1]
blueprint = Blueprint(modname, __name__, template_folder='templates')
login_manager = LoginManager()

# Must come later as we use blueprint and query property in views
from . import views
# Must come later as we use login_manager in models
from . import models

# Attach to the database
auth_db = Manager(Model=models.BaseAuthModel)

# Attach query property to BaseProblemModel
extend_declarative_base(models.BaseAuthModel, session=auth_db.session)

# Setup Flask Login/Security
auth_users = SQLAlchemyUserDatastore(auth_db, models.User, models.Role)
security = Security()


@blueprint.record_once
def on_load(state):
    login_manager.init_app(state.app)
    # config=DevConfig,
    auth_db.config.update(state.app.config)
    auth_db.create_all()
    security.init_app(app=state.app, datastore=auth_users)
