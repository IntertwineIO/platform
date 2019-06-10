# -*- coding: utf-8 -*-


class EnvironmentConfig:
    """Base class for environments"""
    ERROR_404_HELP = True  # Flask-Restful setting


class LocalConfig(EnvironmentConfig):
    """Local Based configuration"""


class HerokuConfig(EnvironmentConfig):
    """Heroku Based configuration"""


class VagrantConfig(EnvironmentConfig):
    """Vagrant Based configuration"""
    ERROR_404_HELP = False  # Flask-Restful setting


class EC2Config(EnvironmentConfig):
    """AWS EC2 Based configuration"""
    ERROR_404_HELP = False  # Flask-Restful setting


class EBConfig(EnvironmentConfig):
    """AWS Elastic Beanstalk Based configuration"""
    ERROR_404_HELP = False  # Flask-Restful setting
