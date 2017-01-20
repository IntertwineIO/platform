#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
Base platform for intertwine.

'''
import flask
from alchy import Manager
from alchy.model import extend_declarative_base, make_declarative_base
from flask_bootstrap import Bootstrap

from .bases import BaseIntertwineMeta, BaseIntertwineModel
from .__metadata__ import *  # noqa

# from . import demo
# from sassutils.wsgi import SassMiddleware


# Set up base model and database connection, and attach query property
IntertwineModel = make_declarative_base(Base=BaseIntertwineModel,
                                        Meta=BaseIntertwineMeta)

intertwine_db = Manager(Model=IntertwineModel)
extend_declarative_base(IntertwineModel, session=intertwine_db.session)

from . import auth, communities, geos, main, problems, signup  # noqa


def create_app(name=None, config=None):
    '''Creates an app based on a config file

    Args:
        config: Configuration

    Returns:
        Flask: a Flask app

    >>> from intertwine import create_app
    >>> from config import DevConfig
    >>> app = create_app(config=DevConfig)
    >>> app.run()
    '''
    name = name or __name__
    app = flask.Flask(name, static_folder='static', static_url_path='')
    if config is None:
        config = {}
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
    app.register_blueprint(auth.blueprint, url_prefix='/login')
    app.register_blueprint(signup.blueprint, url_prefix='/signup')
    app.register_blueprint(problems.blueprint, url_prefix='/problems')
    app.register_blueprint(geos.blueprint, url_prefix='/geos')
    app.register_blueprint(communities.blueprint, url_prefix='/communities')

    # app.url_map.strict_slashes = False
    # app.register_blueprint(demo.blueprint, url_prefix='/demo')

    # Auto-build SASS/SCSS for each request
    # app.wsgi_app = SassMiddleware(app.wsgi_app, {
    #     __name__: ('problems/static/sass', 'problems/static/css', 'problems/static/css')
    # })

    # if app.config['DEBUG']:
    #     toolbar.init_app(app)

    return app
