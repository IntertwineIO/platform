#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
Base platform for intertwine.

'''
import flask
from flask.ext.bootstrap import Bootstrap
from flask.ext.debugtoolbar import DebugToolbarExtension

import intertwine.auth
import intertwine.main
import intertwine.problems
import intertwine.signup

###############################################################################
__title__ = 'intertwine'
__version__ = '0.1.0-dev'
__author__ = 'Intertwine'
__email__ = 'engineering@intertwine.io'
__license__ = 'Proprietary:  All rights reserved'
__copyright__ = 'Copyright 2015, 2016 - Intertwine'
__url__ = 'https://github.com/IntertwineIO/platform.git'
__shortdesc__ = "Untangle the world's problems"


###############################################################################


toolbar = DebugToolbarExtension()


def create_app(config):
    '''Creates an app

    >>> from intertwine import create_app
    >>> from config import DevConfig
    >>> app = create_app(DevConfig)
    >>> app.run()
    '''
    app = flask.Flask(__name__, static_folder='static', static_url_path='')
    app.config.from_object(config)
    if app.config['DEBUG']:
        app.config['SQLALCHEMY_ECHO'] = True
        app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = True

    # We are using bootstrap for now
    Bootstrap(app)

    # Register all of the blueprints
    app.register_blueprint(intertwine.main.blueprint, url_prefix='/')
    app.register_blueprint(intertwine.auth.blueprint, url_prefix='/auth')
    app.register_blueprint(intertwine.signup.blueprint, url_prefix='/signup')

    if app.config['DEBUG']:
        toolbar.init_app(app)

    return app
