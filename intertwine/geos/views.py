# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from operator import attrgetter

import flask
from flask import abort, redirect, render_template

from . import blueprint, geo_db
from .models import Geo, GeoLevel


@blueprint.route('/', methods=['GET'])
def render():
    '''Generic page rendering for top level'''
    geos = Geo.query.filter(Geo.path_parent is None,
                            Geo.alias_target is None).order_by(Geo.name).all()
    # glvls = GeoLevel.query.filter(GeoLevel.level == 'country').all()
    # geos = [glvl.geo for glvl in glvls]
    if len(geos) == 1:
        geo = geos[0]
        glvl = geo.levels.keys()[0]
        dlvl = GeoLevel.DOWN[glvl][0]

        by_name = sorted(geo.children.all(), key=attrgetter('name'))
        by_designation = sorted(by_name,
                                key=lambda g: g.levels[dlvl].designation)

        geos += by_designation
    template = render_template(
        'geos.html',
        current_app=flask.current_app,
        title="Geos",
        geos=geos)
    return template


@blueprint.route('/<path:geo_human_id>', methods=['GET'])
def render_geo(geo_human_id):
    '''Problem Page'''
    human_id = geo_human_id.lower()
    geo = Geo.query.filter_by(human_id=human_id).first()

    if geo is None:
        # TODO: Instead of aborting, reroute to geo_not_found page
        # Oops! 'X' is not a geo found in Intertwine.
        # Did you mean:
        # <geo_1>
        # <geo_2>
        # <geo_3>
        abort(404)

    if geo.alias_target:
        target = geo.alias_target.human_id
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
