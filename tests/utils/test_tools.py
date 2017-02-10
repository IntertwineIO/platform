#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import json
import pytest


@pytest.mark.unit
@pytest.mark.parametrize("problem_name, org_name, geo_name, num_followers", [
    ('Homelessness', None, None, 100000),
    ('Homelessness', None, 'Austin', 10000),
    ('Sexual Assault', 'University of Texas', None, 10000),
    ('Sexual Assault', 'University of Texas', 'Austin', 5000),
    ('Homeless Often Lack ID', None, 'Travis County', 100),
    ('Lack of Standard Homeless Metrics', None, 'Greater Austin', 3),
    ('Homelessness', None, u'Lopeño', 0),
    ('Homelessness', None, 'Waxahachie', None),
])
def test_vardygrify(session, problem_name, org_name, geo_name, num_followers):
    '''Tests vardygrify by comparing vardygr and real communities'''
    from intertwine.communities.models import Community
    from intertwine.geos.models import Geo
    from intertwine.problems.models import Problem
    from intertwine.utils.tools import vardygrify

    problem = Problem(name=problem_name) if problem_name else None
    org = org_name if org_name else None
    geo = Geo(name=geo_name) if geo_name else None
    community_kwds = dict(problem=problem, org=org, geo=geo,
                          num_followers=num_followers)
    real_community = Community(**community_kwds)

    session.add(real_community)
    session.commit()

    vardygr_community = vardygrify(Community, **community_kwds)

    # Hide ids, since they will differ
    json_config = {
        '.id': 0,
        '.problem.id': 0,
        '.geo.id': 0,
    }

    real_community_payload = real_community.jsonify(config=json_config)
    vardygr_community_payload = vardygr_community.jsonify(config=json_config)
    assert real_community_payload == vardygr_community_payload

    real_community_json = json.dumps(real_community_payload)
    vardygr_community_json = json.dumps(vardygr_community_payload)
    assert real_community_json == vardygr_community_json
