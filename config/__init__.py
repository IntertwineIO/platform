#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''Provides a way to dynamically create a new environment if needed.

Standard environments are:  Demo, Local and Dev

TODO:  Test (staging) and Production
'''
from .Default import DefaultConfig, DevelopmentConfig, TestingConfig, ProductionConfig, DeployableConfig
from .Environment import LocalConfig, HerokuConfig, VagrantConfig, AWSConfig
from .Database import InMemoryConfig, SqlLiteConfig, PostgresConfig

__all__ = ['DemoConfig', 'LocalDemoConfig', 'DevConfig']


class DemoConfig(DeployableConfig, HerokuConfig, SqlLiteConfig):
    '''Configures for demo'''


class LocalDemoConfig(DeployableConfig, LocalConfig, SqlLiteConfig):
    '''Configures for local demo'''


class DevConfig(DevelopmentConfig, LocalConfig, SqlLiteConfig):
    '''Standard development environment configuration'''
