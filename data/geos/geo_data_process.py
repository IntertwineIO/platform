#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''Loads geo data into Intertwine'''
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

from collections import Counter, defaultdict, namedtuple

from sqlalchemy import desc
from alchy import Manager
from alchy.model import extend_declarative_base

from config import DevConfig
from data.data_process import DataSessionManager
from data.geos.models import (BaseGeoDataModel, LSAD, GHRP,
                              State, CBSA, County, Cousub, Place)
from intertwine.trackable import Trackable
from intertwine.trackable.exceptions import (KeyMissingFromRegistry,
                                             KeyRegisteredAndNoModify)
from intertwine.utils.structures import PeekableIterator
from intertwine.utils.tools import add_leading_zeros
from intertwine.geos.models import (
    BaseGeoModel, Geo, GeoData, GeoLevel, GeoID,
    PARENTS, CHILDREN,  # PATH_CHILDREN, ALIASES, ALIAS_TARGETS,
    COUNTRY, SUBDIVISION1, SUBDIVISION2, SUBDIVISION3, PLACE, SUBPLACE,
    CORE_AREA, COMBINED_AREA,
    FIPS, ANSI, ISO_A2, ISO_A3, ISO_N3, CSA_2010, CBSA_2010)
from intertwine.utils.space import Area, GeoLocation

COUNTY_LSAD_AS_QUALIFIER = False

GHRP_DATA_FIELDS = GeoData.Record(*GHRP.DATA_FIELDS)
PREFIXED_GHRP_DATA_FIELDS = GeoData.Record(
    *('_'.join((GHRP.__name__.lower(), f)) for f in GHRP_DATA_FIELDS))

invalid_cousub_name = Cousub.invalid_name_pattern.search


def define_record(name, *fields):
    '''
    Obtain namedtuple class and SQLAlchemy columns given name and fields

    I/O:
    name: the name to be given to the namedtuple class for the record
    fields: a sequence of field strings or a single string containing
    multiple comma-delimited fields (similar to namedtuple)

    Each field string must be in this form: <ClassName>.<column_name>
    Each namedtuple field takes this form: <classname>_<column_name>

    Example: 'County.aland_sqmi' is mapped to 'county_aland_sqmi'
    '''
    if len(fields) == 1 and ',' in fields[0]:
        fields = fields[0].split(',')

    class_column_name_pairs = [field.strip().split('.') for field in fields]

    columns = [getattr(globals()[class_name], column_name)
               for class_name, column_name in class_column_name_pairs]

    tuple_fields = ('_'.join((class_name.lower(), column_name))
                    for class_name, column_name in class_column_name_pairs)

    namedtuple_class = namedtuple(name, tuple_fields)

    return namedtuple_class, columns


def find_non_place_cousubs(geo=None, include_all=False):
    '''Utility to find non-place cousubs'''
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
                    int(cousub.name[0])  # non-integers raise ValueError
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
    '''Load geos for the US'''
    load_country_geos(geo_session, session)
    load_subdivision1_geos(geo_session, session)
    load_subdivision2_geos(geo_session, session)
    load_subdivision3_geos(geo_session, session)
    load_place_geos(geo_session, session)
    load_cbsa_geos(geo_session, session)
    load_manual_fixes(geo_session, session)

    return Trackable.catalog_updates()


def load_country_geos(geo_session, session):
    '''Load COUNTRY geos - US and USA alias'''
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


def load_subdivision1_geos(geo_session, session, sub1keys=None):
    '''Load SUBDIVISION1 geos'''
    load_states(geo_session, session, sub1keys)
    load_territories(geo_session, session, sub1keys)
    update_us_data()


def load_states(geo_session, session, sub1keys=None):
    '''Load U.S. states plus DC and Puerto Rico'''
    base_query = (
        geo_session.query(GHRP).filter(GHRP.sumlev == '040',
                                       GHRP.geocomp == '00'))

    if sub1keys:
        if not (set(sub1keys) - State.SMALL_TERRITORIES):
            return
        statefps = {State.get_by('stusps', k).statefp for k in sub1keys}
        base_query = base_query.filter(GHRP.statefp.in_(statefps))

    records = base_query.all()

    us = Geo['us']
    print('Loading states, DC, and Puerto Rico...')

    for r in records:
        state = r.state
        print('{usps} - {name}'.format(usps=state.stusps, name=state.name))

        data_record = GeoData.extract_data(r, GHRP_DATA_FIELDS)

        geo = Geo(name=state.name, abbrev=state.stusps, path_parent=us,
                  parents=[us])

        GeoData(geo=geo, **data_record._asdict())

        glvl = GeoLevel(geo=geo, level=SUBDIVISION1, designation=State.STATE)

        GeoID(level=glvl, standard=FIPS, code=r.statefp)
        GeoID(level=glvl, standard=ANSI, code=r.statens)

    if not sub1keys or 'PR' in sub1keys:
        # Correct Puerto Rico designation
        pr = us['pr']
        pr.levels[SUBDIVISION1].designation = State.TERRITORY

    if not sub1keys or 'DC' in sub1keys:
        # Correct Washington, D.C. designation and create alias
        dc = us['dc']
        dc.levels[SUBDIVISION1].designation = State.FEDERAL_DISTRICT
        Geo(name='Washington, D.C.', path_parent=us, alias_targets=[dc])


def load_territories(geo_session, session, sub1keys=None):
    '''
    Load U.S. territories, except for Puerto Rico
    Sources:
    www.census.gov/newsroom/releases/archives/2010_census/cb13-tps62.html
    www2.census.gov/geo/docs/reference/state.txt
    '''
    TerritoryDataRecord = namedtuple(
        'TerritoryDataRecord',
        'fips, ansi, total_pop, urban_pop, latitude, longitude, '
        'land_area, water_area')
    #                                                                  (km^2)
    #     fips  ansi        tpop    upop    latitude     longitude   land water
    as_ = '60', '01802701', 55519,  48645, -14.2638166, -170.6620902, 198, 1307
    gu_ = '66', '01802705', 159358, 149918, 13.4383000,  144.7729285, 543, 935
    mp_ = '69', '01779809', 53883,  48997,  14.9367835,  145.6010210, 472, 4644
    um_ = '74', '01878752', 300,    0,      0,           0,           41,   0
    vi_ = '78', '01802710', 106405, 100607, 18.3267485, -064.9712501, 348, 1550
    territory_data = {'AS': as_, 'GU': gu_, 'MP': mp_, 'UM': um_, 'VI': vi_}
    territory_keys = State.SMALL_TERRITORIES

    if sub1keys:
        territory_keys &= set(sub1keys)
        if not territory_keys:
            return

    records = (geo_session.query(State)
                          .filter(State.stusps.in_(territory_keys)).all())

    us = Geo['us']
    print('Loading remaining territories...')

    for r in records:
        print('{state} - {name}'.format(state=r.stusps,
                                        name=r.name))
        geo = Geo(name=r.name, abbrev=r.stusps, path_parent=us, parents=[us])

        data_dict = TerritoryDataRecord(*territory_data[r.stusps])._asdict()
        fips = data_dict.pop('fips')
        ansi = data_dict.pop('ansi')

        GeoData(geo=geo, **data_dict)

        glvl = GeoLevel(geo=geo, level=SUBDIVISION1,
                        designation=State.TERRITORY)

        GeoID(level=glvl, standard=FIPS, code=fips)
        GeoID(level=glvl, standard=ANSI, code=ansi)


def update_us_data():
    '''Update US population and area values based on subdivision1 values'''
    us = Geo['us']
    children = us.children.all()
    us.data.total_pop = sum((c.data.total_pop for c in children if c.data))
    us.data.urban_pop = sum((c.data.urban_pop for c in children if c.data))
    us.data.land_area = sum((c.data.land_area for c in children if c.data))
    us.data.water_area = sum((c.data.water_area for c in children if c.data))


def load_subdivision2_geos(geo_session, session, sub1keys=None):
    '''Load SUBDIVISION2 geos'''
    load_state_counties(geo_session, session, sub1keys)
    load_territory_counties(geo_session, session, sub1keys)


def load_state_counties(geo_session, session, sub1keys=None):
    '''Load county geos in states, DC, and Puerto Rico'''
    CountyRecord, columns = define_record(
        'CountyRecord',
        'GHRP.name, GHRP.lsadc, GHRP.statefp, '
        'GHRP.countyid, GHRP.countyns, GHRP.p0020001, GHRP.p0020002, '
        'GHRP.intptlat, GHRP.intptlon, GHRP.arealand, GHRP.areawatr')

    # U.S. counties including independent cities
    base_query = (
        geo_session.query(GHRP)
                   .filter(GHRP.sumlev == '050', GHRP.geocomp == '00'))

    if sub1keys:
        if not (set(sub1keys) - State.SMALL_TERRITORIES):
            return
        statefps = {State.get_by('stusps', k).statefp for k in sub1keys}
        base_query = base_query.filter(GHRP.statefp.in_(statefps))

    records = base_query.order_by(GHRP.statefp, GHRP.countyid).values(*columns)

    us = Geo['us']
    state = None
    stusps = prior_stusps = None
    qualifier = None
    geos_with_unusual_affixes = []

    print('Loading counties and equivalents...')
    for r in (CountyRecord(*record) for record in records):

        stusps = State.get_by('statefp', r.ghrp_statefp).stusps
        if stusps != prior_stusps:
            state = us[stusps]
            print('{state} - {name}'.format(
                state=state.abbrev, name=state.name))
            prior_stusps = stusps

        print(u"\t{name}, {state} ({standard}, '{code}')"
              .format(name=r.ghrp_name, state=state.abbrev, standard=ANSI,
                      code=r.ghrp_countyns))

        name, lsad, affix, _, _ = LSAD.deaffix(r.ghrp_name, r.ghrp_lsadc)

        if COUNTY_LSAD_AS_QUALIFIER:
            qualifier = lsad if affix == LSAD.SUFFIX else None
            name = name if qualifier else r.ghrp_name
        else:
            qualifier = None
            name = r.ghrp_name

        designation = lsad if lsad else County.COUNTY

        data_record = GeoData.extract_data(r, PREFIXED_GHRP_DATA_FIELDS)

        data_match_dict = data_record._asdict()
        del data_match_dict['latitude']
        del data_match_dict['longitude']

        # County matches state so add county geolevel; DC only
        if state.data.matches(inexact=1, **data_match_dict):

            county_glvl = GeoLevel(geo=state, level=SUBDIVISION2,
                                   designation=designation)

            GeoID(level=county_glvl, standard=FIPS, code=r.ghrp_countyid)

            ansi = r.ghrp_countyns
            if (ansi is not None and
                    GeoID.tget((ANSI, ansi), query_on_miss=False) is None):
                GeoID(level=county_glvl, standard=ANSI, code=ansi)

            continue

        county = Geo(name=name, qualifier=qualifier,
                     path_parent=state, parents=[state, us])

        GeoData(geo=county, **data_record._asdict())

        glvl = GeoLevel(geo=county, level=SUBDIVISION2,
                        designation=designation)

        GeoID(level=glvl, standard=FIPS, code=r.ghrp_countyid)

        ansi = r.ghrp_countyns
        if (ansi is not None and
                GeoID.tget((ANSI, ansi), query_on_miss=False) is None):
            GeoID(level=glvl, standard=ANSI, code=r.ghrp_countyns)

        if affix != LSAD.SUFFIX:
            geos_with_unusual_affixes.append((county, name, lsad, affix))

    print('Geos with unusual affixes:')
    for geo_lsad_tuple in geos_with_unusual_affixes:
        print(geo_lsad_tuple)


def load_territory_counties(geo_session, session, sub1keys=None):
    '''Load counties in U.S. territories, except for Puerto Rico'''
    TerritoryCountyDataRecord = namedtuple(
        'TerritoryCountyDataRecord',
        'fips, ansi, stusps, lsad_code, full_name')

    # TODO: Find and add data (they do not show up as children without data)
    territory_county_data = (
        # fips       ansi    stusps lsad_code  full_name
        ('60010', '01805240', 'AS', '07', 'Eastern District'),
        ('60020', '01805242', 'AS', '07', "Manu'a District"),
        ('60030', '01805243', 'AS', '10', 'Rose Island'),
        ('60040', '01805244', 'AS', '10', 'Swains Island'),
        ('60050', '01805241', 'AS', '07', 'Western District'),
        ('66010', '01802705', 'GU', '00', 'Guam'),  # dup ansi; TODO: Add '14'
        ('69085', '01805245', 'MP', '12', 'Northern Islands Municipality'),
        ('69100', '01805246', 'MP', '12', 'Rota Municipality'),
        ('69110', '01805247', 'MP', '12', 'Saipan Municipality'),
        ('69120', '01805248', 'MP', '12', 'Tinian Municipality'),
        ('74300', None,       'UM', '00', 'Midway Islands'),
        ('78010', '02378248', 'VI', '10', 'St. Croix Island'),
        ('78020', '02378249', 'VI', '10', 'St. John Island'),
        ('78030', '02378250', 'VI', '10', 'St. Thomas Island'),
        # Sources:
        # www.census.gov/newsroom/releases/archives/2010_census/cb13-tps62.html
    )
    records = (TerritoryCountyDataRecord(*d) for d in territory_county_data)

    territory_keys = State.SMALL_TERRITORIES

    if sub1keys:
        territory_keys &= set(sub1keys)
        if not territory_keys:
            return

    records = (r for r in records if r.stusps in territory_keys)

    us = Geo['us']
    territory = None
    stusps = prior_stusps = None
    geos_with_unusual_affixes = []

    for fips, ansi, stusps, lsad_code, full_name in records:

        if stusps != prior_stusps:
            territory = us[stusps]
            print('{state} - {name}'.format(
                state=territory.abbrev, name=territory.name))
            prior_stusps = stusps

        print(u"\t{name}, {state} ({standard}, '{code}')"
              .format(name=full_name, state=stusps, standard=ANSI, code=ansi))

        name, lsad, affix, _, _ = LSAD.deaffix(full_name, lsad_code)

        if COUNTY_LSAD_AS_QUALIFIER:
            qualifier = lsad if affix == LSAD.SUFFIX else None
            name = name if qualifier else full_name
        else:
            qualifier = None
            name = full_name

        designation = lsad if lsad else County.COUNTY

        # Look for existing geo with same county ANSI code; Guam only
        try:
            ansi_geoid = GeoID.tget((ANSI, ansi), query_on_miss=False)
            # Raise AttributeError if ansi_geoid is None
            existing = ansi_geoid.level.geo
            assert not existing.levels.get(SUBDIVISION2)

        except AttributeError:
            pass

        else:
            print(u"\t{name}, {state} ({standard}, '{code}')"
                  " with same place ANSI exists".format(
                    name=full_name, state=stusps, standard=ANSI, code=ansi))

            county_glvl = GeoLevel(geo=territory, level=SUBDIVISION2,
                                   designation=designation)
            GeoID(level=county_glvl, standard=FIPS, code=fips)
            continue

        county = Geo(name=name, qualifier=qualifier,
                     path_parent=territory, parents=[territory, us])

        glvl = GeoLevel(geo=county, level=SUBDIVISION2,
                        designation=designation)

        GeoID(level=glvl, standard=FIPS, code=fips)

        # Per try above, GeoID.tget((ANSI, ansi)) is None...
        if ansi is not None:
            GeoID(level=glvl, standard=ANSI, code=ansi)

        if affix != LSAD.SUFFIX:
            geos_with_unusual_affixes.append((county, name, lsad, affix))

    print('Geos with unusual affixes:')
    for geo_lsad_tuple in geos_with_unusual_affixes:
        print(geo_lsad_tuple)

    # TODO: Consolidate Guam county into Guam the territory


def load_subdivision3_geos(geo_session, session, sub1keys=None, sub2keys=None):
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
    sub2keys=None: sequence of county fips ids to scope the data load
    '''
    CousubRecord, columns = define_record(
        'CousubRecord', 'GHRP.name, GHRP.lsadc, GHRP.statefp, '
        'GHRP.countyid, GHRP.countyns, '
        'GHRP.cousubid, GHRP.cousubns, '
        'GHRP.p0020001, GHRP.p0020002, '
        'GHRP.intptlat, GHRP.intptlon, '
        # 'Cousub.intptlat, Cousub.intptlong, '
        'GHRP.arealand, GHRP.areawatr')

    # State-County-Cousub (including independent cities)
    base_query = (
        geo_session.query(GHRP)  # .outerjoin(GHRP.cousub)
                   .filter(GHRP.sumlev == '060', GHRP.geocomp == '00'))

    if sub1keys:
        statefps = {State.get_by('stusps', k).statefp for k in sub1keys}
        base_query = base_query.filter(GHRP.statefp.in_(statefps))

    if sub2keys:
        countyfps = {add_leading_zeros(cfp, 3) for cfp in sub2keys}
        base_query = base_query.filter(GHRP.countyfp.in_(countyfps))

    records = (
        base_query.order_by(GHRP.statefp, GHRP.cousubns)
                  .values(*columns))

    records = PeekableIterator(records)

    us = Geo['us']
    state = None
    stusps = prior_stusps = None  # State FIPS codes
    countyid = prior_countyid = None  # County FIPS codes
    cousubns = prior_cousubns = None  # Cousub ANSI codes

    record_number = 0
    counties = set()
    fips_county_map = {}
    total_pop = urban_pop = 0
    total_area = land_area = water_area = 0
    coordinate_tuple = latitude = longitude = None

    tracker = defaultdict(list)

    print('Loading county subdivisions and equivalents...')
    for r in (CousubRecord(*record) for record in records):

        cousubns = r.ghrp_cousubns
        cousubid = r.ghrp_cousubid
        geoids = {ANSI: cousubns, FIPS: cousubid}

        # Invalid cousub (e.g. 'County subdivisions not defined')
        if cousubns == '00000000':
            print(u"\t\tSkipping invalid cousub: {name} ({standard}, '{code}')"
                  .format(name=r.ghrp_name, standard=ANSI, code=cousubns))
            continue

        name, lsad, _, _, _ = LSAD.deaffix(r.ghrp_name, r.ghrp_lsadc)
        designation = lsad if lsad else Cousub.COUNTY_SUBDIVISION

        stusps = State.get_by('statefp', r.ghrp_statefp).stusps
        if stusps != prior_stusps:
            state = us[stusps]
            print(u'{state} - {name}'.format(
                state=state.abbrev, name=state.name))
            prior_stusps = stusps

        countyid = r.ghrp_countyid
        if countyid != prior_countyid:
            county = GeoID[FIPS, r.ghrp_countyid].level.geo
            print(u"\t{name}, {state} ({standard}, '{code}')"
                  .format(name=county.name, state=state.abbrev, standard=ANSI,
                          code=r.ghrp_countyns))
            prior_countyid = countyid

        # If it's a new cousub place, reset variables
        if cousubns != prior_cousubns:
            record_number = 0
            counties.clear()
            fips_county_map.clear()
            total_pop = urban_pop = 0
            total_area = land_area = water_area = 0
            coordinate_tuple = latitude = longitude = None
            prior_cousubns = cousubns

        record_number += 1
        counties.add(county)
        fips_county_map[cousubid] = county

        new_geo_location = GeoLocation(r.ghrp_intptlat, r.ghrp_intptlon)
        new_land_area = Area(r.ghrp_arealand, requantize=True)
        new_water_area = Area(r.ghrp_areawatr, requantize=True)
        new_total_area = new_land_area + new_water_area

        if coordinate_tuple is None:
            coordinate_tuple = new_geo_location.values
        else:
            coordinate_tuple = GeoLocation.combine_coordinates(
                (coordinate_tuple, total_area),
                (new_geo_location.values, new_total_area))

        total_pop += r.ghrp_p0020001
        urban_pop += r.ghrp_p0020002
        land_area += new_land_area
        water_area += new_water_area
        total_area = land_area + water_area

        if (records.has_next() and
                CousubRecord(*records.peek()).ghrp_cousubns == cousubns):
            continue

        # We're on the last record for the current cousub place
        print("\t{name}, {state} ({standard}, '{code}')"
              .format(name=name, state=stusps, standard=ANSI, code=cousubns))

        latitude, longitude = GeoLocation(*coordinate_tuple)

        data_record = GeoData.Record(
            total_pop, urban_pop, latitude, longitude, land_area, water_area)

        parents = list(counties | {state, us})

        # if cousubns == '00666022':  # Winnebago, MN
        # if cousubns == '02397885':  # Union City, OH
        # if cousubns in {'00978733', '00978734'}:  # Binghamton, NY
        # if cousubns == '01939972':  # Yakutat, AK
        # if cousubns == '01929081':  # Mullen, NE
        # if cousubns == '00468764':  # Sumner, IA in Bremer/Fayette Counties
        # if cousubns == '02390665':  # Washington DC
        # if cousubns == '00428803':  # Chicago, IL

        is_friendly_name = not invalid_cousub_name(name)
        if record_number > 1 and not is_friendly_name:
            tracker['unfriendly_multiples'].append(
                (cousubns, name, record_number))

        if ((stusps in State.STATES_WITH_MCDS_AS_GOVERNMENTAL_UNITS or
                record_number > 1) and is_friendly_name):

            # If multiple cousubs with same ANSI, main geo has no FIPS
            if record_number > 1:
                geoids.pop(FIPS)

            place, place_created = manifest_geo(
                name=name, lsad=lsad, path_parent=state, state=state,
                county=county, counties=counties, data_record=data_record,
                parents=parents, level=SUBDIVISION3, designation=designation,
                geoids=geoids, tracker=tracker)

            place_level = (SUBPLACE if cousubns in Cousub.NYC_ANSI_CODES
                           else PLACE)

            # GeoIDs for the PLACE level must be added by load_place_geos
            geo_level, level_created = GeoLevel.update_or_create(
                geo=place, level=place_level, designation=designation,
                _query_on_miss=False, _nested_transaction=False)

            if place is county:
                continue

            for cousub_fips, path_county in fips_county_map.items():
                place_alias, alias_created = manifest_alias(
                    alias_targets=[place], name=name, lsad=lsad,
                    path_parent=path_county, state=state, county=path_county,
                    tracker=tracker)

                if record_number > 1:
                    geo_level, level_created = GeoLevel.redesignate_or_create(
                        geo=place_alias, level=SUBDIVISION3,
                        designation=designation, ids={FIPS: cousub_fips},
                        _query_on_miss=False, _nested_transaction=False)

        else:
            cousub, cousub_created = manifest_geo(
                name=name, lsad=lsad, path_parent=county, state=state,
                county=county, data_record=data_record, parents=parents,
                level=SUBDIVISION3, designation=designation, geoids=geoids,
                tracker=tracker)

    for key, value in tracker.items():
        print(' '.join(word.capitalize() for word in key.split('_')) + ':')
        print(value)
        print()

    return tracker


def load_place_geos(geo_session, session, sub1keys=None, placeids=None):

    PlaceRecord, columns = define_record(
        'PlaceRecord',
        'GHRP.name, GHRP.lsadc, '
        'GHRP.statefp, GHRP.countycc, '
        'GHRP.countyid, GHRP.countyns, '
        'GHRP.cousubid, GHRP.cousubns, '
        'GHRP.placeid, GHRP.placens, '
        'GHRP.p0020001, GHRP.p0020002, '
        'Place.intptlat, Place.intptlong, '
        'GHRP.arealand, GHRP.areawatr')

    # U.S. places by county equivalent
    base_query = (
        geo_session.query(GHRP)
                   .outerjoin(GHRP.place)
                   .filter(GHRP.sumlev == '070', GHRP.geocomp == '00'))

    if sub1keys:
        statefps = {State.get_by('stusps', k).statefp for k in sub1keys}
        base_query = base_query.filter(GHRP.statefp.in_(statefps))

    if placeids:
        placeids = set(placeids) if not isinstance(placeids, set) else placeids
        base_query = base_query.filter(GHRP.placeid.in_(placeids))

    records = (
        base_query.order_by(GHRP.statefp, GHRP.placeid,
                            GHRP.countyid, GHRP.cousubid)
                  .values(*columns))

    records = PeekableIterator(records)

    us = Geo['us']
    state = None
    stusps = prior_stusps = None  # State FIPS codes
    countyid = prior_countyid = None  # County FIPS codes
    cousubid = prior_cousubid = None  # Cousub FIPS codes
    placeid = prior_placeid = None  # Place FIPS codes

    counties = set()
    cousubs = set()
    total_pop = urban_pop = 0
    land_area = water_area = 0

    tracker = defaultdict(list)

    print('Loading places...')
    for r in (PlaceRecord(*record) for record in records):

        placens = r.ghrp_placens
        placeid = r.ghrp_placeid
        geoids = {ANSI: placens, FIPS: placeid}

        name, lsad, affix, extra_prefixes, extra_suffixes = deaffix_place(
            r.ghrp_name, r.ghrp_lsadc, placens)
        designation = lsad if lsad else Place.PLACE

        stusps = State.get_by('statefp', r.ghrp_statefp).stusps
        if stusps != prior_stusps:
            state = us[stusps]
            print(u'{state} - {name}'.format(state=stusps, name=state.name))
            prior_stusps = stusps

        countyid = r.ghrp_countyid
        if countyid != prior_countyid:
            county = GeoID[ANSI, r.ghrp_countyns].level.geo
            assert county
            prior_countyid = countyid

        cousubid = r.ghrp_cousubid
        cousubns = r.ghrp_cousubns

        if cousubid != prior_cousubid:
            # Exclusively water areas of states fall into this category
            if cousubns == '00000000':
                print(u'\t\tSkipping place with undefined cousub: '
                      "{name} ({standard}, '{code}')"
                      .format(name=r.ghrp_name, standard=ANSI, code=cousubns))
                continue

            if (not GeoID.tget((ANSI, cousubns), query_on_miss=False) and
                    placens != cousubns):
                tracker['places_missing_for_missing_cousub_ansi_ids'].append(
                    (cousubns, placens, cousubid, placeid))

            # Use ANSI code to ensure we don't get an alias
            cousub = GeoID[ANSI, cousubns].level.geo
            assert cousub.data
            prior_cousubid = cousubid

        # Place remainder or missing place (already created from cousub)
        if placens == '99999999':
            is_remainder = LSAD.PREFIX_REMAINDER_OF in extra_prefixes
            if not is_remainder:
                tracker['missing_places'].append(cousub)

            place_created_from_cousub = cousub.levels.get(PLACE) is not None
            if (stusps in State.STATES_WITH_MCDS_AS_GOVERNMENTAL_UNITS and
                    not place_created_from_cousub):
                tracker['cousub_missing_places'].append(cousub)

            print(u'\t{name}, {state} ({standard}, {placens}) is '
                  "{skipped_place} cousub {cousub} ({standard}, '{cousubns}')"
                  .format(name=r.ghrp_name, state=state.abbrev, standard=ANSI,
                          placens=placens, cousub=cousub.name,
                          cousubns=r.ghrp_cousubns,
                          skipped_place=(
                            'a remainder of' if is_remainder else
                            'missing, but was already created from'
                            if place_created_from_cousub else
                            'missing. Place NOT created from')))
            continue

        # If it's a new place, reset variables
        if placeid != prior_placeid:
            counties.clear()
            cousubs.clear()
            total_pop = urban_pop = 0
            land_area = water_area = 0
            prior_placeid = placeid

        counties.add(county)
        cousubs.add(cousub)
        total_pop += r.ghrp_p0020001
        urban_pop += r.ghrp_p0020002
        land_area += Area(r.ghrp_arealand, requantize=True)
        water_area += Area(r.ghrp_areawatr, requantize=True)

        if (records.has_next() and
                PlaceRecord(*records.peek()).ghrp_placeid == placeid):
            continue

        # We're on the last record for the current place
        print("\t{name}, {state} ({standard}, '{code}')"
              .format(name=name, state=stusps, standard=ANSI, code=placens))

        geo_location = GeoLocation(r.place_intptlat, r.place_intptlong)
        latitude, longitude = geo_location.coordinates

        data_record = GeoData.Record(
            total_pop, urban_pop, latitude, longitude, land_area, water_area)

        data_match_dict = data_record._asdict()
        del data_match_dict['latitude']
        del data_match_dict['longitude']

        if len(cousubs) == 1 and cousub.data.matches(inexact=1,
                                                     **data_match_dict):
            level = PLACE
        else:
            # If any cousub is a PLACE, set level to SUBPLACE
            level = SUBPLACE if max(bool(cousub.levels.get(PLACE))
                                    for cousub in cousubs) else PLACE

        parents = list(cousubs | counties | {state, us})
        children = ([cs for cs in cousubs if cs.levels.get(SUBPLACE)]
                    if level == PLACE else [])

        # if placens == '02395220':  # New York
        # if placens == '02394197':  # Bloomington, IL (alias conflict)
        # if placens == '00485605':  # Lake Quivira, KS (ANSI data discrepancy)
        # if placens == '02378022':  # Framingham, MA (town, not CDP)

        place, created = manifest_geo(
            name=name, lsad=lsad, path_parent=state, state=state,
            county=county, cousub=cousub, counties=counties, cousubs=cousubs,
            data_record=data_record, parents=parents, children=children,
            level=level, designation=designation, geoids=geoids,
            tracker=tracker)

        # If consolidated county or independent city, add to list
        if r.ghrp_countycc in {'H6', 'C7'}:
            tracker['consolidated'].append((county, cousub, place, created))

    for key, value in tracker.items():
        print(' '.join(word.capitalize() for word in key.split('_')) + ':')
        print(value)
        print()

    return tracker


def manifest_alias(alias_targets, name, lsad, path_parent, state, county,
                   cousub=None, tracker=None):

    return manifest_geo(name=name, lsad=lsad, path_parent=path_parent,
                        state=state, county=county, cousub=cousub,
                        alias_targets=alias_targets, tracker=tracker)


def manifest_geo(name, lsad, path_parent, state, county,
                 cousub=None, counties=None, cousubs=None, alias_targets=None,
                 data_record=None, parents=None, children=None,
                 level=None, designation=None, geoids=None, tracker=None):

    if level in {COUNTRY, SUBDIVISION1, SUBDIVISION2}:
        raise ValueError('Unsupported level: {}'.format(level))

    if alias_targets and (data_record or parents or children or
                          designation or geoids):
        raise ValueError('Arguments inconsistent with alias')

    indent = '\t\t'
    counties = counties if counties is not None else {county}
    cousubs = cousubs if cousubs is not None else {cousub} if cousub else set()
    alias_targets = alias_targets if alias_targets is not None else []
    parents = parents if parents is not None else []
    children = children if children is not None else []
    geoids = geoids if geoids is not None else {}
    ansi = geoids.get(ANSI)

    if alias_targets:
        data_match_dict = None
    else:
        data_match_dict = data_record._asdict()
        del data_match_dict['latitude']
        del data_match_dict['longitude']

    geo_created = False

    for single_loop_to_enable_exception_flow_control in range(1):

        ############################################################
        #
        # Check if existing GeoID
        #
        try:
            ansi_geoid = GeoID.tget((ANSI, ansi), query_on_miss=False)
            if not ansi_geoid:
                # Raise on alias since ansi is None
                raise KeyMissingFromRegistry

        except KeyMissingFromRegistry:
            pass  # Execution proceeds after else clause

        else:
            ansi_glvl = ansi_geoid.level
            geo = ansi_glvl.geo

            ############################################################
            #
            # Happy path 1: Geo with matching ANSI code
            #
            if geo.data.matches(inexact=1, **data_match_dict):
                print(u'{}Geo with matching ANSI code and data'.format(indent))
                # If cousub spans counties, replace calculated coordinates
                if ansi_glvl.level == SUBDIVISION3 and len(counties) > 1:
                    geo.data.latitude = data_record.latitude
                    geo.data.longitude = data_record.longitude
            else:
                print(u'{}Updating data mismatch on ANSI match'.format(indent))
                if tracker is not None:
                    old_data_dict = geo.data.jsonify(
                        nest=True, hide={'id', 'geo', 'total_area'})
                    new_data_dict = data_record._asdict()
                    tracker['ansi_data_discrepancies'].append(
                        (ansi, geo, old_data_dict, new_data_dict))
                geo.data.update(**new_data_dict)

            geo_level, level_created = GeoLevel.redesignate_or_create(
                geo=geo, level=level, designation=designation, ids=geoids,
                _query_on_miss=False, _nested_transaction=False)

            if geo.is_known_by(name):
                continue  # Execution proceeds after single loop

            # Create alias & resolve any conflicts (e.g Bloomington, IL)
            manifest_alias(alias_targets=[geo], name=name, lsad=lsad,
                           path_parent=path_parent, state=state,
                           county=county, cousub=cousub, tracker=tracker)
            continue  # Execution proceeds after single loop

        ################################################################
        #
        # Happy path 2: Geo matches county so add geolevel
        #
        try:
            # Raise TypeError on alias as data_match_dict is None
            if (len(counties) != 1 or not
                    county.data.matches(inexact=1, **data_match_dict)):
                raise ValueError

        except (TypeError, ValueError):
            pass  # Execution proceeds after else clause

        else:
            print(u'{}Found geo with data matching county'.format(indent))

            geo = county  # e.g. San Francisco, DC, and Carson City

            geo_level, level_created = add_level_and_rename(
                geo=county, level=level, designation=designation,
                geoids=geoids, name=name, lsad=lsad,
                path_parent=county.path_parent, match_level=SUBDIVISION2,
                state=state, county=county, cousub=cousub, tracker=tracker)

            continue  # Execution proceeds after single loop

        ############################################################
        #
        # Happy path 3: Geo matches cousub so add geolevel
        #
        try:
            # Raise TypeError on alias as data_match_dict is None
            if (level == SUBDIVISION3 or len(cousubs) != 1 or
                    not cousub.data.matches(inexact=1, **data_match_dict)):
                raise ValueError

        except (TypeError, ValueError):
            pass  # Execution proceeds after else clause

        else:
            print(u'{}Found geo with data matching cousub'.format(indent))

            # Create place from matching cousub if one doesn't exist yet
            if cousub.path_parent is county:
                cousub_alias = cousub  # Becomes alias via create place
                cousub, _ = create_place_from_cousub(cousub)
                if tracker is not None:
                    tracker['cousubs_promoted_to_places'].append(
                        (cousub_alias, cousub))

            geo = cousub

            # If cousub spans counties, replace calculated coordinates
            if len(counties) > 1:
                geo.data.location = data_record.latitude, data_record.longitude

            # Do not replace non-CDP designation with CDP, e.g. Framingham, MA
            if (designation == Place.CDP and geo.levels.get(level) and
                    geo.levels[level].designation != Place.CDP):
                designation = geo.levels[level].designation

            geo_level, level_created = add_level_and_rename(
                geo=geo, level=level, designation=designation,
                geoids=geoids, name=name, lsad=lsad,
                path_parent=geo.path_parent, match_level=SUBDIVISION3,
                state=state, county=county, cousub=cousub, tracker=tracker)

            continue  # Execution proceeds after single loop

        ############################################################
        #
        # Happy path 4: Create geo, if no conflict
        #
        try:
            geo = Geo(name=name, path_parent=path_parent,
                      alias_targets=alias_targets, parents=parents,
                      children=children)
            geo_created = True

        except KeyRegisteredAndNoModify:
            pass  # Execution proceeds after else clause

        else:
            if alias_targets:
                continue  # Execution proceeds after single loop
            GeoData(geo=geo, **data_record._asdict())

            geo_level, level_created = GeoLevel.redesignate_or_create(
                geo=geo, level=level, designation=designation, ids=geoids,
                _query_on_miss=False, _nested_transaction=False)

            continue  # Execution proceeds after single loop

        ############################################################
        #
        # Conflict with geo or geo alias
        #
        geo_conflict_key = Geo.create_key(name=name, path_parent=path_parent)
        geo_conflict = Geo[geo_conflict_key]
        geo_conflict_alias_targets = geo_conflict.alias_targets

        # if we have targets and geo conflict is an alias, reuse it
        if alias_targets and geo_conflict_alias_targets:
            geo_conflict.add_alias_targets(*alias_targets)
            geo = geo_conflict
            continue  # Execution proceeds after single loop

        # Create geo with temporary path until conflict resolved
        geo = Geo(name=name, path_parent=None, alias_targets=alias_targets,
                  parents=parents, children=children)
        geo_created = True
        target_geos = alias_targets if alias_targets else (geo,)

        if not alias_targets:
            GeoData(geo=geo, **data_record._asdict())

            geo_level, level_created = GeoLevel.redesignate_or_create(
                geo=geo, level=level, designation=designation, ids=geoids,
                _query_on_miss=False, _nested_transaction=False)

        if geo_conflict_alias_targets:
            # geo is not an alias else we would have recycled per above
            geo_conflict.add_alias_target(geo)

        else:
            resolve_geo_conflict(geo_conflict, geo, lsad, state)

        ############################################################
        #
        # If geo is alias, put it in conflict namespace
        #
        if geo.alias_targets:
            geo.path_parent = path_parent
            continue  # Execution proceeds after single loop

        ############################################################
        #
        # Name conflict so qualify by LSAD
        #
        try:
            geo.qualifier, geo.path_parent = lsad, path_parent
            print(u'{indent}Geos with same name in {state}: {geos}'
                  .format(indent=indent, state=state.abbrev,
                          geos=(geo_conflict.human_id, geo.human_id)))
            continue  # Execution proceeds after single loop

        except KeyError:
            pass

        ############################################################
        #
        # Conflict w/ LSAD-qualified geo so also qualify by county
        #
        lsad_geo_conflict_key = Geo.create_key(name=name, qualifier=lsad,
                                               path_parent=path_parent)
        lsad_geo_conflict = Geo[lsad_geo_conflict_key]
        lsad_geo_conflict_alias_targets = lsad_geo_conflict.alias_targets

        if lsad_geo_conflict_alias_targets:
            lsad_geo_alias = lsad_geo_conflict

        else:
            lsad_geo_conflict.qualifier = ' in '.join((
                get_primary_designation(lsad_geo_conflict, state),
                lsad_geo_conflict.get_related_geos(
                    relation=PARENTS, level=SUBDIVISION2)[0].name))
            # Add alias in conflict namespace to point to conflicts
            lsad_geo_alias = Geo(name=name, qualifier=lsad,
                                 path_parent=path_parent,
                                 alias_targets=[lsad_geo_conflict])

        lsad_geo_alias.add_alias_targets(*target_geos)

        geo.qualifier, geo.path_parent = (
            ' in '.join((lsad, county.name)), path_parent)

        print(u'{indent}Geos with same name/lsad in {state}: {geos}'
              .format(indent=indent, state=state.abbrev,
                      geos=(lsad_geo_conflict.human_id, geo.human_id)))

    # After single loop: execution proceeds here
    return geo, geo_created


def add_level_and_rename(geo, level, designation, geoids, name, lsad,
                         path_parent, match_level, state, county, cousub,
                         tracker=None):
    # e.g. San Francisco, DC, and Carson City

    geo_level, created = GeoLevel.redesignate_or_create(
        geo=geo, level=level, designation=designation, ids=geoids,
        _query_on_miss=False, _nested_transaction=False)

    if tracker is not None:
        tracker['_'.join((match_level, 'matches'))].append(geo)

    # Keep name only up to comma, e.g. 'Lynchburg, Moore County' in TN
    raw_name = name
    if ', ' in name:
        name = name.split(', ')[0]
        if tracker is not None:
            tracker['names_with_commas'].append((raw_name, name))

    if geo.is_known_by(name):
        return geo_level, created

    geo_conflict_key = Geo.create_key(name=name, path_parent=path_parent)
    geo_conflict = Geo.tget(geo_conflict_key)
    if geo_conflict is geo:
        # Never seen this happen, but just in case
        return geo_level, created

    # Create alias (rather than rename) if any apply:
    # - adding cousub with unfriendly name, e.g. "1, Charlotte", NC
    # - existing geo is cousub with friendly name
    # - geo conflict exists
    # - state is DC
    if ((level == SUBDIVISION3 and invalid_cousub_name(name)) or
        (match_level == SUBDIVISION3 and not invalid_cousub_name(geo.name)) or
            geo_conflict or state is Geo['us/dc']):  # Just alias DC
        # Geo(name=name, path_parent=path_parent, alias_targets=[geo])
        # Bloomington, IL alias conflict
        alias, alias_created = manifest_alias(
            alias_targets=[geo], name=name, lsad=lsad, path_parent=path_parent,
            state=state, county=county, cousub=cousub, tracker=tracker)
        if tracker is not None:
            tracker['_'.join((match_level, 'match_aliases'))].append(
                (alias, geo, alias_created))
        return geo_level, created

    # Try to rename geo and add alias in vacated namespace if not cousub
    try:
        geo_name = geo.name
        geo_qualifier = geo.qualifier
        # Key conflict raises KeyError
        geo.name, geo.qualifier = name, None
        # Create alias for old name, but not for invalid cousub name
        if match_level == SUBDIVISION3:
            old_geo_alias = None
        else:
            old_geo_alias = Geo(name=geo_name, qualifier=geo_qualifier,
                                path_parent=path_parent, alias_targets=[geo])
            # Create alias for each child using old path
            for child_geo in geo.children.all():
                Geo(name=child_geo.name, qualifier=child_geo.qualifier,
                    abbrev=child_geo.abbrev, path_parent=old_geo_alias,
                    alias_targets=[child_geo])

        if tracker is not None:
            tracker['_'.join((match_level, 'renames'))].append(
                (geo, old_geo_alias, raw_name))

    except KeyError:
        if tracker is not None:
            tracker['_'.join((match_level, 'failed_renames'))].append(
                (geo, geo_conflict, raw_name))

    return geo_level, created


def resolve_geo_conflict(geo_conflict, geo, lsad, state):
    '''
    Resolve geo conflict

    The geo conflict is not an alias, so resolve it by giving it an
    LSAD qualifier. If the qualified conflict also has a conflict,
    qualify it further with county. Create alias(es) for all namespace
    conflicts. If the geo conflict was already LSAD-qualified, create
    an LSAD-qualified geo alias, forcing the geo to be further qualified
    by county.

    I/O:
    geo_conflict: existing geo that conflicts with new geo
    geo: new geo with temporary path until conflict resolved
    lsad: LSAD for the new geo
    state: state geo in which geo resides
    '''
    target_geos = geo.alias_targets if geo.alias_targets else (geo,)
    geo_conflict_qualifier = get_primary_designation(geo_conflict, state)

    try:
        # If conflict already qualified by LSAD, qualify by county too
        if geo_conflict.qualifier == geo_conflict_qualifier:
            raise ValueError
        # Raise KeyError if qualified conflict itself conflicts
        geo_conflict.qualifier = geo_conflict_qualifier

    except (ValueError, KeyError):
        ################################################################
        #
        # LSAD-qualified geo conflict (QPC) itself conflicts with an
        # existing geo or alias. Resolve by qualifying by county too.
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
        qualified_geo_conflict_key = Geo.create_key(
            name=geo_conflict.name, qualifier=geo_conflict_qualifier,
            path_parent=state)
        qgc = Geo[qualified_geo_conflict_key]
        qgc_alias_targets = qgc.alias_targets

        if qgc_alias_targets:
            qualified_geo_alias = qgc

            # If a dedicated alias, promote it to clear the conflict
            if (geo_conflict in qgc_alias_targets and
                    len(qgc_alias_targets) == 1):
                qgc.promote_to_alias_target()
                assert len(geo_conflict.alias_targets) == 1
                geo_conflict.add_alias_targets(*target_geos)
                return

        else:
            qgc.qualifier = ' in '.join((
                get_primary_designation(qgc, state),
                qgc.get_related_geos(
                    relation=PARENTS, level=SUBDIVISION2)[0].name))
            # Add alias in conflict namespace to point to conflicts
            qualified_geo_alias = Geo(
                name=geo_conflict.name, qualifier=geo_conflict_qualifier,
                path_parent=state, alias_targets=[qgc])

        if qgc is geo_conflict:
            ############################################################
            #
            # Geo conflict was already LSAD-qualified and was further
            # qualified by county. So create an LSAD-qualified alias.
            #
            # Example: Union City, OH
            # There are 28 Union, OHs, of which 27 are townships and 1
            # is a city in Miami County. In addition, a Union City
            # township in Montgomery County conflicts with Union city.
            #
            # Name        LSAD      County             Human ID
            # ----------------------------------------------------------
            # Union       township  [27 Counties]      union_township_in_x
            # Union       city      Miami County       union_city
            # Union City  township  Montgomery County  union_city
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
                lsad_geo_alias = Geo(name=geo.name, qualifier=lsad,
                                     path_parent=state, alias_targets=[geo])
            except KeyRegisteredAndNoModify:
                lsad_geo_alias_key = Geo.create_key(
                    name=geo.name, qualifier=lsad, path_parent=state)
                lsad_geo_alias = Geo[lsad_geo_alias_key]
                assert lsad_geo_alias.alias_targets
                lsad_geo_alias.add_alias_targets(*target_geos)

        else:
            qualified_geo_alias.add_alias_target(geo_conflict)

            geo_conflict.qualifier = ' in '.join((
                get_primary_designation(geo_conflict, state),
                geo_conflict.get_related_geos(relation=PARENTS,
                                              level=SUBDIVISION2)[0].name))

        print(u'\t\tGeo conflict itself conflicts when '
              'qualified by lsad in {state}: {geos}'
              .format(state=state.abbrev, geos=(
               qgc.human_id, geo_conflict.human_id)))

    if geo.alias_targets:
        # Geo is an alias, so make it an alias of the geo conflict too
        geo.add_alias_target(geo_conflict)
        return

    try:
        # Add alias in conflict namespace just vacated
        Geo(name=geo.name, path_parent=state,
            alias_targets=[geo_conflict, geo])

    except KeyRegisteredAndNoModify:
        # Conflict already qualified, so alias in conflict namespace
        geo_alias_key = Geo.create_key(name=geo.name, path_parent=state)
        geo_alias = Geo[geo_alias_key]
        geo_alias.add_alias_targets(geo_conflict, *target_geos)


def create_place_from_cousub(cousub, county=None, state=None, lsad=None,
                             designation=None, ansi=None, tracker=None):
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
    designation = designation or lsad
    ansi = ansi or cousub.levels[SUBDIVISION3].ids[ANSI].code

    level = SUBPLACE if ansi in Cousub.NYC_ANSI_CODES else PLACE

    # GeoIDs for the PLACE level must be added by load_place_geos
    GeoLevel(geo=cousub, level=level, designation=designation)

    # As county, cousub path parent already state, so don't create alias
    if cousub is county:
        return county, False

    place, created = manifest_alias(
        alias_targets=[cousub], name=name, lsad=lsad, path_parent=state,
        state=state, county=county, cousub=cousub, tracker=tracker)

    place.promote_to_alias_target()

    return place, created


def get_primary_designation(geo, state):
    # prioritized_levels = GeoLevel.UP.keys()

    if state.abbrev in State.STATES_WITH_MCDS_AS_GOVERNMENTAL_UNITS:
        # Not worth removing cousub duplicate
        # prioritized_levels = chain((SUBDIVISION3,), prioritized_levels)
        prioritized_levels = (SUBDIVISION3, SUBPLACE, PLACE, SUBDIVISION2)

    else:
        prioritized_levels = (SUBPLACE, PLACE, SUBDIVISION2, SUBDIVISION3)

    for level in prioritized_levels:
        try:
            return geo.levels[level].designation
        except KeyError:
            pass


def deaffix_place(full_name, lsad_code, placens):
    if lsad_code != '00' or placens == '99999999':
        return LSAD.deaffix(full_name, lsad_code)

    B = LSAD.SUFFIX_BALANCE
    P = LSAD.SUFFIX_PART
    SUFFIX = LSAD.SUFFIX

    CB = 'city (balance)'
    CGB = 'consolidated government (balance)'
    # MGB = 'metropolitan government (balance)'
    # UGB = 'unified government (balance)'

    PLACE_PATCH_MAP = {
        #                                                extra affixes
        # placens    name               lsad     affix    pre     suf    state
        '02378282': ('Milford',          CB,    SUFFIX,  set(),  {B}),    # CT
        '02407405': ('Athens',           CGB,   SUFFIX,  set(), {B, P}),  # GA
        '02405078': ('Augusta',          CGB,   SUFFIX,  set(), {B, P}),  # GA
        '02395424': ('Indianapolis',     CGB,   SUFFIX,  set(), {B, P}),  # IN
        '01967434': ('Louisville',       CGB,   SUFFIX,  set(), {B, P}),  # KY
        '02409650': ('Anaconda',         CGB,   SUFFIX,  set(),   {P}),   # MT
        '02409652': ('Butte',            CGB,   SUFFIX,  set(), {B, P}),  # MT
        '00863219': ('Carson City',      CGB,   SUFFIX,  set(),  set()),  # NV
        '02405085': ('Hartsville',       CGB,   SUFFIX,  set(),   {P}),   # TN
        '02405092': ('Nashville',        CGB,   SUFFIX,  set(), {B, P}),  # TN
    }

    return PLACE_PATCH_MAP[placens]


def load_cbsa_geos(geo_session, session, sub1keys=None, cbsa_keys=None):

    CBSARecord, columns = define_record(
        'CBSARecord',
        'CBSA.cbsa_code, CBSA.cbsa_name, CBSA.cbsa_type, '
        'CBSA.csa_code, CBSA.csa_name, '
        'GHRP.statefp, GHRP.countyid, GHRP.placeid, '
        'GHRP.p0020001, GHRP.p0020002')

    # U.S. places by county equivalent with CBSA/CSA data
    base_query = (
        # State-County-Cousub
        geo_session.query(GHRP)
                   .join(GHRP.county)
                   .join(County.cbsa)
                   .filter(GHRP.sumlev == '155', GHRP.geocomp == '00'))

    if sub1keys:
        statefps = {State.get_by('stusps', k).statefp for k in sub1keys}
        base_query = base_query.filter(GHRP.statefp.in_(statefps))

    # Greater Austin: '12420'
    if cbsa_keys:
        cbsa_keys = cbsa_keys if isinstance(cbsa_keys, set) else set(cbsa_keys)
        base_query = base_query.filter(CBSA.cbsa_code.in_(cbsa_keys))

    records = (
        base_query.order_by(CBSA.csa_code, CBSA.cbsa_code, desc(GHRP.p0020001))
                  .values(*columns))

    records = PeekableIterator(records)

    us = Geo['us']
    cbsa_code = prior_cbsa_code = ''
    csa_code = prior_csa_code = ''

    cbsa_states = Counter()  # state pop within CBSA, indexed by state geo
    cbsa_counties = Counter()  # county pop within CBSA, indexed by county geo
    cbsa_places = Counter()  # place pop within CBSA, indexed by place geo
    csa_states = Counter()  # state pop within CSA, indexed by state geo
    csa_counties = Counter()  # county pop within CSA, indexed by county geo
    csa_places = Counter()  # place pop within CSA, indexed by place geo

    cbsa_county_children = set()
    csa_county_children = set()
    csa_cbsa_main_places = {}  # main places indexed by CBSA geo

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
            cbsa_states.clear()
            cbsa_counties.clear()
            cbsa_places.clear()
            cbsa_county_children.clear()
            cbsa_place_1 = cbsa_place_2 = None
            # cbsa_non_cdp_1 = cbsa_non_cdp_2 = None
            cbsa_main_place = None
            prior_cbsa_code = cbsa_code

            # If it's a new CSA, initialize variables
            csa_code = r.cbsa_csa_code
            if csa_code != prior_csa_code:
                csa = None
                csa_states.clear()
                csa_counties.clear()
                csa_places.clear()
                csa_county_children.clear()
                csa_cbsa_main_places.clear()
                csa_cbsa_1 = csa_cbsa_2 = None
                csa_main_cbsa = None
                prior_csa_code = csa_code

        statefp = r.ghrp_statefp
        state = GeoID[FIPS, statefp].level.geo
        if not state.levels.get(SUBDIVISION1):
            raise ValueError('State {!r} missing geo level'.format(state))
        if state.alias_targets:
            raise ValueError('State {!r} is an alias'.format(state))
        cbsa_states[state] += r.ghrp_p0020001

        countyid = r.ghrp_countyid
        county = GeoID[(FIPS, countyid)].level.geo
        if not county.levels.get(SUBDIVISION2):
            raise ValueError('County {!r} missing geo level'.format(county))
        if county.alias_targets:
            raise ValueError('County {!r} is an alias'.format(county))
        # Store pop of county (CBSAs consist of whole counties)
        if not cbsa_counties.get(county):
            cbsa_counties[county] = county.data.total_pop
            cbsa_county_children |= set(county.children.all())

        placeid = r.ghrp_placeid
        place = GeoID[(FIPS, placeid)].level.geo
        if not (place.levels.get(PLACE) or place.levels.get(SUBPLACE)):
            raise ValueError('Place {!r} missing geo level'.format(place))
        if place.alias_targets:
            raise ValueError('Place {!r} is an alias'.format(place))
        # Assemble pop of place within CBSA
        cbsa_places[place] += r.ghrp_p0020001

        # Add consolidated counties with children as places
        # (those without children are already added)
        if ((county.levels.get(PLACE) or county.levels.get(SUBPLACE)) and
                not cbsa_places.get(county)):
            cbsa_places[county] = county.data.total_pop

        # We're on the last record for the current CBSA, so create geo
        if (not records.has_next() or
                CBSARecord(*records.peek()).cbsa_cbsa_code != cbsa_code):

            cbsa_name = r.cbsa_cbsa_name
            print(u"\t\tCBSA: {name} ({cbsa_2010}, '{code}')"
                  .format(name=cbsa_name, cbsa_2010=CBSA_2010, code=cbsa_code))

            cbsa = Geo(name=cbsa_name + ' Area',
                       uses_the=True,
                       path_parent=us,
                       parents=cbsa_states.keys(),
                       children=set(cbsa_counties) | cbsa_county_children,
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
                    csa_states[state] += cbsa_states[state]

                # Counties are always wholly contained by CBSAs
                csa_counties.update(cbsa_counties)
                csa_county_children |= set(cbsa_county_children)

                # Places can be in multiple CBSAs in a CSA
                for place in cbsa_places:
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
                    print(u"\t\tCSA: {name} ({csa_2010}, '{code}')"
                          .format(name=csa_name, csa_2010=CSA_2010,
                                  code=csa_code))

                    csa = Geo(name='Greater ' + csa_name + ' Area',
                              uses_the=True,
                              path_parent=us,
                              parents=csa_states.keys(),
                              children=(set(csa_cbsa_main_places) |
                                        set(csa_counties) |
                                        csa_county_children),
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
                                alias_targets=[csa],
                                uses_the=False))

                        greater_csa_area_alias = (
                            Geo(name=('Greater ' + csa_mp_name + ' Area'),
                                abbrev=('Greater ' + csa_mp_abbrev + ' Area'
                                        if csa_mp_abbrev else None),
                                path_parent=csa_state,
                                alias_targets=[csa],
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
                                alias_targets=[cbsa_target],
                                uses_the=True))

                        if alias_state is cbsa_main_place.path_parent:
                            new_cbsa_target = cbsa_area_alias
                    else:
                        cbsa_area_alias = (
                            Geo(name=cbsa_mp_name + ' Area',
                                abbrev=(cbsa_mp_abbrev + ' Area'
                                        if cbsa_mp_abbrev else None),
                                path_parent=alias_state,
                                alias_targets=[cbsa_target],
                                uses_the=True))

                        greater_cbsa_alias = (
                            Geo(name='Greater ' + cbsa_mp_name,
                                abbrev=('Greater ' + cbsa_mp_abbrev
                                        if cbsa_mp_abbrev else None),
                                path_parent=alias_state,
                                alias_targets=[cbsa_target],
                                uses_the=False))

                        greater_cbsa_area_alias = (
                            Geo(name='Greater ' + cbsa_mp_name + ' Area',
                                abbrev=('Greater ' + cbsa_mp_abbrev + ' Area'
                                        if cbsa_mp_abbrev else None),
                                path_parent=alias_state,
                                alias_targets=[cbsa_target],
                                uses_the=True))

                        if alias_state is cbsa_main_place.path_parent:
                            new_cbsa_target = greater_cbsa_alias

                new_cbsa_target.promote_to_alias_target()

    # Add proper DC CBSA alias and promote
    dc_dc_area = Geo['us/dc/dc_area']
    dc_area = Geo(name=dc_dc_area.name,
                  abbrev=dc_dc_area.abbrev,
                  path_parent=us,
                  alias_targets=dc_dc_area.alias_targets,
                  uses_the=True)
    dc_area.promote_to_alias_target()

    # Add proper DC CSA aliases and promote
    dc_greater_dc = Geo['us/dc/greater_dc']
    greater_dc = Geo(name=dc_greater_dc.name,
                     abbrev=dc_greater_dc.abbrev,
                     path_parent=us,
                     alias_targets=dc_greater_dc.alias_targets,
                     uses_the=False)
    dc_greater_dc_area = Geo['us/dc/greater_dc_area']
    greater_dc_area = Geo(name=dc_greater_dc_area.name,
                          abbrev=dc_greater_dc_area.abbrev,
                          path_parent=us,
                          alias_targets=dc_greater_dc_area.alias_targets,
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


def load_manual_fixes(geo_session, session):
    '''Load manual fixes'''
    # TODO: Add verbose state aliases, prevent us/washington DC alias,
    # and create new us/dc/washington
    wdc = Geo.tget(u'us/washington')
    wdc.path_parent = Geo['us/dc']

    # Fix ñ in Española, NM. Note: ñ appears correctly elsewhere:
    # Peñasco, NM; Cañones, NM; La Cañada Flintridge, CA; etc.
    esp = Geo.tget(u'us/nm/espanola')
    if esp:
        esp.name = u'Espa\xf1ola'  # Geo[u'us/nm/espa\xf1ola']


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
