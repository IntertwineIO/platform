#!/usr/bin/env python
# -*- coding: utf-8 -*-


class DefaultDatabaseConfig(object):
    MAIL_SERVER = 'smtp.example.com'
    MAIL_PORT = 465
    MAIL_USE_SSL = True
    MAIL_USERNAME = 'username'
    MAIL_PASSWORD = 'password'


class NoMailServer(DefaultDatabaseConfig):
    '''No Mailserver Configuration'''
    MAIL_SERVER = ''
    MAIL_USERNAME = ''
    MAIL_PASSWORD = ''


class LocalMailServer(DefaultDatabaseConfig):
    '''No Mailserver Configuration'''
    MAIL_SERVER = 'localhost'
    MAIL_USERNAME = 'admin'
    MAIL_PASSWORD = 'admin'
