# -*- coding: utf-8 -*-
from fixtures import *  # noqa


def pytest_addoption(parser):
    parser.addoption("--license", action="store_true", help="run license tests")

collect_ignore = ["setup.py"]
