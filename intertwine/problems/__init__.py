#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

from flask import Blueprint
from alchy import Manager
from alchy.model import extend_declarative_base

from . import models

blueprint = Blueprint(models.Problem.blueprint_name(), __name__,
                      template_folder='templates', static_folder='static')

problem_db = Manager(Model=models.BaseProblemModel)

# Attach query property to BaseProblemModel
extend_declarative_base(models.BaseProblemModel, session=problem_db.session)

# Must come later as we use blueprint and query property in views
from . import views


@blueprint.record_once
def on_load(state):
    # Set up database tables
    problem_db.config.update(state.app.config)
    problem_db.create_all()
