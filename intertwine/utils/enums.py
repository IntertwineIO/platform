# -*- coding: utf-8 -*-
from enum import Enum


MatchType = Enum('FilterType', 'BEST, EXACT, STARTS_WITH, ENDS_WITH, CONTAINS',
                 module=__name__)

UriType = Enum('UriType', 'PRIMARY, NATURAL', module=__name__)
