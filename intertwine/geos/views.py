# -*- coding: utf-8 -*-
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import flask
from flask import (abort, jsonify, make_response, redirect, render_template,
                   request)

from . import blueprint
from .models import Geo, GeoLevel
from intertwine.utils.jsonable import Jsonable
from ..exceptions import InterfaceException, ResourceDoesNotExist
from ..utils.flask_utils import crossdomain, json_requested


@blueprint.errorhandler(InterfaceException)
def handle_interface_exception(error):
    """
    Handle Interface Exception

    Intercept the error and return a response consisting of the status
    code and a JSON representation of the error.
    """
    return make_response(jsonify(error.jsonify()), error.status_code)


@blueprint.route('/', methods=['GET'])
@crossdomain(origin='*')
def render():
    """Base endpoint serving both pages and the API"""
    if json_requested():
        match_string = request.args.get('match_string')
        return find_geo_matches(match_string)

    return render_index()


def render_index():
    """Generic page rendering for top level"""
    geos = Geo.query.filter(~Geo.path_parent.has(),
                            ~Geo.alias_targets.any()).order_by(Geo.name).all()
    # glvls = GeoLevel.query.filter(GeoLevel.level == 'country').all()
    # geos = [glvl.geo for glvl in glvls]
    if len(geos) == 1:
        geo = geos[0]
        glvl = next(iter(geo.levels))
        dlvl = GeoLevel.DOWN[glvl][0]

        by_name = geo.get_related_geos(Geo.PATH_CHILDREN, level=dlvl,
                                       order_by=Geo.name)
        by_designation = sorted(by_name,
                                key=lambda g: g.levels[dlvl].designation)
        geos += by_designation

    template = render_template(
        'geos.html',
        current_app=flask.current_app,
        title="Geos",
        geos=geos)

    return template


def find_geo_matches(match_string, match_limit=None):
    """
    Find geo matches endpoint

    Usage:
    curl -H 'accept:application/json' -X GET \
    'http://localhost:5000/geos/?match_string=austin,%20tx&match_limit=-1'
    """
    match_string = match_string.strip('"\'')
    if not match_string:
        return jsonify(Jsonable.jsonify_value([]))

    match_limit = match_limit or int(request.args.get('match_limit', 0))
    geo_matches = Geo.find_matches(match_string)
    geo_json_kwargs = dict(Geo.objectify_json_kwargs(request.args))
    # hide = {Geo.PARENTS, Geo.CHILDREN, Geo.PATH_CHILDREN}
    kwarg_map = {Geo: geo_json_kwargs}
    json_kwargs = dict(limit=match_limit) if match_limit else {}
    import pdb; pdb.set_trace()

    return jsonify(Jsonable.jsonify_value(geo_matches, kwarg_map, **json_kwargs))


@blueprint.route(Geo.form_uri(
    Geo.Key('<path:geo_huid>'), sub_only=True), methods=['GET'])
def get_geo(geo_huid):
    """Get geo endpoint"""
    if json_requested():
        return get_geo_json(geo_huid)

    return get_geo_html(geo_huid)


def get_geo_json(geo_huid):
    """
    Get geo JSON

    Usage:
    curl -H 'accept:application/json' -X GET \
    'http://localhost:5000/geos/us/tx/austin'
    """
    json_kwargs = dict(Geo.objectify_json_kwargs(request.args))

    try:
        geo = Geo.reconstruct(geo_huid)
    except KeyError as e:
        raise ResourceDoesNotExist(str(e))

    return jsonify(geo.jsonify(**json_kwargs))


def get_geo_html(geo_huid):
    """Geo Page"""
    geo_huid = geo_huid.lower()

    try:
        geo = Geo.reconstruct(geo_huid)
    except KeyError:
        # TODO: Instead of aborting, reroute to geo_not_found page
        # Oops! 'X' is not a geo found in Intertwine.
        # Did you mean:
        # <geo_1>
        # <geo_2>
        # <geo_3>
        abort(404)

    alias_targets = geo.alias_targets
    if alias_targets:
        target = alias_targets[0].human_id
        return redirect('/geos/{}'.format(target), code=302)
    # Austin, Texas, United States
    title = geo.display()

    geo = geo

    # get list of top problems in geo based on followers, activity, trending
    # top_problems =

    template = render_template(
        'geo.html',
        current_app=flask.current_app,
        title=title,
        geo=geo,
        # top_problems=top_problems,
    )
    return template
