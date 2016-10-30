#!/usr/bin/env python
# -*- coding: utf-8 -*-
from flask_script import Manager

from . import create_app


def web():
    app = create_app()
    manager = Manager(app)

    manager.run()
