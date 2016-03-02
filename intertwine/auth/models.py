#!/usr/bin/env python
# -*- coding: utf-8 -*-
from flask.ext.security import UserMixin, RoleMixin

from . import login_manager
from . import auth_db


roles_users = auth_db.Table(
    'roles_users',
    auth_db.Column('user_id', auth_db.Integer(), auth_db.ForeignKey('users.id')),
    auth_db.Column('role_id', auth_db.Integer(), auth_db.ForeignKey('roles.id'))
)


class Role(auth_db.Model, RoleMixin):
    '''Allows users to have different roles'''

    __tablename__ = 'roles'

    id = auth_db.Column(auth_db.Integer, primary_key=True)
    name = auth_db.Column(auth_db.String, unique=True)
    description = auth_db.Column(auth_db.String)

    def __init__(self, name, description='', permissions=None):
        self.name = name
        self.description = description

    def __repr__(self):
        cname = self.__class__.__name__
        string = '<{cname} {name}>'.format(
            cname=cname,
            name=self.name
            )
        return string


class User(auth_db.Model, UserMixin):
    '''Basic user model'''

    __tablename__ = 'users'

    # TODO: Replace this with something real
    user_database = {
        'admin': ('admin', 'admin'),
        'guest': ('guest', 'guest')
    }

    id = auth_db.Column(auth_db.Integer, primary_key=True)
    display_name = auth_db.Column(auth_db.String)
    email = auth_db.Column(auth_db.String, unique=True)
    username = auth_db.Column(auth_db.String, unique=True)
    password = auth_db.Column(auth_db.String)
    active = auth_db.Column(auth_db.Boolean())
    confirmed_at = auth_db.Column(auth_db.DateTime())
    roles = auth_db.relationship(
        'Role',
        secondary=roles_users,
        backref=auth_db.backref('users', lazy='dynamic')
    )

    def __init__(self, username, password, email):
        self.password = password
        self.email = email
        self.username = username

    @classmethod
    def get(cls, id):
        return cls.user_database.get(id)

    def __repr__(self):
        cname = self.__class__.__name__
        name = ':{} "{}"'.format(self.username, self.display_name)
        string = '<{cname}{name}>'.format(
            cname=cname,
            name=name
            )
        return string


@login_manager.request_loader
def load_user(request):
    token = request.headers.get('Authorization')
    if token is None:
        token = request.args.get('token')

    if token is not None:
        username, password = token.split(":")  # naive token
        user_entry = User.get(username)
        if (user_entry is not None):
            user = User(username=user_entry[0], password=user_entry[1])
            if (user.password == password):
                return user
