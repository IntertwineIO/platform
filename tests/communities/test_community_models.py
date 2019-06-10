# -*- coding: utf-8 -*-
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
def test_community_model_create(session, problem_name, org_name, geo_name,
                                num_followers):
    """Test simple community model interaction"""
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

    assert Community[community.derive_key()] is community
    assert problem is community.problem
    assert org == community.org
    assert geo is community.geo

    community_from_db = Community.query.filter_by(
        problem=problem, org=org, geo=geo).one()

    assert community_from_db is community
    assert community_from_db.problem is problem
    assert community_from_db.org == org
    assert community_from_db.geo is geo
    assert community_from_db.num_followers == num_followers
    assert community_from_db.name == problem.name + (
        ' at ' + org_name if org_name else '') + (
        ' in ' + geo.display(show_abbrev=False) if geo else '')
