# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

# from alchy import Manager
from flask import Blueprint
from flask_sqlalchemy import SQLAlchemy

# from . import models

modname = __name__.split('.')[-1]
blueprint = Blueprint(modname, __name__, template_folder='templates')


# signup_db = Manager(Model=models.BaseSignupModel)
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
