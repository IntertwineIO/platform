#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os


class DefaultDatabaseConfig(object):
    '''Default config for database'''
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite://'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = False


class InMemoryConfig(DefaultDatabaseConfig):
    '''In Memory transient database'''
    DATABASE = 'sqlite://'
    SQLALCHEMY_DATABASE_URI = DATABASE


class SqlLiteConfig(DefaultDatabaseConfig):
    '''Local SqlLite file'''
    DATABASE = 'sqlite:///{}'.format(
        os.path.join(os.path.dirname(os.path.dirname(__file__)), 'sqlite.db')
    )
    SQLALCHEMY_DATABASE_URI = DATABASE


class PostgresConfig(DefaultDatabaseConfig):
    '''Connect to a postgres database'''
    DATABASE = 'Not Implemented'
    SQLALCHEMY_DATABASE_URI = DATABASE