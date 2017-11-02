#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

from enum import Enum


MatchType = Enum('FilterType', 'BEST, EXACT, STARTS_WITH, ENDS_WITH, CONTAINS',
                 module=__name__)
