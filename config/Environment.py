#!/usr/bin/env python
# -*- coding: utf-8 -*-


class EnvironmentConfig(object):
    '''Base class for environments'''


class LocalConfig(EnvironmentConfig):
    '''Local Based configuration'''


class HerokuConfig(EnvironmentConfig):
    '''Heroku Based configuration'''


class VagrantConfig(EnvironmentConfig):
    '''Vagrant Based configuration'''


class AWSConfig(EnvironmentConfig):
    '''AWS Based configuration'''
