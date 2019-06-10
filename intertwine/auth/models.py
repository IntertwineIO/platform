# -*- coding: utf-8 -*-
from alchy.model import ModelBase, make_declarative_base
from flask_security import UserMixin, RoleMixin
from sqlalchemy import orm, types, Column, ForeignKey, Table

from . import login_manager
from ..bases import AutoTableMixin


BaseAuthModel = make_declarative_base(Base=ModelBase,
                                      # Meta=Trackable
                                      )

roles_users = Table(
    'roles_users',
    BaseAuthModel.metadata,
    Column('user_id', types.Integer(), ForeignKey('users.id')),
    Column('role_id', types.Integer(), ForeignKey('roles.id'))
)


class Role(AutoTableMixin, RoleMixin, BaseAuthModel):
    """Allows users to have different roles"""

    __tablename__ = 'roles'

    id = Column(types.Integer, primary_key=True)
    name = Column(types.String, unique=True)
    description = Column(types.String)

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


class User(AutoTableMixin, UserMixin, BaseAuthModel):
    """Basic user model"""

    __tablename__ = 'users'

    # TODO: Replace this with something real
    user_database = {
        'admin': ('admin', 'admin'),
        'guest': ('guest', 'guest')
    }

    id = Column(types.Integer, primary_key=True)
    display_name = Column(types.String)
    email = Column(types.String, unique=True)
    username = Column(types.String, unique=True)
    password = Column(types.String)
    active = Column(types.Boolean())
    confirmed_at = Column(types.DateTime())
    roles = orm.relationship(
        'Role',
        secondary=roles_users,
        backref=orm.backref('users', lazy='dynamic')
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
