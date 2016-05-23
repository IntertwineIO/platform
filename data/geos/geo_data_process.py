#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''Loads geo data into Intertwine'''
from alchy import Manager
from alchy.model import extend_declarative_base

from config import DevConfig
from data.data_process import DataSessionManager
from data.geos.models import (BaseGeoDataModel, State, CBSA, County, Place,
                              LSAD, Geoclass, GHR, F02)
from intertwine.utils import Trackable
from intertwine.geos.models import BaseGeoModel, Geo


def load_geo_data():

    # Session for geo.db, which contains the geo source data
    geo_dsm = DataSessionManager(db_config=DevConfig.GEO_DATABASE,
                                 ModelBases=[BaseGeoDataModel])
    geo_session = geo_dsm.session

    # Session for main Intertwine db, where geo data is loaded
    # dsm = DataSessionManager(db_config=DevConfig.DATABASE,
    #                          ModelBases=[BaseGeoModel])
    # session = dsm.session
    db = Manager(Model=BaseGeoModel, config=DevConfig)
    session = db.session
    extend_declarative_base(BaseGeoModel, session=session)
    db.create_all()

    Trackable.register_existing(session, Geo)
    Trackable.clear_updates()

    us = Geo(name='United States', abbrev='US',
             # geo_type='country', descriptor='country'
             )

    # States including PR and DC
    print 'Loading states and equivalents...'
    ghrs = geo_session.query(GHR).filter(GHR.sumlev == '040',
                                         GHR.geocomp == '00').all()
    for ghr in ghrs:
        state = ghr.state
        Geo(name=state.name,
            abbrev=state.stusps,
            path_parent=us,
            # geo_type='subdivision1',
            # descriptor='state',
            parents=[us],
            # total_pop=ghr.f02.p0020001,
            # urban_pop=ghr.f02.p0020002
            )

    # Handle special cases
    pr = Geo['us' + Geo.delimiter + 'pr']
    pr.descriptor = 'territory'
    dc = Geo['us' + Geo.delimiter + 'dc']
    dc.name = 'Washington, D.C.'
    dc.geo_type = 'place'
    dc.descriptor = 'consolidated federal district'

    # Remaining U.S. territories
    more_areas = geo_session.query(State).filter(
            State.stusps.in_(['AS', 'GU', 'MP', 'UM', 'VI'])).all()
    for area in more_areas:
        Geo(name=area.name,
            abbrev=area.stusps,
            path_parent=us,
            geo_type='subdivision1',
            descriptor='territory',
            parents=[us])

    # Counties excluding independent cities and DC
    print 'Loading counties and equivalents in...'
    ghrs = geo_session.query(GHR).filter(GHR.sumlev == '050',
                                         GHR.geocomp == '00',
                                         GHR.countycc != 'C7',
                                         GHR.statefp != '11').all()
    state = None
    stusps = last_stusps = None
    for ghr in ghrs:
        stusps = ghr.county.stusps
        if stusps != last_stusps:
            state = Geo['us' + Geo.delimiter + stusps.lower()]
            print '\t' + state.name
            last_stusps = stusps
        name = ghr.county.name
        Geo(name=name,
            path_parent=state,
            geo_type='subdivision2',
            descriptor=ghr.countyclass.name.lower(),
            parents=[state],
            total_pop=ghr.f02.p0020001,
            urban_pop=ghr.f02.p0020002)

    # Handle special cases
    ak = Geo['us' + Geo.delimiter + 'ak']
    anchorage = Geo[Geo.create_key(name='Anchorage Municipality',
                                   path_parent=ak)]
    anchorage.name = 'Anchorage'
    anchorage.geo_type = 'place'
    juneau = Geo[Geo.create_key(name='Juneau City and Borough',
                                path_parent=ak)]
    juneau.name = 'Juneau'
    juneau.geo_type = 'place'
    sitka = Geo[Geo.create_key(name='Sitka City and Borough',
                               path_parent=ak)]
    sitka.name = 'Sitka'
    sitka.geo_type = 'place'

    ca = Geo['us' + Geo.delimiter + 'ca']
    sf = Geo[Geo.create_key(name='San Francisco County',
                            path_parent=ca)]
    sf.name = 'San Francisco'
    sf.geo_type = 'place'

    # Counties in remaining U.S. territories, except Guam, because Guam
    # has just a single coextensive county
    more_areas = geo_session.query(County).filter(
            County.stusps.in_(['AS', 'MP', 'UM', 'VI'])).all()

    territory = None
    stusps = last_stusps = None
    for area in more_areas:
        stusps = area.stusps
        if stusps != last_stusps:
            territory = Geo['us' + Geo.delimiter + stusps.lower()]
            print '\t' + territory.name
            last_stusps = stusps
        name = area.name
        Geo(name=name,
            path_parent=territory,
            geo_type='subdivision2',
            descriptor=area.geoclass.name.lower(),
            parents=[territory])



    # CSAs

    # CBSAs

    # Places
    ghrs = geo_session.query(GHR).filter(GHR.sumlev == '070',
                                         GHR.statefp != '11').all()


    # Handle unincorporated county remainder special case
    # Handle independent city special case
    # Handle consolidated cities/counties special case
    # Handle Washington, D.C. special case

    return Trackable.catalog_updates()
