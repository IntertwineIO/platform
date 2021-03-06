# -*- coding: utf-8 -*-
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
    ('Homelessness', None, 'Lopeño', 0),
    ('Homelessness', None, 'Waxahachie', None),
])
def test_jsonify(session, problem_name, org_name, geo_name, num_followers):
    """Test jsonify of Jsonable mixin by producing community JSON"""
    from intertwine.communities.models import Community
    from intertwine.geos.models import Geo
    from intertwine.problems.models import Problem

    problem = Problem(name=problem_name) if problem_name else None
    org = org_name if org_name else None
    geo = Geo(name=geo_name) if geo_name else None
    community = Community(
        problem=problem, org=org, geo=geo, num_followers=num_followers)

    session.add(community)
    session.commit()

    community_payload = community.jsonify()

    root = community_payload[Community.JSON_ROOT]
    community_json = community_payload[root]

    problem_key = community_json['problem']
    if problem:
        assert problem_key
        assert problem_key not in community_payload

    org_key = community_json['org']
    if org:
        assert org_key
        assert org_key not in community_payload

    geo_key = community_json['geo']
    if geo:
        assert geo_key
        assert geo_key not in community_payload

    json.dumps(community_payload)


@pytest.mark.unit
@pytest.mark.parametrize("problem_name, org_name, geo_name, num_followers", [
    ('Homelessness', None, None, 100000),
    ('Homelessness', None, 'Austin', 10000),
    ('Sexual Assault', 'University of Texas', None, 10000),
    ('Sexual Assault', 'University of Texas', 'Austin', 5000),
    ('Homeless Often Lack ID', None, 'Travis County', 100),
    ('Lack of Standard Homeless Metrics', None, 'Greater Austin', 3),
    ('Homelessness', None, 'Lopeño', 0),
    ('Homelessness', None, 'Waxahachie', None),
])
def test_jsonify_depth2(session, problem_name, org_name, geo_name,
                        num_followers):
    """Test jsonify by producing depth 2 community JSON"""
    from intertwine.communities.models import Community
    from intertwine.geos.models import Geo
    from intertwine.problems.models import Problem

    problem = Problem(name=problem_name) if problem_name else None
    org = org_name if org_name else None
    geo = Geo(name=geo_name) if geo_name else None
    community = Community(
        problem=problem, org=org, geo=geo, num_followers=num_followers)

    session.add(community)
    session.commit()

    community_payload = community.jsonify(depth=2)

    root = community_payload[Community.JSON_ROOT]
    community_json = community_payload[root]

    problem_key = community_json['problem']
    if problem:
        assert problem_key
        assert problem_key in community_payload

    org_key = community_json['org']
    if org:
        assert org_key
        # Include once there is an org model
        # assert org_key in community_payload

    geo_key = community_json['geo']
    if geo:
        assert geo_key
        assert geo_key in community_payload

    json.dumps(community_payload)
