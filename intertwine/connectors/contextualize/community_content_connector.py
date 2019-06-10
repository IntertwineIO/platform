# -*- coding: utf-8 -*-
import json
import os

import requests

import settings
from intertwine.geos.models import Geo
from intertwine.problems.models import AggregateProblemConnectionRating as APCR


class CommunityContentConnector:

    URL = os.path.join(settings.CONTEXTUALIZE_BASE_URL, 'community', 'content')
    TIMEOUT = 1

    def fetch(self):

        try:
            request = response = content = None
            request = self.request_builder.build()
            response = requests.post(self.URL, timeout=self.TIMEOUT, json=request)
            content = self.response_parser.parse(response)

        except Exception as e:
            print(dict(msg='Error fetching community content via connector',
                       type='community_content_connector_error', request=request,
                       response=response, content=content, error=str(e)))

        return content

    def __init__(self, community):
        self.community = community
        # self.log_parameters = self._initialize_log_parameters(community)
        self.request_builder = CommunityContentRequestBuilder(community)
        self.response_parser = CommunityContentResponseParser(community)


class CommunityContentRequestBuilder:

    COMMUNITY_CONFIG = {
        '.': -1,
        '.name': 1,
        '.problem': -2,
        '.problem.name': 1,
        '.org': -1,
        '.geo': -1,
        '.aggregate_ratings': {'depth': 2, 'hide_all': True, 'nest': True},
    }

    GEO_CONFIG = {
        '.name': 1,
        '.abbrev': 1,
        '.levels': -1,
        '.levels.designation': 1,
        '.aliases': -1,
        '.path_parent': -1,
    }

    AGGREGATE_RATING_CONFIG = {
        '.rating': 1,
        '.adjacent_problem_name': 1,
        '.adjacent_community_url': 1,
    }

    COMMUNITY_KWARG_MAP = {
        Geo: dict(config=GEO_CONFIG),
        APCR: dict(config=AGGREGATE_RATING_CONFIG)
    }

    def build(self):
        try:
            return self.community.jsonify(config=self.COMMUNITY_CONFIG,
                                          kwarg_map=self.COMMUNITY_KWARG_MAP)
        except Exception as e:
            print(e)

    def __init__(self, community):
        self.community = community


class CommunityContentResponseParser:

    def parse(self, response):
        content_bytes = response.content
        content_string = content_bytes.decode('utf-8')
        content_json = json.loads(content_string)
        return content_json

    def __init__(self, community):
        self.community = community
