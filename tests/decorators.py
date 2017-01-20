# -*- coding: utf-8 -*-
import pytest


license = pytest.mark.skipif(
    not pytest.config.getoption("--license"),
    reason="need --license option to run"
)
