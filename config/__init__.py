#!/usr/bin/env python
# -*- coding: utf-8 -*-
from .Default import DefaultConfig, DevelopmentConfig, TestingConfig, ProductionConfig, DeployableConfig
from .Environment import LocalConfig, HerokuConfig, VagrantConfig, EBConfig, EC2Config
from .Database import InMemoryConfig, SqlLiteConfig, PostgresConfig, GeoSqlLiteConfig

__all__ = ['DemoConfig', 'LocalDemoConfig', 'DevConfig', 'ToxConfig']


class DemoConfig(DeployableConfig, HerokuConfig, SqlLiteConfig):
    """Configures for demo"""


class LocalDemoConfig(DeployableConfig, LocalConfig, SqlLiteConfig):
    """Configures for local demo"""


class DevConfig(DevelopmentConfig, LocalConfig, SqlLiteConfig,
                GeoSqlLiteConfig):
    """Standard development environment configuration"""


class ToxConfig(TestingConfig, LocalConfig, InMemoryConfig):
    """Standard development for tox testing"""
