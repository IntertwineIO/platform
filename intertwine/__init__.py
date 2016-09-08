#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
Base platform for intertwine.

'''
from alchy import Manager
from alchy.model import (make_declarative_base, extend_declarative_base,
                         ModelBase)
import flask
from flask_bootstrap import Bootstrap
# from sassutils.wsgi import SassMiddleware

from trackable import Trackable

# Set up base model and database connection, and attach query property
BaseIntertwineModel = make_declarative_base(Base=ModelBase, Meta=Trackable)
intertwine_db = Manager(Model=BaseIntertwineModel)
extend_declarative_base(BaseIntertwineModel, session=intertwine_db.session)

from . import auth, communities, geos, main, problems, signup


###############################################################################


__title__ = 'intertwine'
__version_str__ = '0.3.0-dev'
__version__ = tuple((int(v.split('-')[0]) for v in __version_str__.split('.')))
__author__ = 'Intertwine'
__email__ = 'engineering@intertwine.io'
__license__ = 'Proprietary'
__copyright__ = 'Copyright 2015, 2016 - Intertwine'
__url__ = 'https://github.com/IntertwineIO/platform.git'
__shortdesc__ = "Untangle the world's problems"


###############################################################################


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
    #     from flask_debugtoolbar import DebugToolbarExtension
    #     toolbar = DebugToolbarExtension()

    # Auto-build SASS/SCSS for each request
    # app.wsgi_app = SassMiddleware(app.wsgi_app, {
    #     __name__: ('static/sass', 'static/css', 'static/css')
    # })

    # We are using bootstrap for now
    Bootstrap(app)

    # Register all of the blueprints
    app.register_blueprint(main.blueprint, url_prefix='/')
    app.register_blueprint(auth.blueprint, url_prefix='/auth')
    app.register_blueprint(signup.blueprint, url_prefix='/signup')
    app.register_blueprint(problems.blueprint, url_prefix='/problems')
    app.register_blueprint(geos.blueprint, url_prefix='/geos')
    app.register_blueprint(communities.blueprint, url_prefix='/communities')

    # app.url_map.strict_slashes = False

    # Auto-build SASS/SCSS for each request
    # app.wsgi_app = SassMiddleware(app.wsgi_app, {
    #     __name__: ('problems/static/sass', 'problems/static/css', 'problems/static/css')
    # })

    # if app.config['DEBUG']:
    #     toolbar.init_app(app)

    return app
