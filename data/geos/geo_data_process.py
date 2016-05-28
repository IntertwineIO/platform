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
from intertwine.geos.models import (BaseGeoModel, Geo, GeoLevel,
                                    geo_association_table)


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

    us = Geo(name='United States', abbrev='U.S.')
    usa = Geo(name='United States of America', abbrev='U.S.A.', mcka=us)
    GeoLevel(geo=us, level='country', designation='federal republic')

    # States including PR and DC
    print 'Loading states and equivalents...'
    ghrs = geo_session.query(GHR).filter(GHR.sumlev == '040',
                                         GHR.geocomp == '00').all()
    for ghr in ghrs:
        state = ghr.state
        g = Geo(name=state.name,
                abbrev=state.stusps,
                path_parent=us,
                parents=[us],
                # total_pop=ghr.f02.p0020001,
                # urban_pop=ghr.f02.p0020002
                )
        GeoLevel(geo=g, level='subdivision1', designation='state')

    # Handle special cases
    pr = Geo['us' + Geo.delimiter + 'pr']
    pr.levels['subdivision1'].designation = 'territory'

    d_of_c = Geo['us' + Geo.delimiter + 'dc']
    d_of_c.abbrev = None
    d_of_c.parents = []
    dc = Geo(name='Washington, D.C.', abbrev='D.C.', path_parent=us,
             parents=[us])
    d_of_c.mcka = dc

    dc.levels = d_of_c.levels
    dc.levels['subdivision1'].designation = 'federal district'
    GeoLevel(geo=dc, level='subdivision2', designation='consolidated county or equivalent')
    GeoLevel(geo=dc, level='place', designation='city')

    w = Geo(name='Washington', mcka=dc)
    wdc = Geo(name='Washington', path_parent=dc, mcka=dc)

    # Remaining U.S. territories
    more_areas = geo_session.query(State).filter(
            State.stusps.in_(['AS', 'GU', 'MP', 'UM', 'VI'])).all()
    for area in more_areas:
        g = Geo(name=area.name,
                abbrev=area.stusps,
                path_parent=us,
                parents=[us])
        GeoLevel(geo=g, level='subdivision1', designation='territory')

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
        g = Geo(name=name,
                path_parent=state,
                parents=[state],
                # total_pop=ghr.f02.p0020001,
                # urban_pop=ghr.f02.p0020002
                )
        GeoLevel(geo=g, level='subdivision2',
                 designation=ghr.countyclass.name.lower())

    # Handle special cases
    ak = Geo['us' + Geo.delimiter + 'ak']
    anchorage = Geo[Geo.create_key(name='Anchorage Municipality',
                                   path_parent=ak)]
    anchorage.name = 'Anchorage'
    juneau = Geo[Geo.create_key(name='Juneau City and Borough',
                                path_parent=ak)]
    juneau.name = 'Juneau'
    sitka = Geo[Geo.create_key(name='Sitka City and Borough',
                               path_parent=ak)]
    sitka.name = 'Sitka'

    ca = Geo['us' + Geo.delimiter + 'ca']
    sf = Geo[Geo.create_key(name='San Francisco County',
                            path_parent=ca)]
    sf.name = 'San Francisco'

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
        g = Geo(name=name,
                path_parent=territory,
                parents=[territory])
        GeoLevel(geo=g, level='subdivision2',
                 designation=area.geoclass.name.lower())



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
