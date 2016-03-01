#!/usr/bin/env python
# -*- coding: utf-8 -*-
import pytest
from intertwine.config import ToxConfig

collect_ignore = ["setup.py"]


@pytest.fixture(scope="module")
def options():
    '''Captures configuration data from config file and validates that
    data is available'''

    options = {
        'host': '127.0.0.1',
        'port': 5000,
        'config': ToxConfig(),
    }

    return options
