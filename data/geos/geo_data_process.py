#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''Loads geo data into Intertwine'''
from sqlalchemy import desc
from alchy import Manager
from alchy.model import extend_declarative_base

from config import DevConfig
from data.data_process import DataSessionManager
from data.geos.models import (BaseGeoDataModel, State, CBSA, County, Place,
                              LSAD, Geoclass, GHRP)
from intertwine.utils import Trackable
from intertwine.geos.models import (BaseGeoModel, Geo, GeoData, GeoLevel,
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
    usa = Geo(name='United States of America', abbrev='U.S.A.',
              alias_target=us)
    GeoLevel(geo=us, level='country', designation='federal republic')

    # States including PR and DC
    ghrps = geo_session.query(GHRP).filter(GHRP.sumlev == '040',
                                           GHRP.geocomp == '00',
                                           # GHRP.statefp == '48'
                                           ).all()

    print 'Loading states and equivalents...'
    for ghrp in ghrps:
        state = ghrp.state
        g = Geo(name=state.name,
                abbrev=state.stusps,
                path_parent=us,
                parents=[us])
        GeoData(geo=g,
                total_pop=ghrp.p0020001,
                urban_pop=ghrp.p0020002,
                latitude=ghrp.intptlat,
                longitude=ghrp.intptlon)
        GeoLevel(geo=g, level='subdivision1', designation='state')

    # Handle special cases
    pr = us['pr']
    pr.levels['subdivision1'].designation = 'territory'
    dc = us['dc']
    dc.levels['subdivision1'].designation = 'federal district'

    # d_of_c = us['dc']
    # d_of_c.abbrev = None
    # d_of_c.parents = []
    # dc = Geo(name='Washington, D.C.', abbrev='D.C.', path_parent=us,
    #          parents=[us])
    # d_of_c.alias_target = dc

    # dc.levels['subdivision1'].designation = 'federal district'
    # GeoLevel(geo=dc, level='subdivision2',
    #          designation='consolidated county or equivalent')
    # GeoLevel(geo=dc, level='place', designation='city')

    # w = Geo(name='Washington', alias_target=dc)
    # wdc = Geo(name='Washington', path_parent=dc, alias_target=dc)

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
    ghrps = geo_session.query(GHRP).filter(GHRP.sumlev == '050',
                                           GHRP.geocomp == '00',
                                           GHRP.countycc != 'C7',
                                           # GHRP.statefp != '11'
                                           ).all()

    # Testing: Counties containing the 3 Chula Vista CDPs
    # ghrps = geo_session.query(GHRP).filter(
    #                                 GHRP.sumlev == '050',
    #                                 GHRP.geocomp == '00',
    #                                 GHRP.countycc != 'C7',
    #                                 GHRP.countyfp.in_(['061', '323', '507']),
    #                                 GHRP.statefp == '48').all()

    state = None
    stusps = prior_stusps = None
    print 'Loading counties and equivalents in...'
    for ghrp in ghrps:
        stusps = ghrp.county.stusps
        if stusps != prior_stusps:
            state = us[stusps]
            print '\t' + state.name
            prior_stusps = stusps
        name = ghrp.county.name
        g = Geo(name=name,
                path_parent=state,
                parents=[state])
        GeoData(geo=g,
                total_pop=ghrp.p0020001,
                urban_pop=ghrp.p0020002,
                latitude=ghrp.intptlat,
                longitude=ghrp.intptlon)
        GeoLevel(geo=g, level='subdivision2',
                 designation=ghrp.countyclass.name.lower())

    # Counties in remaining U.S. territories, except Guam, because Guam
    # has just a single coextensive county
    more_areas = geo_session.query(County).filter(
            County.stusps.in_(['AS', 'MP', 'UM', 'VI'])).all()

    territory = None
    stusps = prior_stusps = None
    for area in more_areas:
        stusps = area.stusps
        if stusps != prior_stusps:
            territory = us[stusps]
            print '\t' + territory.name
            prior_stusps = stusps
        name = area.name
        g = Geo(name=name,
                path_parent=territory,
                parents=[territory])
        GeoLevel(geo=g, level='subdivision2',
                 designation=area.geoclass.name.lower())



    # CSAs

    # CBSAs

    # Places
    ghrps = geo_session.query(GHRP).filter(
                GHRP.sumlev == '155',
                GHRP.geocomp == '00',
                # GHRP.statefp == '48'  # Texas (for testing)
                ).order_by(
                    GHRP.statefp,
                    GHRP.placefp,
                    desc(GHRP.p0020001)).all()

    num_places = len(ghrps)
    stusps = prior_stusps = None
    state = None
    counties = []
    total_pop = urban_pop = 0
    conflicts = {}
    consolidated = {}
    print 'Loading places in...'
    for i, ghrp in enumerate(ghrps):

        # update variables
        stusps = ghrp.state.stusps
        if stusps != prior_stusps:
            state = us[stusps]
            print '\t' + state.name
            prior_stusps = stusps

        county = state[ghrp.county.name]
        if county is not None:
            counties.append(county)
        total_pop += ghrp.p0020001
        urban_pop += ghrp.p0020002

        # we're on the last record for the current place, so create geo
        if i+1 == num_places or ghrps[i+1].geoid != ghrp.geoid:
            ghrp_place = ghrp.place

            lsad = ghrp_place.lsad
            desig = lsad.display
            desig = desig.split(' (actual text)')[0]
            desig = desig.split(' (prefix)')[0]
            desig = desig.split(' (suffix)')[0]
            place_name = ghrp_place.name
            if desig != '':
                place_name = place_name.split(desig)[0].strip()

            # desig = desig.lower()
            print '\t\t' + place_name + '(' + ghrp.geoid + ')'

            # check for existing place with same key
            key = Geo.create_key(name=place_name, path_parent=state)
            existing = Geo[key]
            if existing is not None:
                # if not an alias, rename it and make an alias to it
                # TODO: add an optional 'qualifier' attribute to Geo
                if existing.alias_target is None:
                    # TODO: make sure it's a county name
                    if (existing.levels.get('place', None) is not None):
                        existing_desig = existing.levels['place'].designation
                        existing.name += (' (' + existing_desig + ' in ' +
                                          existing.parents[0].name + ')')
                        alias = Geo(name=place_name,
                                    path_parent=state,
                                    alias_target=existing)
                        conflicts[key] = existing.data.total_pop
                    elif (existing.levels.get(
                                            'subdivision2', None) is not None):
                        if existing != county:
                            raise NameError('place key conflicts with '
                                            'subdivision2 key, yet place is '
                                            'not in subdivision2')
                        GeoLevel(geo=existing,
                                 level='place',
                                 designation=desig)
                        counties = []
                        total_pop = urban_pop = 0
                        continue
                    else:
                        raise NameError('key conflict with geo that is '
                                         'neither a place nor subdivision2')


                assert len(counties) > 0
                place_name += ' (' + desig + ' in ' + counties[0].name + ')'

            g = Geo(name=place_name,
                    path_parent=state,
                    parents=counties + [state])
            GeoData(geo=g,
                    total_pop=total_pop,
                    urban_pop=urban_pop,
                    latitude=ghrp_place.intptlat,
                    longitude=ghrp_place.intptlong)
            GeoLevel(geo=g, level='place', designation=desig)

            # update alias to point at the geo with the largest pop
            if (existing is not None and total_pop > conflicts[key]):
                alias.alias_target = g
                conflicts[key] = total_pop

            # if consolidated county, add place to list
            if ghrp.county.geoclassfp == 'H6':
                places = consolidated.get(county, None)
                if places is None:
                    consolidated[county] = [g]
                else:
                    consolidated[county].append(g)

            # reset variables for new place
            counties = []
            total_pop = urban_pop = 0

    # Add missing consolidated counties
    ak = us['ak']
    yak = ak['yakutat'].parents[0]
    consolidated[yak] = yak.children.all()
    wra = ak['wrangell'].parents[0]
    consolidated[wra] = wra.children.all()
    dc = us['dc']
    dc_county = dc['washington'].parents[0]
    consolidated[dc_county] = dc_county.children.all()

    # Clean up consolidated counties with only one place
    for county, places in consolidated.iteritems():
        if len(places) == 1:
            place = places[0]
            # GeoData.unregister(place.data)
            place.data = None
            assert len(place.levels) == 1
            place.levels['place'].geo = county
            place.parents = []
            # Move any children of the place to the county
            for child in place.children.all():
                if county not in child.parents:
                    child.parents = [county] + child.parents

            # Make the place an alias for the county
            place.alias_target = county
            # Reverse the relationship, making the county the alias
            place.promote_to_alias_target()

    # Combine DC again
    w = dc['washington']
    w.data = None
    w.levels['subdivision2'].geo = dc
    w.levels['place'].geo = dc
    w.parents = []
    w.alias_target = dc
    wdc = dc['district_of_columbia']
    wdc.name = 'Washington, D.C.'
    wdc.path_parent = us

    # Clean up places with lsad_code = '00':
    #
    # 1 CT  0947515     Milford city (balance)
    #   CT  0988050     Woodmont borough is wholly contained in Milford
    #                   Rename as Milford
    #                   Update pop
    #                   Add Woodmont as child
    # 2 GA  1303440     Athens-Clarke County unified government (balance)
    #   GA  1383728     Winterville city is wholly contained in Athens-Clarke
    #   GA  1309068     Bogart town: 140/117 (t/u) pop resides within Athens-Clarke County
    #                   Rename as Athens-Clarke County
    #                   Rename place geolevel as 'unified government'
    #                   Repoint place geolevel to Clarke County
    #                   Remove data from Athens-Clarke County (unregister)
    #                   Transfer Winterville and Bogart children to Clarke County
    #                   Make Athens-Clarke County an alias to Clarke County
    #                   Promote Athens-Clarke County
    # 3 GA  1304204     Augusta-Richmond County consolidated government (balance)
    # 4 IN  1836003     Indianapolis city (balance)
    # 5 KY  2148006     Louisville/Jefferson County metro government (balance)
    # 6 MT  3001675     Anaconda-Deer Lodge County
    # 7 MT  3011397     Butte-Silver Bow (balance)
    # 8 NV  3209700     Carson City
    # 9 TN  4732742     Hartsville/Trousdale County
    #10 TN  4752006     Nashville-Davidson metropolitan government (balance)


    # TODO: Handle unincorporated county remainder special case
    ghrps = geo_session.query(GHRP).filter(GHRP.sumlev == '070',
                                           GHRP.placefp == '99999').all()
    # Need to sum remainders across county subdivisions within a county

    return Trackable.catalog_updates()
