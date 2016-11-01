# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

import flask
from flask import render_template

from . import blueprint


@blueprint.route('/login', defaults={'user': 'Unknown'}, methods=['POST', 'GET'])
@blueprint.route('/login/<user>', methods=['POST', 'GET'])
def login(user):
    '''Logs user in'''
    return user


@blueprint.route('/logout', defaults={'user': 'Unknown'}, methods=['GET'])
def logout(user):
    '''Logs user out'''
    return user


@blueprint.route('/', methods=['GET'])
def render():
    '''Generic page rendering for top level'''
    template = render_template(
        'sign-in.html',
        current_app=flask.current_app,
        title="Login")
    return template
