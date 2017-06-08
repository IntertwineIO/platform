#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''Loads geo data into Intertwine'''
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

from collections import namedtuple

from sqlalchemy import desc
from alchy import Manager
from alchy.model import extend_declarative_base

from config import DevConfig
from data.data_process import DataSessionManager
from data.geos.models import (BaseGeoDataModel,
                              State, CBSA, County, Cousub, Place,
                              LSAD, Geoclass,  # Keep - used in globals()
                              GHRP)
from intertwine.trackable import Trackable
from intertwine.trackable.exceptions import KeyRegisteredAndNoModify
from intertwine.utils.structures import PeekableIterator
from intertwine.geos.models import (
    BaseGeoModel, Geo, GeoData, GeoLevel, GeoID,
    # Geo constants
    PARENTS, CHILDREN,  # PATH_CHILDREN, ALIASES, ALIAS_TARGETS,
    # GeoLevel constants
    COUNTRY, SUBDIVISION1, SUBDIVISION2, SUBDIVISION3, PLACE,
    CORE_AREA, COMBINED_AREA,
    # GeoID constants
    FIPS, ANSI, ISO_A2, ISO_A3, ISO_N3, CSA_2010, CBSA_2010)


def derive_columns(classes, fields):
    '''
    Derive columns from classes and fields

    Returns a list of sqlalchemy columns derived from a list of classes
    and a list of fields, often from a named tuple used to store
    queried records. Column names may contain underscores, but class
    names may not. The fields must be in this format:

        <lowercase class name>_<column name>

    Example: 'county_aland_sqmi' becomes column County.aland_sqmi
    '''
    classmap = {cls.__name__.lower(): cls.__name__ for cls in classes}
    columns = [getattr(globals()[classmap[f.split('_')[0]]],  # class
                       '_'.join(f.split('_')[1:]))  # attribute
               for f in fields]
    return columns


def find_non_place_cousubs(geo=None, include_all=False):
    geos = []

    prior_state = prior_county = None

    level = geo.top_level_key if geo else COUNTRY

    states = (
        Geo['us'].get_related_geos(relation=CHILDREN, level=SUBDIVISION1)
        if level == COUNTRY else
        [geo] if level == SUBDIVISION1 else
        [geo.get_related_geos(relation=PARENTS, level=SUBDIVISION1)])

    for state in states:
        state_has_non_place_cousubs = False

        counties = (
            state.get_related_geos(relation=CHILDREN, level=SUBDIVISION2)
            if level in {COUNTRY, SUBDIVISION1} else
            [geo] if level == SUBDIVISION2 else
            [geo.get_related_geos(relation=PARENTS, level=SUBDIVISION2)])

        for county in counties:
            county_has_non_place_cousubs = False
            cousubs = county.get_related_geos(relation=CHILDREN,
                                              level=SUBDIVISION3)
            for cousub in cousubs:
                try:
                    int(cousub.name[0])
                    if include_all:
                        geo_to_add = cousub
                        if state is not prior_state:
                            print('{}'.format(state.trepr()))
                        if county is not prior_county:
                            print('\t{}'.format(county.trepr()))

                    else:
                        geo_to_add = (state if level == COUNTRY else
                                      county if level == SUBDIVISION1
                                      else cousub)

                    geos.append(geo_to_add)
                    print('{indent}{geo}'.format(
                        indent='\t\t' if include_all else '',
                        geo=geo_to_add.trepr()))
                    county_has_non_place_cousubs = True
                    state_has_non_place_cousubs = True
                    prior_state = state
                    prior_county = county
                except ValueError:
                    pass

                if (not include_all and county_has_non_place_cousubs and
                        level in {COUNTRY, SUBDIVISION1}):
                    break
            if (not include_all and state_has_non_place_cousubs and
                    level == COUNTRY):
                break

    return geos


def load_geos(geo_session, session):

    load_country_geos(geo_session, session)
    load_subdivision1_geos(geo_session, session)
    load_subdivision2_geos(geo_session, session)
    load_subdivision3_geos(geo_session, session)
    # load_place_geos(geo_session, session)
    # load_cbsa_geos(geo_session, session)

    return Trackable.catalog_updates()


def load_country_geos(geo_session, session):
    us = Geo(name='United States', abbrev='U.S.')
    Geo(name='United States of America', abbrev='U.S.A.', alias_targets=[us])
    GeoData(geo=us,
            total_pop=0,
            urban_pop=0,
            latitude=39.8333333,
            longitude=-98.585522,
            land_area=0,
            water_area=0)
    # 0 values to be recalculated from children
    # land: 9158022, water: 699284 www.census.gov/geo/reference/state-area.html

    glvl = GeoLevel(geo=us, level=COUNTRY, designation='federal republic')
    GeoID(level=glvl, standard=ISO_A2, code='US')
    GeoID(level=glvl, standard=ISO_A3, code='USA')
    GeoID(level=glvl, standard=ISO_N3, code='840')


def load_subdivision1_geos(geo_session, session):
    # U.S. states plus DC and PR
    ghrps = geo_session.query(GHRP).filter(GHRP.sumlev == '040',
                                           GHRP.geocomp == '00',
                                           # GHRP.statefp == '48'
                                           ).all()
    us = Geo['us']
    print('Loading states and equivalents...')
    for ghrp in ghrps:
        state = ghrp.state
        print('\t{usps} - {name}'.format(usps=state.stusps, name=state.name))
        g = Geo(name=state.name,
                abbrev=state.stusps,
                path_parent=us,
                parents=[us])
        GeoData(geo=g,
                total_pop=ghrp.p0020001,
                urban_pop=ghrp.p0020002,
                latitude=ghrp.intptlat,
                longitude=ghrp.intptlon,
                land_area=(ghrp.arealand * 1.0)/10**6,
                water_area=(ghrp.areawatr * 1.0)/10**6)
        glvl = GeoLevel(geo=g, level=SUBDIVISION1, designation='state')
        GeoID(level=glvl, standard=FIPS, code=ghrp.statefp)
        GeoID(level=glvl, standard=ANSI, code=ghrp.statens)

    # Handle special cases
    pr = us['pr']
    pr.levels[SUBDIVISION1].designation = 'territory'
    dc = us['dc']
    dc.levels[SUBDIVISION1].designation = 'federal district'

    # Remaining U.S. territories
    # Sources:
    # www.census.gov/newsroom/releases/archives/2010_census/cb13-tps62.html
    # www2.census.gov/geo/docs/reference/state.txt
    #                                                                 (km^2)
    #     fips  ansi        tpop    upop    latitude     longitude   land water
    as_ = '60', '01802701', 55519,  48645, -14.2638166, -170.6620902, 198, 1307
    gu_ = '66', '01802705', 159358, 149918, 13.4383000,  144.7729285, 543, 935
    mp_ = '69', '01779809', 53883,  48997,  14.9367835,  145.6010210, 472, 4644
    um_ = '74', '01878752', 0,      0,      0,           0,           0,   0
    vi_ = '78', '01802710', 106405, 100607, 18.3267485, -064.9712501, 348, 1550
    territories = {'AS': as_, 'GU': gu_, 'MP': mp_, 'UM': um_, 'VI': vi_}

    more_areas = geo_session.query(State).filter(
            State.stusps.in_(territories)).all()
    for area in more_areas:
        print('\t{usps} - {name}'.format(usps=area.stusps, name=area.name))
        g = Geo(name=area.name,
                abbrev=area.stusps,
                path_parent=us,
                parents=[us])
        (fips, ansi, total_pop, urban_pop, latitude, longitude,
            land_area, water_area) = territories[area.stusps]
        GeoData(geo=g,
                total_pop=total_pop,
                urban_pop=urban_pop,
                latitude=latitude,
                longitude=longitude,
                land_area=land_area,
                water_area=water_area)
        glvl = GeoLevel(geo=g, level=SUBDIVISION1, designation='territory')
        GeoID(level=glvl, standard=FIPS, code=fips)
        GeoID(level=glvl, standard=ANSI, code=ansi)

    # Update US population and area values based on subdivision1 values
    children = us.children.all()
    us.data.total_pop = sum((c.data.total_pop for c in children if c.data))
    us.data.urban_pop = sum((c.data.urban_pop for c in children if c.data))
    us.data.land_area = sum((c.data.land_area for c in children if c.data))
    us.data.water_area = sum((c.data.water_area for c in children if c.data))


def load_subdivision2_geos(geo_session, session):
    CountyRecord = namedtuple(
        'CountyRecord',
        'ghrp_name, ghrp_lsadc, ghrp_statefp, '  # geoclass_name removed
        'ghrp_countyid, ghrp_countyns, ghrp_p0020001, ghrp_p0020002, '
        'ghrp_intptlat, ghrp_intptlon, ghrp_arealand, ghrp_areawatr')

    columns = derive_columns(classes=(GHRP,),  # Geoclass removed
                             fields=CountyRecord._fields)

    # U.S. counties including independent cities
    records = (geo_session.query(GHRP)
               # .join(GHRP.countyclass)  # geoclass_name removed
               .filter(GHRP.sumlev == '050', GHRP.geocomp == '00',
                       # Counties containing the 3 Chula Vista CDPs:
                       # GHRP.countyid.in_(['48061', '48323', '48507'])
                       )
               .order_by(GHRP.statefp, GHRP.countyid)
               .values(*columns))

    us = Geo['us']
    state = None
    stusps = prior_stusps = None
    print('Loading counties and equivalents in...')
    for r in (CountyRecord(*record) for record in records):

        stusps = State.get_by('statefp', r.ghrp_statefp).stusps
        if stusps != prior_stusps:
            state = us[stusps]
            print('\t{usps} - {name}'.format(usps=state.abbrev,
                                             name=state.name))
            prior_stusps = stusps

        name = r.ghrp_name
        lsad = LSAD.get_by('lsad_code', r.ghrp_lsadc).display

        g = Geo(name=name, path_parent=state, parents=[state])

        GeoData(geo=g,
                total_pop=r.ghrp_p0020001,
                urban_pop=r.ghrp_p0020002,
                latitude=r.ghrp_intptlat,
                longitude=r.ghrp_intptlon,
                land_area=(r.ghrp_arealand * 1.0) / 10**6,
                water_area=(r.ghrp_areawatr * 1.0) / 10**6)

        glvl = GeoLevel(geo=g, level=SUBDIVISION2, designation=lsad)

        GeoID(level=glvl, standard=FIPS, code=r.ghrp_countyid)

        ansi = r.ghrp_countyns
        if ansi is not None and GeoID.tget((ANSI, ansi)) is None:
            GeoID(level=glvl, standard=ANSI, code=r.ghrp_countyns)

    # County equivalents in remaining U.S. territories
    # TODO: Find and add data (they do not show up as children without data)
    more_areas = (
        # fips     ansi      stusps  name                desig
        ('60010', '01805240', 'AS', 'Eastern District', 'district'),
        ('60020', '01805242', 'AS', "Manu'a District", 'district'),
        ('60030', '01805243', 'AS', 'Rose Island', 'island'),
        ('60040', '01805244', 'AS', 'Swains Island', 'island'),
        ('60050', '01805241', 'AS', 'Western District', 'district'),
        ('66010', '01802705', 'GU', 'Guam', 'county equivalent'),  # dup ansi
        ('69085', '01805245', 'MP', 'Northern Islands Municipality',
                                    'municipality'),
        ('69100', '01805246', 'MP', 'Rota Municipality', 'municipality'),
        ('69110', '01805247', 'MP', 'Saipan Municipality', 'municipality'),
        ('69120', '01805248', 'MP', 'Tinian Municipality', 'municipality'),
        ('74300', None,       'UM', 'Midway Islands', 'islands'),
        ('78010', '02378248', 'VI', 'St. Croix Island', 'island'),
        ('78020', '02378249', 'VI', 'St. John Island', 'island'),
        ('78030', '02378250', 'VI', 'St. Thomas Island', 'island'),
        # Sources:
        # www.census.gov/newsroom/releases/archives/2010_census/cb13-tps62.html
    )

    territory = None
    stusps = prior_stusps = None
    for fips, ansi, stusps, name, desig in more_areas:

        if stusps != prior_stusps:
            territory = us[stusps]
            print('\t{usps} - {name}'.format(usps=territory.abbrev,
                                             name=territory.name))
            prior_stusps = stusps

        g = Geo(name=name, path_parent=territory, parents=[territory])

        glvl = GeoLevel(geo=g, level=SUBDIVISION2, designation=desig)

        GeoID(level=glvl, standard=FIPS, code=fips)

        if ansi is not None and GeoID.tget((ANSI, ansi)) is None:
            GeoID(level=glvl, standard=ANSI, code=ansi)

    # TODO: Consolidate Guam county into Guam the territory


def load_subdivision3_geos(geo_session, session, sub1keys=None):
    '''
    Load SUBDIVISION3 geos

    Create SUBDIVISION3 geo for each valid county subdivision (cousub).
    In addition, create PLACE geos for cousubs meeting these criteria:
    1. Cousub is in a state with MCDs that serve as a governmental units
    2. Cousub has a (non-zero) ANSI code
    3. Cousub name does not contain a number

    I/O:
    geo_session: sqlalchemy session for geo database of US census data
    session: sqlalchemy session for Intertwine database
    sub1keys=None: sequence of state abbrevs to scope the data load
    '''
    CountySubdivisionRecord = namedtuple(
        'CountySubdivisionRecord',
        'ghrp_name, ghrp_lsadc, ghrp_statefp, '
        'ghrp_countyid, ghrp_countyns, ghrp_cousubid, ghrp_cousubns, '
        'ghrp_p0020001, ghrp_p0020002, ghrp_intptlat, ghrp_intptlon, '
        'ghrp_arealand, ghrp_areawatr')

    columns = derive_columns(classes=(GHRP,),
                             fields=CountySubdivisionRecord._fields)

    # U.S. county subdivisions including independent cities
    if sub1keys:
        statefps = [State.get_by('stusps', k).statefp for k in sub1keys]
        records = (geo_session.query(GHRP)
                   # State-County-Cousub
                   .filter(GHRP.sumlev == '060', GHRP.geocomp == '00',
                           GHRP.statefp.in_(statefps))
                   .order_by(GHRP.statefp, GHRP.countyid, GHRP.cousubid)
                   .values(*columns))
    else:
        records = (geo_session.query(GHRP)
                   # State-County-Cousub
                   .filter(GHRP.sumlev == '060', GHRP.geocomp == '00')
                   .order_by(GHRP.statefp, GHRP.countyid, GHRP.cousubid)
                   .values(*columns))

    us = Geo['us']
    state = None
    stusps = prior_stusps = None
    countyid = prior_countyid = None
    print('Loading county subdivisions and equivalents in...')
    for r in (CountySubdivisionRecord(*record) for record in records):

        # Invalid cousub (e.g. 'County subdivisions not defined')
        if r.ghrp_cousubns == '00000000':
            print(u'\t\t\tSkipping invalid cousub: {name} ({cousubid})'
                  .format(name=r.ghrp_name, cousubid=r.ghrp_cousubid))
            continue

        stusps = State.get_by('statefp', r.ghrp_statefp).stusps
        if stusps != prior_stusps:
            state = us[stusps]
            print(u'\t{stusps} - {name}'.format(stusps=state.abbrev,
                                                name=state.name))
            prior_stusps = stusps

        countyid = r.ghrp_countyid
        if countyid != prior_countyid:
            county = GeoID[(FIPS, r.ghrp_countyid)].level.geo
            print(u'\t\t{county_name} ({countyid}), {stusps}'.format(
                county_name=county.name, countyid=r.ghrp_countyid,
                stusps=state.abbrev))
            prior_countyid = countyid

        name, lsad = LSAD.deaffix(r.ghrp_name, r.ghrp_lsadc)

        print('\t\t\t' + name + ' (' + r.ghrp_cousubid + ')')

        # if name.lower() == 'st. albans':  # VT
        #     import pdb; pdb.set_trace()

        for _ in range(1):  # Single loop for exception flow control

            ############################################################
            #
            # Happy path: if no geo conflict, create a new cousub
            #
            try:
                cousub = Geo(name=name, path_parent=county,
                             parents=[county, state])

            except KeyRegisteredAndNoModify:
                pass  # Execution proceeds after else clause

            else:
                GeoData(geo=cousub,
                        total_pop=r.ghrp_p0020001, urban_pop=r.ghrp_p0020002,
                        latitude=r.ghrp_intptlat, longitude=r.ghrp_intptlon,
                        land_area=(r.ghrp_arealand * 1.0) / 10**6,
                        water_area=(r.ghrp_areawatr * 1.0) / 10**6)

                cousub_glvl = GeoLevel(geo=cousub, level=SUBDIVISION3,
                                       designation=lsad)

                GeoID(level=cousub_glvl, standard=FIPS, code=r.ghrp_cousubid)

                ansi = r.ghrp_cousubns
                if ansi is not None and GeoID.tget((ANSI, ansi)) is None:
                    GeoID(level=cousub_glvl, standard=ANSI, code=ansi)

                continue  # Execution proceeds after single loop

            ############################################################
            #
            # Conflict with cousub or cousub alias
            #
            cousub_conflict_key = Geo.create_key(name=name, path_parent=county)
            cousub_conflict = Geo[cousub_conflict_key]
            cousub_conflict_alias_targets = cousub_conflict.alias_targets

            ############################################################
            #
            # Attach new geo level to existing geo (only for D.C.)
            #
            try:
                # If conflict is an alias, set cousub to largest target
                cousub = (cousub_conflict if not cousub_conflict_alias_targets
                          else cousub_conflict_alias_targets[0])

                cousub_glvl = GeoLevel(geo=cousub, level=SUBDIVISION3,
                                       designation=lsad)

                print('\t\t\tAdding level to existing geo: {}'
                      .format(cousub_glvl.trepr()))  # DC only

                # If conflict is an alias of 2+ geos, something is wrong
                if len(cousub_conflict_alias_targets) > 1:
                    raise ValueError('Geo level attached to ambiguous geo')

            except KeyRegisteredAndNoModify:
                pass  # Execution proceeds after else clause

            else:
                GeoID(level=cousub_glvl, standard=FIPS, code=r.ghrp_cousubid)

                ansi = r.ghrp_cousubns
                if ansi is not None and GeoID.tget((ANSI, ansi)) is None:
                    GeoID(level=cousub_glvl, standard=ANSI, code=ansi)

                continue  # Execution proceeds after single loop

            ############################################################
            #
            # There are 2+ cousubs of the same name in the same county!
            # Use qualifiers to resolve conflicts and track via alias.
            # e.g. Cedar Falls city vs township, Black Hawk County, IA.
            # They will be LSAD-qualified and an alias in the conflict
            # namespace (without a qualifier) will point to them.
            #
            if cousub_conflict_alias_targets:
                cousub_alias = cousub_conflict

                ########################################################
                #
                # If cousub alias has 1 target, the target is a (cousub)
                # place, so try creating a new LSAD-qualified alias.
                #
                if len(cousub_conflict_alias_targets) == 1:
                    cousub_alias_target = cousub_conflict_alias_targets[0]
                    assert cousub_alias_target.levels.get(PLACE)
                    try:
                        Geo(name=name, path_parent=county,
                            qualifier=cousub_alias_target.levels[
                                SUBDIVISION3].designation,
                            alias_targets=[cousub_alias_target])
                    except KeyRegisteredAndNoModify:
                        pass

            else:
                cousub_conflict.qualifier = (
                    cousub_conflict.levels[SUBDIVISION3].designation)
                # Add alias in conflict namespace to point to conflicts
                cousub_alias = Geo(name=name, path_parent=county,
                                   alias_targets=[cousub_conflict])

            cousub = Geo(name=name, qualifier=lsad, path_parent=county,
                         aliases=[cousub_alias], parents=[county, state])

            print(u'\t\t\tCousubs with same name in {state}: {cousubs}'.format(
                state=state.abbrev,
                cousubs=(cousub_conflict.human_id, cousub.human_id)))

            GeoData(geo=cousub,
                    total_pop=r.ghrp_p0020001, urban_pop=r.ghrp_p0020002,
                    latitude=r.ghrp_intptlat, longitude=r.ghrp_intptlon,
                    land_area=(r.ghrp_arealand * 1.0) / 10**6,
                    water_area=(r.ghrp_areawatr * 1.0) / 10**6)

            cousub_glvl = GeoLevel(geo=cousub, level=SUBDIVISION3,
                                   designation=lsad)

            GeoID(level=cousub_glvl, standard=FIPS, code=r.ghrp_cousubid)

            ansi = r.ghrp_cousubns
            if ansi is not None and GeoID.tget((ANSI, ansi)) is None:
                GeoID(level=cousub_glvl, standard=ANSI, code=ansi)

            continue  # Execution proceeds after single loop

        # After single loop: execution proceeds here
        if (stusps in State.STATES_WITH_MCDS_AS_GOVERNMENTAL_UNITS and
                not Cousub.invalid_name_pattern.search(name)):
            create_place_from_cousub(cousub, county, state, lsad)


def create_place_from_cousub(cousub, county=None, state=None, lsad=None):
    '''
    Create place from county subdivision (cousub)

    Create place and aliases for resolving conflicts from cousub. The
    cousub becomes an alias targeting the new place. Only called if in
    state where MCDs serve as governmental unit and cousub name is valid

    I/O:
    cousub: cousub geo just created
    county=None: county geo that is path parent of the cousub
    state=None: state geo that is path parent of the county
    lsad=None: LSAD for the cousub
    '''
    name = cousub.name
    county = county or cousub.get_related_geos(
                    relation=PARENTS, level=SUBDIVISION2)[0]
    state = state or cousub.get_related_geos(
                    relation=PARENTS, level=SUBDIVISION1)[0]
    lsad = lsad or cousub.levels[SUBDIVISION3].designation

    # if name == 'Winnebago':  # MN
    #     import pdb; pdb.set_trace()
    # if name.lower() == 'union city':  # OH
    #     import pdb; pdb.set_trace()

    GeoLevel(geo=cousub, level=PLACE, designation=lsad)

    for _ in range(1):  # Single loop for exception flow control

        ################################################################
        #
        # Happy path: if no geo conflict, create a new place alias
        #
        try:
            # Temporarily an alias until promoted to target
            place = Geo(name=name, path_parent=state,
                        alias_targets=[cousub])

            continue  # Execution proceeds after single loop

        except KeyRegisteredAndNoModify:
            pass

        ################################################################
        #
        # Conflict with place or alias so create place (cousub alias)
        # with lsad qualifier
        #
        place_conflict_key = Geo.create_key(name=name, path_parent=state,
                                            alias_targets=[cousub])
        place_conflict = Geo[place_conflict_key]
        place_conflict_alias_targets = place_conflict.alias_targets

        if place_conflict_alias_targets:
            place_alias = place_conflict

        else:
            place_alias = resolve_cousub_place_conflict(place_conflict, cousub,
                                                        state, lsad)

        # Add cousub as target since place is yet to be promoted
        place_alias.add_alias_target(cousub)

        try:
            # Temporarily an alias until promoted to target
            place = Geo(name=name, qualifier=lsad, path_parent=state,
                        alias_targets=[cousub])

            print(u'\t\t\tPlaces with same name in {state}: {places}'
                  .format(state=state.abbrev, places=(
                    place_conflict.human_id, place.human_id)))

            continue  # Execution proceeds after single loop

        except KeyRegisteredAndNoModify:
            pass

        ############################################################
        #
        # Conflict with LSAD-qualified place or alias so change
        # qualifiers to '{LSAD} in {county}'
        #
        lsad_place_conflict_key = Geo.create_key(name=name, qualifier=lsad,
                                                 path_parent=state)
        lsad_place_conflict = Geo[lsad_place_conflict_key]
        lsad_place_conflict_alias_targets = (
            lsad_place_conflict.alias_targets)

        if lsad_place_conflict_alias_targets:
            lsad_place_alias = lsad_place_conflict

        else:
            lsad_place_conflict.qualifier = ' in '.join((
                lsad_place_conflict.levels[PLACE].designation,
                lsad_place_conflict.get_related_geos(
                    relation=PARENTS, level=SUBDIVISION2)[0].name))
            # Add alias in conflict namespace to point to conflicts
            lsad_place_alias = Geo(name=name, qualifier=lsad,
                                   path_parent=state,
                                   alias_targets=[lsad_place_conflict])

        # Add cousub as target since place is yet to be promoted
        lsad_place_alias.add_alias_target(cousub)
        # Temporarily an alias until promoted to target
        place = Geo(name=name, qualifier=' in '.join((lsad, county.name)),
                    path_parent=state, alias_targets=[cousub])

        print(u'\t\t\tPlaces with same name/lsad in {state}: {places}'
              .format(state=state.abbrev, places=(
                    lsad_place_conflict.human_id, place.human_id)))

        continue  # Execution proceeds after single loop

    # After single loop: execution proceeds here
    place.promote_to_alias_target()


def resolve_cousub_place_conflict(place_conflict, cousub, state, lsad):
    '''
    Resolve cousub place conflict and return alias to it

    Place conflict is not an alias, so resolve the conflict by giving it
    a qualifier. Also, create and return an alias in the conflict
    namespace targeting the resolved place conflict.

    I/O:
    place_conflict: existing place geo that conflicts with new place geo
    cousub: cousub geo whose place geo encountered the conflict
    state: state geo in which cousub resides
    lsad: LSAD for the cousub
    '''
    place_conflict_qualifier = place_conflict.levels[PLACE].designation
    try:
        # If place conflict is already qualified by LSAD, raise
        if place_conflict.qualifier == place_conflict_qualifier:
            raise ValueError
        # Raise if qualified conflict itself conflicts
        place_conflict.qualifier = place_conflict_qualifier

    except ValueError:
        ################################################################
        #
        # LSAD-qualified place conflict (QPC) itself conflicts with an
        # existing place or alias. Resolve by qualifying by county too.
        #
        # Example: Winnebago, MN
        # Winnebago in Faribault County (WFC) conflicts with Winnebago
        # in Houston County (WHC). But when WFC is qualified with city,
        # it conflicts with 'Winnebago City', also in Faribault County.
        #
        # Resolution:
        # Geo[u'us/mn/winnebago'] alias targeting:
        #     Geo[u'us/mn/winnebago_city_in_faribault_county']
        #     Geo[u'us/mn/winnebago_township']
        # Geo[u'us/mn/winnebago_city'] alias targeting:
        #     Geo[u'us/mn/winnebago_city_in_faribault_county']
        #     Geo[u'us/mn/winnebago_city_township_in_faribault_county']
        #
        qualified_place_conflict_key = Geo.create_key(
            name=place_conflict.name, path_parent=state,
            qualifier=place_conflict_qualifier)
        qpc = Geo[qualified_place_conflict_key]
        qpc_alias_targets = qpc.alias_targets

        if qpc_alias_targets:
            qualified_place_alias = qpc

        else:
            qpc.qualifier = ' in '.join((
                qpc.levels[PLACE].designation,
                qpc.get_related_geos(
                    relation=PARENTS, level=SUBDIVISION2)[0].name))
            # Add alias in conflict namespace to point to conflicts
            qualified_place_alias = Geo(
                name=place_conflict.name, path_parent=state,
                qualifier=place_conflict_qualifier,
                alias_targets=[qpc])

        if qpc is place_conflict:
            ############################################################
            #
            # Place conflict was already LSAD-qualified, so the conflict
            # was qualified by county. So force place to be qualified by
            # county too by creating an LSAD-qualified alias to cousub.
            #
            # Example: Union City, OH
            # There are 28 Union, OHs, of which 27 are townships and 1
            # is a city in Miami County. In addition, a Union City
            # township in Montgomery County conflicts with Union city.
            #
            # Resolution:
            # Geo[u'us/oh/union'] alias targeting 28 geos, including:
            #     Geo[u'us/oh/union_city_in_miami_county']
            # Geo[u'us/oh/union_city'] alias targeting:
            #     Geo[u'us/oh/union_city_in_miami_county']
            #     Geo[u'us/oh/union_city_township_in_montgomery_county']
            # Geo[u'us/oh/union_city_township'] alias targeting:
            #     Geo[u'us/oh/union_city_township_in_montgomery_county']
            #
            try:
                lsad_place_alias = Geo(name=cousub.name, qualifier=lsad,
                                       path_parent=state,
                                       alias_targets=[cousub])
            except KeyRegisteredAndNoModify:
                lsad_place_alias_key = Geo.create_key(
                    name=cousub.name, qualifier=lsad, path_parent=state)
                lsad_place_alias = Geo[lsad_place_alias_key]
                assert lsad_place_alias.alias_targets
                lsad_place_alias.add_alias_target(cousub)

        else:
            # Add place conflict as target
            qualified_place_alias.add_alias_target(place_conflict)

            place_conflict.qualifier = ' in '.join((
                place_conflict.levels[PLACE].designation,
                place_conflict.get_related_geos(relation=PARENTS,
                                                level=SUBDIVISION2)[0].name))

        print(u'\t\t\tPlace conflict itself conflicts when '
              'qualified by lsad in {state}: {places}'
              .format(state=state.abbrev, places=(
               qpc.human_id, place_conflict.human_id)))

    finally:
        try:
            # Add alias in conflict namespace to point to conflicts
            place_alias = Geo(name=cousub.name, path_parent=state,
                              alias_targets=[place_conflict])

        except KeyRegisteredAndNoModify:
            place_alias_key = Geo.create_key(name=cousub.name,
                                             path_parent=state)
            place_alias = Geo[place_alias_key]
            place_alias.add_alias_target(place_conflict)

    return place_alias


def load_place_geos(geo_session, session):

    PlaceRecord = namedtuple('PlaceRecord',
                             'place_name, lsad_description, '
                             'ghrp_statefp, ghrp_countyid, ghrp_countycc, '
                             'ghrp_placeid, ghrp_placens, '
                             'ghrp_p0020001, ghrp_p0020002, '
                             'place_intptlat, place_intptlong, '
                             'ghrp_arealand, ghrp_areawatr')

    columns = derive_columns(classes=(Place, LSAD, GHRP),
                             fields=PlaceRecord._fields)

    # U.S. places by county equivalent
    records = (geo_session.query(GHRP)
                          .join(GHRP.place)
                          .join(Place.lsad)
                          .filter(GHRP.sumlev == '155',
                                  GHRP.geocomp == '00',
                                  # GHRP.statefp.in_(['48', '11'])
                                  )
                          .order_by(GHRP.placeid,
                                    desc(GHRP.p0020001))
                          .values(*columns))

    records = PeekableIterator(records)
    statefp = prior_statefp = None  # State FIPS codes
    placeid = prior_placeid = None  # Place FIPS codes
    state = None
    counties = []
    total_pop = urban_pop = 0
    land_area = water_area = 0
    conflicts = {}
    consolidated = {}
    print('Loading places in...')
    for r in (PlaceRecord(*record) for record in records):

        statefp = r.ghrp_statefp
        # If it's a new state, update variables
        if statefp != prior_statefp:
            state = GeoID[(FIPS, statefp)].level.geo
            print('\t' + state.name)
            prior_statefp = statefp

        placeid = r.ghrp_placeid

        # If it's a new place, reset variables
        if placeid != prior_placeid:
            counties = []
            total_pop = urban_pop = 0
            land_area = water_area = 0
            prior_placeid = placeid

        county = GeoID[(FIPS, r.ghrp_countyid)].level.geo

        if county is not None:
            counties.append(county)
        total_pop += r.ghrp_p0020001
        urban_pop += r.ghrp_p0020002
        land_area += (r.ghrp_arealand * 1.0) / 10**6
        water_area += (r.ghrp_areawatr * 1.0) / 10**6

        # We're on the last record for the current place, so create geo
        if (not records.has_next() or
                PlaceRecord(*records.peek()).ghrp_placeid != placeid):

            desig = r.lsad_description
            desig = desig.split(' (actual text)')[0]
            desig = desig.split(' (prefix)')[0]
            desig = desig.split(' (suffix)')[0]
            place_name = r.place_name
            if desig != '':
                place_name = place_name.split(desig)[0].strip()
            qualifier = None

            print('\t\t' + place_name + '(' + placeid + ')')

            # check for existing place with same key
            key = Geo.create_key(name=place_name, path_parent=state)
            existing = Geo.tget(key)
            if existing is not None:
                if existing.alias_target is None:
                    # if existing conflict is a place, rename it, make
                    # an alias to it, and keep track of its population
                    if (existing.levels.get(PLACE, None) is not None):
                        existing_desig = existing.levels[PLACE].designation
                        existing.qualifier = (existing_desig + ' in ' +
                                              existing.parents[0].name)
                        alias = Geo(name=place_name,
                                    path_parent=state,
                                    alias_target=existing)
                        conflicts[key] = existing.data.total_pop
                    # if existing conflict is a parent county, just add
                    # a geo level for the place to the county
                    elif (existing.levels.get(SUBDIVISION2, None) is not None):
                        if existing not in counties:
                            raise NameError('place key conflicts with '
                                            'subdivision2 key, yet place is '
                                            'not in subdivision2')
                        glvl = GeoLevel(geo=existing,
                                        level=PLACE,
                                        designation=desig)
                        GeoID(level=glvl, standard=FIPS, code=placeid)
                        placens = r.ghrp_placens
                        if GeoID.tget((ANSI, placens)) is None:
                            GeoID(
                                level=glvl, standard=ANSI, code=placens)

                        continue
                    else:
                        raise NameError('key conflict with geo that is '
                                        'neither a place nor subdivision2')

                assert len(counties) > 0
                qualifier = desig + ' in ' + counties[0].name

            g = Geo(name=place_name,
                    qualifier=qualifier,
                    path_parent=state,
                    parents=counties + [state])
            GeoData(geo=g,
                    total_pop=total_pop,
                    urban_pop=urban_pop,
                    latitude=r.place_intptlat,
                    longitude=r.place_intptlong,
                    land_area=land_area,
                    water_area=water_area)
            glvl = GeoLevel(geo=g, level=PLACE, designation=desig)
            GeoID(level=glvl, standard=FIPS, code=placeid)
            placens = r.ghrp_placens
            if GeoID.tget((ANSI, placens)) is None:
                GeoID(level=glvl, standard=ANSI, code=placens)

            # Update alias to point at the geo with the largest pop
            # TODO: convert alias_target to alias_targets and order by
            # population, descending
            if (existing is not None and total_pop > conflicts[key]):
                alias.alias_target = g
                conflicts[key] = total_pop

            # If consolidated county or independent city, add to list
            if r.ghrp_countycc == 'H6' or r.ghrp_countycc == 'C7':
                places = consolidated.get(county, None)
                if places is None:
                    consolidated[county] = [g]
                else:
                    consolidated[county].append(g)

    # TODO: Handle unincorporated county remainder special case
    # records = geo_session.query(GHRP).filter(GHRP.sumlev == '070',
    #                                          GHRP.placefp == '99999').all()
    # Need to sum remainders across county subdivisions within a county

    # Add missing consolidated counties
    dc_county = GeoID[(FIPS, '11001')].level.geo
    consolidated[dc_county] = dc_county.children.all()
    # Yakutat City and Borough contains Yakutat CDP
    # yak_cab = GeoID[(FIPS, '02282')].level.geo
    # consolidated[yak_cab] = yak_cab.children.all()

    for county, places in consolidated.items():

        if len(places) > 1:

            # If a place is a county balance, correct the name and
            # designation, alias the county, and promote it
            # Fixes 6 of 10 consolidated places with lsad_code == '00':
            #     Athens-Clarke County, GA
            #     Augusta-Richmond County, GA
            #     Indianapolis, IN
            #     Louisville/Jefferson County, KY
            #     Butte-Silver Bow, MT
            #     Nashville-Davidson, TN
            balance = None
            for place in places:
                if place.name.find('(balance)') > -1:
                    balance = place
                    break
            if balance is not None:
                # Obtain capitalized portion of the name
                bal_words = balance.name.split()
                end = len(bal_words)
                for i, word in enumerate(bal_words):
                    first_letter = ord(word[0])
                    if first_letter < ord('A') or first_letter > ord('Z'):
                        end = i
                        break

                base_name = ' '.join(bal_words[:end])
                place_name = bal_words[0].split('-')[0]
                place_name = place_name.split('/')[0]

                balance.name = base_name + ' (balance)'
                balance.levels[PLACE].designation = (
                                        'consolidated government (balance)')
                # balance geos only related to immediate parents
                balance.parents.remove(balance.path_parent)
                GeoLevel(geo=county, level=PLACE, designation='city')
                alias = Geo(name=base_name, alias_target=county)
                if place_name != base_name:
                    Geo(name=place_name, alias_target=county)
                alias.promote_to_alias_target()

            continue
        place = places[0]
        county_parents = [p for p in place.parents
                          if p.levels.get(SUBDIVISION2, None) is not None]

        # The counties of NYC
        if len(county_parents) != 1:
            continue
        assert county_parents[0] == county

        # Possible because county remainders are not yet loaded
        if place.data.total_pop != county.data.total_pop:
            continue

        # Consolidate geos for each 1:1 consolidated county/place
        GeoData.unregister(place.data)
        place.data = None

        # Fix 3 of 10 consolidated places with lsad_code == '00':
        #     Carson City, NV
        #     Anaconda-Deer Lodge County, MT
        #     Hartsville/Trousdale County, TN
        if place.levels[PLACE].designation == '':
            place.levels[PLACE].designation = u'city'

        for glvl in place.levels.values():
            glvl.geo = county

        place.parents = []
        # Move any children of the place to the county
        for child in place.children.all():
            if county not in child.parents:
                child.parents = [county] + child.parents

        # Make the place an alias for the county
        place.alias_target = county
        # Reverse the relationship, making the county the alias
        place.promote_to_alias_target()

    # Combine with DC the district and fix aliases
    us = Geo['us']
    dc = us['dc']
    w = GeoID[(FIPS, '1150000')].level.geo  # Washington, DC (place)
    GeoData.unregister(w.data)
    w.data = None
    w.levels[SUBDIVISION2].geo = dc
    w.levels[PLACE].geo = dc
    w.parents = []
    w.alias_target = dc
    wdc = dc['district_of_columbia']
    wdc.name = 'Washington, D.C.'
    wdc.path_parent = us

    # Clean up remaining place (1 of 10) with lsad_code == '00':
    # Milford city (balance), CT
    # Parent is a city (not county!):
    # Milford; city [MISSING]
    #     Milford (balance); city balance
    #     Woodmont; borough
    #     Devon; unincorporated village [MISSING]
    ct = Geo['us/ct']
    nhc = Geo['us/ct/new_haven_county']
    wm = Geo['us/ct/woodmont']
    mfb = Geo['us/ct/milford_city_(balance)']

    mf = Geo(name='Milford', path_parent=ct, parents=[nhc, ct],
             children=[mfb, wm])  # sets geo data based on children
    mfb.levels[PLACE].geo = mf  # move levels and ids
    mf.levels[PLACE].designation = 'city'

    mfb.name = 'Milford (balance)'
    GeoLevel(geo=mfb, level=PLACE, designation='city balance')
    mfb.parents = [mf]  # balance geos only related to immediate parents

    # Fix missing tilde in Española, NM. Note: ñ appears correctly elsewhere:
    # Peñasco, NM; Cañones, NM; La Cañada Flintridge, CA; etc.
    esp = Geo[u'us/nm/espanola']
    esp.name = u'Espa\xf1ola'  # Geo[u'us/nm/espa\xf1ola']


def load_cbsa_geos(geo_session, session):
    CBSARecord = namedtuple('CBSARecord',
                            'cbsa_cbsa_code, cbsa_cbsa_name, cbsa_cbsa_type, '
                            'cbsa_csa_code, cbsa_csa_name, '
                            'ghrp_statefp, ghrp_countyid, ghrp_placeid, '
                            'ghrp_p0020001, ghrp_p0020002')

    columns = derive_columns(classes=(CBSA, GHRP),
                             fields=CBSARecord._fields)

    # U.S. places by county equivalent with CBSA/CSA data
    records = (geo_session.query(GHRP)
                          .join(GHRP.county)
                          .join(County.cbsa)
                          .filter(
                              GHRP.sumlev == '155',
                              GHRP.geocomp == '00',
                              # GHRP.statefp.in_(['33', '44', '9', '11']),
                              # GHRP.statefp == '48',  # Texas
                              # CBSA.cbsa_code == '12420',  # Greater Austin
                              )
                          .order_by(
                              CBSA.csa_code,
                              CBSA.cbsa_code,
                              # CBSA.metro_division_code,
                              desc(GHRP.p0020001))
                          .values(*columns))

    records = PeekableIterator(records)

    us = Geo['us']
    cbsa_code = prior_cbsa_code = ''
    csa_code = prior_csa_code = ''
    cbsas_with_unnamed_main_places = {}
    cbsas_without_main_places = {}
    cbsa_aliases = {}
    # cbsas_not_aliased_by_top_place = {}
    csa = None

    print('Loading CBSAs and CSAs...')
    for r in (CBSARecord(*record) for record in records):

        # If it's a new CBSA, initialize variables
        cbsa_code = r.cbsa_cbsa_code
        if cbsa_code != prior_cbsa_code:
            cbsa = None
            cbsa_states = {}  # CBSA state pop, indexed by state geo
            cbsa_counties = {}  # CBSA county pop, indexed by county geo
            cbsa_places = {}  # CBSA place pop, indexed by place geo
            cbsa_place_1 = cbsa_place_2 = None
            # cbsa_non_cdp_1 = cbsa_non_cdp_2 = None
            cbsa_main_place = None
            prior_cbsa_code = cbsa_code

            # If it's a new CSA, initialize variables
            csa_code = r.cbsa_csa_code
            if csa_code != prior_csa_code:
                csa = None
                csa_states = {}  # CSA state pop, indexed by state geo
                csa_counties = {}  # CSA county pop, indexed by county geo
                csa_places = {}  # CSA place pop, indexed by place geo
                csa_cbsa_main_places = {}  # main places indexed by CBSA geo
                csa_cbsa_1 = csa_cbsa_2 = None
                csa_main_cbsa = None
                prior_csa_code = csa_code

        statefp = r.ghrp_statefp
        state = GeoID[(FIPS, statefp)].level.geo
        if state.levels.get(SUBDIVISION1, None) is None:
            raise ValueError('State {!r} missing geo level'.format(state))
        if state.alias_target is not None:
            raise ValueError('State {!r} is an alias'.format(state))
        # Assemble pop of state within CBSA
        if cbsa_states.get(state, None) is None:
            cbsa_states[state] = 0
        cbsa_states[state] += r.ghrp_p0020001

        countyid = r.ghrp_countyid
        county = GeoID[(FIPS, countyid)].level.geo
        if county.levels.get(SUBDIVISION2, None) is None:
            raise ValueError('County {!r} missing geo level'.format(county))
        if county.alias_target is not None:
            raise ValueError('County {!r} is an alias'.format(county))
        # Store pop of county (CBSAs consist of whole counties)
        if cbsa_counties.get(county, None) is None:
            cbsa_counties[county] = county.data.total_pop

        placeid = r.ghrp_placeid
        place = GeoID[(FIPS, placeid)].level.geo
        if place.levels.get(PLACE, None) is None:
            raise ValueError('Place {!r} missing geo level'.format(place))
        if place.alias_target is not None:
            raise ValueError('Place {!r} is an alias'.format(place))
        # Assemble pop of place within CBSA
        if cbsa_places.get(place, None) is None:
            cbsa_places[place] = 0
        cbsa_places[place] += r.ghrp_p0020001

        # Add consolidated counties with children as places
        # (those without children are already added)
        if (county.levels.get(PLACE, None) is not None and
                cbsa_places.get(county, None) is None):
            cbsa_places[county] = county.data.total_pop

        # We're on the last record for the current CBSA, so create geo
        if (not records.has_next() or
                CBSARecord(*records.peek()).cbsa_cbsa_code != cbsa_code):

            cbsa_name = r.cbsa_cbsa_name
            print(u'\t\tCBSA: {name} ({code})'.format(name=cbsa_name,
                                                      code=cbsa_code))

            cbsa = Geo(name=cbsa_name + ' Area',
                       uses_the=True,
                       path_parent=us,
                       parents=cbsa_states.keys(),
                       children=cbsa_counties.keys() + cbsa_places.keys(),
                       child_data_level=SUBDIVISION2)  # Sum from counties

            cbsa_glvl = GeoLevel(geo=cbsa,
                                 level=CORE_AREA,
                                 designation=r.cbsa_cbsa_type.lower())
            GeoID(level=cbsa_glvl, standard=CBSA_2010, code=cbsa_code)

            for place in cbsa_places:
                if (cbsa_place_1 is None or
                        cbsa_places[place] > cbsa_places[cbsa_place_1]):
                    cbsa_place_1, cbsa_place_2 = place, cbsa_place_1
                elif (cbsa_place_2 is None or
                        cbsa_places[place] > cbsa_places[cbsa_place_2]):
                    cbsa_place_2 = place

            #     # Prioritize non-CDPs over CDPs
            #     # Removed because these are actually exceptions
            #     if place.levels[PLACE].designation == 'CDP':
            #         continue
            #     if (cbsa_non_cdp_1 is None or
            #             cbsa_places[place] > cbsa_places[cbsa_non_cdp_1]):
            #         cbsa_non_cdp_1, cbsa_non_cdp_2 = (
            #             place, cbsa_non_cdp_1)
            #     elif (cbsa_non_cdp_2 is None or
            #             cbsa_places[place] > cbsa_places[cbsa_non_cdp_2]):
            #         cbsa_non_cdp_2 = place
            # if cbsa_non_cdp_1 is not None:
            #     cbsa_place_1 = cbsa_non_cdp_1
            #     cbsa_place_2 = cbsa_non_cdp_2

            cbsa_main_places = [cbsa_place_1]
            if (cbsa_place_2 is not None and (cbsa_places[cbsa_place_1] <=
                                              cbsa_places[cbsa_place_2] * 1)):
                cbsa_main_places.append(cbsa_place_2)

            name_match = False
            for place in cbsa_main_places:
                place_geos = place.aliases.all()
                place_geos.insert(0, place)
                for geo in place_geos:
                    if cbsa_name.find(geo.name) > -1:
                        name_match = True
                        cbsa_main_place = place
                        break
            if not name_match:
                cbsa_main_place = cbsa_main_places[0]

            if cbsa_main_place is not None and not name_match:
                cbsas_with_unnamed_main_places[cbsa] = (
                        cbsa_places, cbsa_main_place)

            if cbsa_main_place is None:
                cbsas_without_main_places[cbsa] = (
                    (cbsa_place_1, cbsa_places[cbsa_place_1]),
                    (cbsa_place_2, cbsa_places[cbsa_place_2]))
                continue

            if csa_code != '':

                # States can be in multiple CBSAs in a CSA
                for state in cbsa_states:
                    if csa_states.get(state, None) is None:
                        csa_states[state] = 0
                    csa_states[state] += cbsa_states[state]

                # Counties are always wholly contained by CBSAs
                csa_counties.update(cbsa_counties)

                # Places can be in multiple CBSAs in a CSA
                for place in cbsa_places:
                    if csa_places.get(place, None) is None:
                        csa_places[place] = 0
                    csa_places[place] += cbsa_places[place]

                csa_cbsa_main_places[cbsa] = cbsa_main_place

                # Find top 2 CBSAs in CSA
                if (csa_cbsa_1 is None or
                        cbsa.data.total_pop > csa_cbsa_1.data.total_pop):
                    csa_cbsa_1, csa_cbsa_2 = cbsa, csa_cbsa_1
                elif (csa_cbsa_2 is None or
                        cbsa.data.total_pop > csa_cbsa_2.data.total_pop):
                    csa_cbsa_2 = cbsa

                # We're on the last record for a valid CSA, so create geo
                if (not records.has_next() or
                        CBSARecord(*records.peek()).cbsa_csa_code != csa_code):

                    csa_name = r.cbsa_csa_name
                    print(u'\t\tCSA: {name} ({code})'.format(name=csa_name,
                                                             code=csa_code))

                    csa = Geo(name='Greater ' + csa_name + ' Area',
                              uses_the=True,
                              path_parent=us,
                              parents=csa_states.keys(),
                              children=(csa_cbsa_main_places.keys() +
                                        csa_counties.keys() +
                                        csa_places.keys()),
                              child_data_level=CORE_AREA)  # Sum from cbsas

                    csa_glvl = GeoLevel(geo=csa,
                                        level=COMBINED_AREA,
                                        designation='CSA')
                    GeoID(level=csa_glvl, standard=CSA_2010, code=csa_code)

                    if (csa_cbsa_2 is None or
                        csa_cbsa_1.data.total_pop >
                            csa_cbsa_2.data.total_pop * 1):
                        csa_main_cbsa = csa_cbsa_1

                    # CSA aliases
                    csa_main_place = csa_cbsa_main_places[csa_main_cbsa]
                    csa_mp_name = csa_main_place.name
                    csa_mp_abbrev = csa_main_place.abbrev

                    for csa_state in csa_states.iterkeys():

                        greater_csa_alias = (
                            Geo(name='Greater ' + csa_mp_name,
                                abbrev=('Greater ' + csa_mp_abbrev
                                        if csa_mp_abbrev else None),
                                path_parent=csa_state,
                                alias_target=csa,
                                uses_the=False))

                        greater_csa_area_alias = (
                            Geo(name=('Greater ' + csa_mp_name + ' Area'),
                                abbrev=('Greater ' + csa_mp_abbrev + ' Area'
                                        if csa_mp_abbrev else None),
                                path_parent=csa_state,
                                alias_target=csa,
                                uses_the=True))

                        if csa_state is csa_main_place.path_parent:
                            new_csa_target = greater_csa_alias

                    new_csa_target.promote_to_alias_target()

            # Ensure we're not in a CSA or we've just created a CSA.
            # CBSA aliases are created after the CSA (if any) because
            # the CSA is named 'Greater X' and the largest CBSA in the
            # CSA is named 'X Area' to distinguish it from the CSA.
            if not (csa_code == '' or csa):
                continue

            cbsa_targets = csa_cbsa_main_places.iterkeys() if csa else (cbsa, )

            for cbsa_target in cbsa_targets:

                if csa:
                    cbsa_main_place = csa_cbsa_main_places[cbsa_target]
                    alias_states = (
                        p for p in cbsa_target.parents
                        if p.levels.get(SUBDIVISION1, None))
                else:
                    alias_states = cbsa_states.iterkeys()

                cbsa_mp_name = cbsa_main_place.name
                cbsa_mp_abbrev = cbsa_main_place.abbrev

                for alias_state in alias_states:

                    if ((csa and csa_main_cbsa is cbsa_target) or
                        cbsa_target.levels[CORE_AREA].designation ==
                            'micropolitan statistical area'):
                        cbsa_area_alias = (
                            Geo(name=cbsa_mp_name + ' Area',
                                abbrev=(cbsa_mp_abbrev + ' Area'
                                        if cbsa_mp_abbrev else None),
                                path_parent=alias_state,
                                alias_target=cbsa_target,
                                uses_the=True))

                        if alias_state is cbsa_main_place.path_parent:
                            new_cbsa_target = cbsa_area_alias
                    else:
                        cbsa_area_alias = (
                            Geo(name=cbsa_mp_name + ' Area',
                                abbrev=(cbsa_mp_abbrev + ' Area'
                                        if cbsa_mp_abbrev else None),
                                path_parent=alias_state,
                                alias_target=cbsa_target,
                                uses_the=True))

                        greater_cbsa_alias = (
                            Geo(name='Greater ' + cbsa_mp_name,
                                abbrev=('Greater ' + cbsa_mp_abbrev
                                        if cbsa_mp_abbrev else None),
                                path_parent=alias_state,
                                alias_target=cbsa_target,
                                uses_the=False))

                        greater_cbsa_area_alias = (
                            Geo(name='Greater ' + cbsa_mp_name + ' Area',
                                abbrev=('Greater ' + cbsa_mp_abbrev + ' Area'
                                        if cbsa_mp_abbrev else None),
                                path_parent=alias_state,
                                alias_target=cbsa_target,
                                uses_the=True))

                        if alias_state is cbsa_main_place.path_parent:
                            new_cbsa_target = greater_cbsa_alias

                new_cbsa_target.promote_to_alias_target()

    # Add proper DC CBSA alias and promote
    dc_dc_area = Geo['us/dc/dc_area']
    dc_area = Geo(name=dc_dc_area.name,
                  abbrev=dc_dc_area.abbrev,
                  path_parent=us,
                  alias_target=dc_dc_area.alias_target,
                  uses_the=True)
    dc_area.promote_to_alias_target()

    # Add proper DC CSA aliases and promote
    dc_greater_dc = Geo['us/dc/greater_dc']
    greater_dc = Geo(name=dc_greater_dc.name,
                     abbrev=dc_greater_dc.abbrev,
                     path_parent=us,
                     alias_target=dc_greater_dc.alias_target,
                     uses_the=False)
    dc_greater_dc_area = Geo['us/dc/greater_dc_area']
    greater_dc_area = Geo(name=dc_greater_dc_area.name,
                          abbrev=dc_greater_dc_area.abbrev,
                          path_parent=us,
                          alias_target=dc_greater_dc_area.alias_target,
                          uses_the=False)
    greater_dc.promote_to_alias_target()

    print('CBSAs with unnamed main places...')
    for cbsa, (cbsa_places, cbsa_main_place) in (
                                cbsas_with_unnamed_main_places.items()):
        sorted_places = sorted(cbsa_places.keys(),
                               key=lambda p: cbsa_places[p],
                               reverse=True)
        print(u'\t{cbsa}:'.format(cbsa=cbsa.trepr()))
        for i, place in enumerate(sorted_places):
            if i == 10:
                print('\t\t(10 of {} places)'.format(len(sorted_places)))
                break
            cbsa_pop = cbsa_places[place]
            pop_total = place.data.total_pop
            print (u'\t\t{place}{main}: {cbsa_pop:,}'.format(
                    place=place.trepr(),
                    main='*' if place == cbsa_main_place else '',
                    cbsa_pop=cbsa_pop) +
                   (' of {pop_total:,}'.format(
                    pop_total=pop_total) if cbsa_pop != pop_total else ''))

    print('CBSAs without main places...')
    for cbsa, (p1_tuple, p2_tuple) in cbsas_without_main_places.items():
        p1_geo, p1_pop = p1_tuple
        p2_geo, p2_pop = p2_tuple
        p1_total, p2_total = p1_geo.data.total_pop, p2_geo.data.total_pop
        print(u'\t{cbsa}:'.format(cbsa=cbsa.trepr()))
        print(
            u'\t\t{p1_geo}: {p1_pop:,}'.format(
                p1_geo=p1_geo.trepr(),
                p1_pop=p1_pop) +
            (' of {p1_total:,}'.format(
                p1_total=p1_total) if p1_pop != p1_total else ''))
        print(
            u'\t\t{p2_geo}: {p2_pop:,} of {p2_total:,}'.format(
                p2_geo=p2_geo.trepr(),
                p2_pop=p2_pop) +
            (' of {p2_total:,}'.format(
                p2_total=p2_total) if p2_pop != p2_total else ''))

if __name__ == '__main__':
    # Session for geo.db, which contains the geo source data
    geo_dsm = DataSessionManager(db_config=DevConfig.GEO_DATABASE,
                                 ModelBases=[BaseGeoDataModel])
    geo_session = geo_dsm.session
    extend_declarative_base(BaseGeoDataModel, session=geo_session)

    # Session for main Intertwine db, where geo data is loaded
    db = Manager(Model=BaseGeoModel, config=DevConfig)
    session = db.session
    extend_declarative_base(BaseGeoModel, session=session)
    db.create_all()

    Trackable.register_existing(session, Geo, GeoData, GeoLevel, GeoID)
    Trackable.clear_updates()

    load_geos(geo_session, session)
