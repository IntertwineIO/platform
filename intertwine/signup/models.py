# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

import datetime

from . import signup_db


class SignUp(signup_db.Model):

    __tablename__ = 'signup'

    id = signup_db.Column(signup_db.Integer, primary_key=True)
    email = signup_db.Column(signup_db.String, unique=True)
    username = signup_db.Column(signup_db.String, unique=True)
    timestamp = signup_db.Column(signup_db.DateTime)

    def __init__(self, email, username):
        self.email = email
        self.username = username
        self.timestamp = datetime.datetime()

    def __repr__(self):
        cname = self.__class__.__name__
        string = '<{cname} {username} {email}>'.format(
            cname=cname,
            username=self.username,
            email=self.email
            )
        return string
