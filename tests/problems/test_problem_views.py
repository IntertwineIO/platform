#!/usr/bin/env python
# -*- coding: utf-8 -*-
import pytest


@pytest.mark.unit
@pytest.mark.smoke
# @pytest.mark.skip('Requires test client')
def test_add_rated_problem_connection(session, client):
    '''Tests aggregate problem connection rating model interaction'''
    import json

    from intertwine.communities.models import Community
    from intertwine.geos.models import Geo
    from intertwine.problems.models import (Problem,
                                            ProblemConnection,
                                            ProblemConnectionRating,
                                            AggregateProblemConnectionRating)

    problem_name_base = 'Test Problem'
    problem1 = Problem(problem_name_base + ' 01')
    org1 = 'University of Texas'
    geo1 = Geo('Austin')
    community1 = Community(problem=problem1, org=org1, geo=geo1)

    session.add(community1)
    session.commit()

    axis12 = 'causal'
    problem2_name = problem_name_base + ' 02'
    aggregation = 'strict'

    request_payload = {
        'connection': {
            'axis': axis12,
            'problem_a': problem1.name,
            'problem_b': problem2_name
        },
        'community': {
            'problem': problem1.human_id,
            'org': org1,
            'geo': geo1.human_id
        },
        'aggregation': aggregation
    }

    request_data = json.dumps(request_payload)
    url = 'http://localhost:5000/problems/rated_connections'

    response = client.post(url, data=request_data,
                           content_type='application/json')

    assert response is not None

    # This doesn't work yet...
    # problem2 = Problem[problem2_name]
    # assert problem2 is not None

    response_data = response.get_data(as_text=True)
    response_payload = json.loads(response_data)
    root_key = response_payload['root_key']
    rated_connection = response_payload[root_key]
    assert rated_connection['adjacent_problem_name'] == problem2_name
