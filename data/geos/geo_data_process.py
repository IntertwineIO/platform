#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''Loads geo data into Intertwine'''
from collections import namedtuple

from sqlalchemy import desc
from alchy import Manager
from alchy.model import extend_declarative_base

from config import DevConfig
from data.data_process import DataSessionManager
from data.geos.models import (BaseGeoDataModel, State, CBSA, County, Place,
                              LSAD, Geoclass,  # Keep - used in globals()
                              GHRP)
from intertwine.utils import PeekableIterator, Trackable
from intertwine.geos.models import (BaseGeoModel, Geo, GeoData, GeoLevel,
                                    GeoID, geo_association_table)


def load_geos(geo_session, session):

    load_country_geos(geo_session, session)
    load_subdivision1_geos(geo_session, session)
    load_subdivision2_geos(geo_session, session)
    load_place_geos(geo_session, session)
    load_cbsa_geos(geo_session, session)

    return Trackable.catalog_updates()


def derive_columns(classes, fields):
    '''Derive columns from classes and fields

    Returns a list of sqlalchemy columns derived from a list of class
    names and a list of fields, often from a named tuple used to store
    queried records. Column names may contain underscores, but class
    names may not. The fields must be in this format:

        <lowercase class name>_<column name>

    Example: 'county_aland_sqmi' becomes column County.aland_sqmi'''
    classmap = {cls.lower(): cls for cls in classes}
    columns = [getattr(globals()[classmap[f.split('_')[0]]],  # class
                       '_'.join(f.split('_')[1:]))  # attribute
               for f in fields]
    return columns


def load_country_geos(geo_session, session):
    us = Geo(name='United States', abbrev='U.S.')
    Geo(name='United States of America', abbrev='U.S.A.', alias_target=us)
    GeoData(geo=us,
            total_pop=0,
            urban_pop=0,
            latitude=39.8333333,
            longitude=-98.585522,
            land_area=0,
            water_area=0)
    # 0 values to be calculated from children
    # land: 9158022, water: 699284 www.census.gov/geo/reference/state-area.html

    glvl = GeoLevel(geo=us, level='country', designation='federal republic')
    GeoID(level=glvl, standard='ISO A2', code='US')  # ISO 3166-1 alpha-2
    GeoID(level=glvl, standard='ISO A3', code='USA')  # ISO 3166-1 alpha-3
    GeoID(level=glvl, standard='ISO N3', code='840')  # ISO 3166-1 numeric-3


def load_subdivision1_geos(geo_session, session):
    # U.S. states plus DC and PR
    ghrps = geo_session.query(GHRP).filter(GHRP.sumlev == '040',
                                           GHRP.geocomp == '00',
                                           # GHRP.statefp == '48'
                                           ).all()
    us = Geo['us']
    print 'Loading states and equivalents...'
    for ghrp in ghrps:
        state = ghrp.state
        print '\t{usps} - {name}'.format(usps=state.stusps, name=state.name)
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
        glvl = GeoLevel(geo=g, level='subdivision1', designation='state')
        GeoID(level=glvl, standard='FIPS', code=ghrp.statefp)
        GeoID(level=glvl, standard='ANSI', code=ghrp.statens)

    # Handle special cases
    pr = us['pr']
    pr.levels['subdivision1'].designation = 'territory'
    dc = us['dc']
    dc.levels['subdivision1'].designation = 'federal district'

    # Remaining U.S. territories
    territories = {
        #      fips  ansi        tpop   upop   latitude     longitude     land water (sq. km.)
        'AS': ('60', '01802701', 55519, 48645, -14.2638166, -170.6620902, 198, 1307),
        'GU': ('66', '01802705', 159358, 149918, +13.4383000, +144.7729285, 543, 935),
        'MP': ('69', '01779809', 53883, 48997, +14.9367835, +145.6010210, 472, 4644),
        'UM': ('74', '01878752', 0, 0, 0, 0, 0, 0),
        'VI': ('78', '01802710', 106405, 100607, +18.3267485, -064.9712501, 348, 1550)
        # Sources:
        # www2.census.gov/geo/docs/reference/state.txt
        # www.census.gov/newsroom/releases/archives/2010_census/cb13-tps62.html
    }
    more_areas = geo_session.query(State).filter(
            State.stusps.in_(['AS', 'GU', 'MP', 'UM', 'VI'])).all()
    for area in more_areas:
        print '\t{usps} - {name}'.format(usps=area.stusps, name=area.name)
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
        glvl = GeoLevel(geo=g, level='subdivision1', designation='territory')
        GeoID(level=glvl, standard='FIPS', code=fips)
        GeoID(level=glvl, standard='ANSI', code=ansi)

    # Update US population and area values based on subdivision1 values
    children = us.children.all()
    us.data.total_pop = sum((c.data.total_pop for c in children if c.data))
    us.data.urban_pop = sum((c.data.urban_pop for c in children if c.data))
    us.data.land_area = sum((c.data.land_area for c in children if c.data))
    us.data.water_area = sum((c.data.water_area for c in children if c.data))


def load_subdivision2_geos(geo_session, session):
    CountyRecord = namedtuple('CountyRecord',
                              'county_name, county_stusps, geoclass_name, '
                              'ghrp_countyid, ghrp_countyns, '
                              'ghrp_p0020001, ghrp_p0020002, '
                              'ghrp_intptlat, ghrp_intptlon, '
                              'ghrp_arealand, ghrp_areawatr')

    columns = derive_columns(classes=['County', 'Geoclass', 'GHRP'],
                             fields=CountyRecord._fields)

    # U.S. counties including independent cities
    records = (geo_session.query(GHRP).join(GHRP.county)
                                      .join(GHRP.countyclass)
                                      .filter(GHRP.sumlev == '050',
                                              GHRP.geocomp == '00')
                                      .values(*columns))
    # Counties containing the 3 Chula Vista CDPs:
    #                         GHRP.countyid.in_(['48061', '48323', '48507']),

    us = Geo['us']
    state = None
    stusps = prior_stusps = None
    print 'Loading counties and equivalents in...'
    for record in records:
        r = CountyRecord(*record)
        stusps = r.county_stusps
        if stusps != prior_stusps:
            state = us[stusps]
            print '\t' + state.name
            prior_stusps = stusps
        name = r.county_name
        g = Geo(name=name,
                path_parent=state,
                parents=[state])
        GeoData(geo=g,
                total_pop=r.ghrp_p0020001,
                urban_pop=r.ghrp_p0020002,
                latitude=r.ghrp_intptlat,
                longitude=r.ghrp_intptlon,
                land_area=(r.ghrp_arealand * 1.0) / 10**6,
                water_area=(r.ghrp_areawatr * 1.0) / 10**6)
        glvl = GeoLevel(geo=g, level='subdivision2',
                        designation=r.geoclass_name.lower())
        GeoID(level=glvl, standard='FIPS', code=r.ghrp_countyid)
        ansi = r.ghrp_countyns
        if ansi is not None and GeoID[('ANSI', ansi)] is None:
            GeoID(level=glvl, standard='ANSI', code=r.ghrp_countyns)

    # County equivalents in remaining U.S. territories
    more_areas = (
        # fips     ansi      stusps  name                desig
        ('60010', '01805240', 'AS', 'Eastern District', 'District'),
        ('60020', '01805242', 'AS', "Manu'a District", 'District'),
        ('60030', '01805243', 'AS', 'Rose Island', 'Island'),
        ('60040', '01805244', 'AS', 'Swains Island', 'Island'),
        ('60050', '01805241', 'AS', 'Western District', 'District'),
        ('66010', '01802705', 'GU', 'Guam', 'County Equivalent'),  # dup ansi
        ('69085', '01805245', 'MP', 'Northern Islands Municipality',
                                    'Municipality'),
        ('69100', '01805246', 'MP', 'Rota Municipality', 'Municipality'),
        ('69110', '01805247', 'MP', 'Saipan Municipality', 'Municipality'),
        ('69120', '01805248', 'MP', 'Tinian Municipality', 'Municipality'),
        ('74300', None, 'UM', 'Midway Islands', 'Islands'),
        ('78010', '02378248', 'VI', 'St. Croix Island', 'Island'),
        ('78020', '02378249', 'VI', 'St. John Island', 'Island'),
        ('78030', '02378250', 'VI', 'St. Thomas Island', 'Island'),
        # Sources:
        # www.census.gov/newsroom/releases/archives/2010_census/cb13-tps62.html
    )

    territory = None
    stusps = prior_stusps = None
    for fips, ansi, stusps, name, desig in more_areas:
        if stusps != prior_stusps:
            territory = us[stusps]
            print '\t' + territory.name
            prior_stusps = stusps
        g = Geo(name=name,
                path_parent=territory,
                parents=[territory])
        glvl = GeoLevel(geo=g, level='subdivision2',
                        designation=desig.lower())
        GeoID(level=glvl, standard='FIPS', code=fips)
        if ansi is not None and GeoID[('ANSI', ansi)] is None:
            GeoID(level=glvl, standard='ANSI', code=ansi)

    # TODO: Consolidate Guam county into Guam the territory


def load_place_geos(geo_session, session):

    PlaceRecord = namedtuple('PlaceRecord',
                             'place_name, lsad_display, '
                             'ghrp_statefp, ghrp_countyid, ghrp_countycc, '
                             'ghrp_placeid, ghrp_placens, '
                             'ghrp_p0020001, ghrp_p0020002, '
                             'place_intptlat, place_intptlong, '
                             'ghrp_arealand, ghrp_areawatr')

    columns = derive_columns(classes=['Place', 'LSAD', 'GHRP'],
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
    print 'Loading places in...'
    for record in records:
        r = PlaceRecord(*record)

        statefp = r.ghrp_statefp
        # If it's a new state, update variables
        if statefp != prior_statefp:
            state = GeoID[('FIPS', statefp)].level.geo
            print '\t' + state.name
            prior_statefp = statefp

        placeid = r.ghrp_placeid

        # If it's a new place, reset variables
        if placeid != prior_placeid:
            counties = []
            total_pop = urban_pop = 0
            land_area = water_area = 0
            prior_placeid = placeid

        county = GeoID[('FIPS', r.ghrp_countyid)].level.geo

        if county is not None:
            counties.append(county)
        total_pop += r.ghrp_p0020001
        urban_pop += r.ghrp_p0020002
        land_area += (r.ghrp_arealand * 1.0) / 10**6
        water_area += (r.ghrp_areawatr * 1.0) / 10**6

        # We're on the last record for the current place, so create geo
        if (not records.has_next() or
                PlaceRecord(*records.peek()).ghrp_placeid != placeid):

            desig = r.lsad_display
            desig = desig.split(' (actual text)')[0]
            desig = desig.split(' (prefix)')[0]
            desig = desig.split(' (suffix)')[0]
            place_name = r.place_name
            if desig != '':
                place_name = place_name.split(desig)[0].strip()

            print '\t\t' + place_name + '(' + placeid + ')'

            # check for existing place with same key
            key = Geo.create_key(name=place_name, path_parent=state)
            existing = Geo[key]
            if existing is not None:
                # TODO: add an optional 'qualifier' attribute to Geo
                if existing.alias_target is None:
                    # if existing conflict is a place, rename it, make
                    # an alias to it, and keep track of its population
                    if (existing.levels.get('place', None) is not None):
                        existing_desig = existing.levels['place'].designation
                        existing.name += (' (' + existing_desig + ' in ' +
                                          existing.parents[0].name + ')')
                        alias = Geo(name=place_name,
                                    path_parent=state,
                                    alias_target=existing)
                        conflicts[key] = existing.data.total_pop
                    # if existing conflict is a parent county, just add
                    # a geo level for the place to the county
                    elif (existing.levels.get(
                                            'subdivision2', None) is not None):
                        if existing not in counties:
                            raise NameError('place key conflicts with '
                                            'subdivision2 key, yet place is '
                                            'not in subdivision2')
                        glvl = GeoLevel(geo=existing,
                                        level='place',
                                        designation=desig)
                        GeoID(level=glvl, standard='FIPS', code=placeid)
                        placens = r.ghrp_placens
                        if GeoID[('ANSI', placens)] is None:
                            GeoID(level=glvl, standard='ANSI', code=placens)

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
                    latitude=r.place_intptlat,
                    longitude=r.place_intptlong,
                    land_area=land_area,
                    water_area=water_area)
            glvl = GeoLevel(geo=g, level='place', designation=desig)
            GeoID(level=glvl, standard='FIPS', code=placeid)
            placens = r.ghrp_placens
            if GeoID[('ANSI', placens)] is None:
                GeoID(level=glvl, standard='ANSI', code=placens)

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
    dc_county = GeoID[('FIPS', '11001')].level.geo
    consolidated[dc_county] = dc_county.children.all()
    # Yakutat City and Borough contains Yakutat CDP
    # yak_cab = GeoID[('FIPS', '02282')].level.geo
    # consolidated[yak_cab] = yak_cab.children.all()

    for county, places in consolidated.iteritems():

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
                balance.levels['place'].designation = (
                                        'consolidated government (balance)')
                # balance geos only related to immediate parents
                balance.parents.remove(balance.path_parent)
                GeoLevel(geo=county, level='place', designation='city')
                alias = Geo(name=base_name, alias_target=county)
                if place_name != base_name:
                    Geo(name=place_name, alias_target=county)
                alias.promote_to_alias_target()

            continue
        place = places[0]
        county_parents = [p for p in place.parents if
                          p.levels.get('subdivision2', None) is not None]

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
        if place.levels['place'].designation == '':
            place.levels['place'].designation = u'city'

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
    w = GeoID[('FIPS', '1150000')].level.geo  # Washington, DC (place)
    GeoData.unregister(w.data)
    w.data = None
    w.levels['subdivision2'].geo = dc
    w.levels['place'].geo = dc
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
    mfb.levels['place'].geo = mf  # move levels and ids
    mf.levels['place'].designation = 'city'

    mfb.name = 'Milford (balance)'
    GeoLevel(geo=mfb, level='place', designation='city balance')
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

    columns = derive_columns(classes=['CBSA', 'GHRP'],
                             fields=CBSARecord._fields)

    # U.S. places by county equivalent with CBSA/CSA data
    records = (geo_session.query(GHRP)
                          .join(GHRP.county)
                          .join(County.cbsa)
                          .filter(
                              GHRP.sumlev == '155',
                              GHRP.geocomp == '00',
                              # GHRP.statefp.in_(['25', '33', '44', '9', '11']),
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

    print 'Loading CBSAs and CSAs...'
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
        state = GeoID[('FIPS', statefp)].level.geo
        if state.levels.get('subdivision1', None) is None:
            raise ValueError('State {!r} missing geo level'.format(state))
        if state.alias_target is not None:
            raise ValueError('State {!r} is an alias'.format(state))
        # Assemble pop of state within CBSA
        if cbsa_states.get(state, None) is None:
            cbsa_states[state] = 0
        cbsa_states[state] += r.ghrp_p0020001

        countyid = r.ghrp_countyid
        county = GeoID[('FIPS', countyid)].level.geo
        if county.levels.get('subdivision2', None) is None:
            raise ValueError('County {!r} missing geo level'.format(county))
        if county.alias_target is not None:
            raise ValueError('County {!r} is an alias'.format(county))
        # Store pop of county (CBSAs consist of whole counties)
        if cbsa_counties.get(county, None) is None:
            cbsa_counties[county] = county.data.total_pop

        placeid = r.ghrp_placeid
        place = GeoID[('FIPS', placeid)].level.geo
        if place.levels.get('place', None) is None:
            raise ValueError('Place {!r} missing geo level'.format(place))
        if place.alias_target is not None:
            raise ValueError('Place {!r} is an alias'.format(place))
        # Assemble pop of place within CBSA
        if cbsa_places.get(place, None) is None:
            cbsa_places[place] = 0
        cbsa_places[place] += r.ghrp_p0020001

        # Add consolidated counties with children as places
        # (those without children are already added)
        if (county.levels.get('place', None) is not None and
                cbsa_places.get(county, None) is None):
            cbsa_places[county] = county.data.total_pop

        # We're on the last record for the current CBSA, so create geo
        if (not records.has_next() or
                CBSARecord(*records.peek()).cbsa_cbsa_code != cbsa_code):

            cbsa_name = r.cbsa_cbsa_name
            print u'\t\tCBSA: {name} ({code})'.format(name=cbsa_name,
                                                      code=cbsa_code)

            cbsa = Geo(name=cbsa_name + ' Area',
                       the_prefix=True,
                       path_parent=us,
                       parents=cbsa_states.keys(),
                       children=cbsa_counties.keys() + cbsa_places.keys(),
                       data_level='subdivision2')  # Calculate from counties

            cbsa_glvl = GeoLevel(geo=cbsa, level='cbsa',
                                 designation=r.cbsa_cbsa_type.lower())
            GeoID(level=cbsa_glvl, standard='CBSA', code=cbsa_code)

            for place in cbsa_places:
                if (cbsa_place_1 is None or
                        cbsa_places[place] > cbsa_places[cbsa_place_1]):
                    cbsa_place_1, cbsa_place_2 = place, cbsa_place_1
                elif (cbsa_place_2 is None or
                        cbsa_places[place] > cbsa_places[cbsa_place_2]):
                    cbsa_place_2 = place

            #     # Prioritize non-CDPs over CDPs
            #     # Removed because these are actually exceptions
            #     if place.levels['place'].designation == 'CDP':
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

            # what if there's only one place in the CBSA name?

            if cbsa_main_place is not None and not name_match:
                cbsas_with_unnamed_main_places[cbsa] = (
                        cbsa_places, cbsa_main_place)

            # Is this necessary?
            # if cbsa_main_place is None:
            #     cbsa_top_places = sorted(cbsa_places,
            #                                 key=lambda p: p.data.total_pop,
            #                                 reverse=True)
            #     for i, place in enumerate(cbsa_places):
            #         if cbsa_name.find(place.name) > -1:
            #             cbsa_main_place = place
            #         else:
            #             for alias in place.aliases.all():
            #                 if cbsa_name.find(alias.name) > -1:
            #                     cbsa_main_place = place
            #                     break
            #         if cbsa_main_place == place:
            #             # for testing:
            #             if i > 0:
            #                 cbsas_not_aliased_by_top_place[g] = cbsa_places[:i+1]
            #             break

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
                    print u'\t\tCSA: {name} ({code})'.format(name=csa_name,
                                                             code=csa_code)

                    csa = Geo(name='Greater ' + csa_name + ' Area',
                              the_prefix=True,
                              path_parent=us,
                              parents=csa_states.keys(),
                              children=(csa_cbsa_main_places.keys() +
                                        csa_counties.keys() +
                                        csa_places.keys()),
                              data_level='cbsa')  # Calculate from cbsas

                    csa_glvl = GeoLevel(geo=csa, level='csa',
                                        designation='CSA')
                    GeoID(level=csa_glvl, standard='CSA', code=csa_code)

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
                                the_prefix=False))

                        greater_csa_area_alias = (
                            Geo(name=('Greater ' + csa_mp_name + ' Area'),
                                abbrev=('Greater ' + csa_mp_abbrev + ' Area'
                                        if csa_mp_abbrev else None),
                                path_parent=csa_state,
                                alias_target=csa,
                                the_prefix=True))

                        if csa_state is csa_main_place.path_parent:
                            new_csa_target = greater_csa_alias

                    new_csa_target.promote_to_alias_target()

            # CBSA aliases

            # Ensure we've just created a CSA or we're not in a CSA
            if not (csa or csa_code == ''):
                continue

            cbsa_targets = csa_cbsa_main_places.iterkeys() if csa else (cbsa, )

            for cbsa_target in cbsa_targets:

                if csa:
                    cbsa_main_place = csa_cbsa_main_places[cbsa_target]
                    alias_states = (p for p in cbsa_target.parents
                                    if p.levels.get('subdivision1', None))
                else:
                    alias_states = cbsa_states.iterkeys()

                cbsa_mp_name = cbsa_main_place.name
                cbsa_mp_abbrev = cbsa_main_place.abbrev

                for alias_state in alias_states:

                    if ((csa and csa_main_cbsa is cbsa_target) or
                        cbsa_target.levels['cbsa'].designation ==
                            'micropolitan statistical area'):
                        cbsa_area_alias = (
                            Geo(name=cbsa_mp_name + ' Area',
                                abbrev=(cbsa_mp_abbrev + ' Area'
                                        if cbsa_mp_abbrev else None),
                                path_parent=alias_state,
                                alias_target=cbsa_target,
                                the_prefix=True))

                        if alias_state is cbsa_main_place.path_parent:
                            new_cbsa_target = cbsa_area_alias
                    else:
                        cbsa_area_alias = (
                            Geo(name=cbsa_mp_name + ' Area',
                                abbrev=(cbsa_mp_abbrev + ' Area'
                                        if cbsa_mp_abbrev else None),
                                path_parent=alias_state,
                                alias_target=cbsa_target,
                                the_prefix=True))

                        greater_cbsa_alias = (
                            Geo(name='Greater ' + cbsa_mp_name,
                                abbrev=('Greater ' + cbsa_mp_abbrev
                                        if cbsa_mp_abbrev else None),
                                path_parent=alias_state,
                                alias_target=cbsa_target,
                                the_prefix=False))

                        greater_cbsa_area_alias = (
                            Geo(name='Greater ' + cbsa_mp_name + ' Area',
                                abbrev=('Greater ' + cbsa_mp_abbrev + ' Area'
                                        if cbsa_mp_abbrev else None),
                                path_parent=alias_state,
                                alias_target=cbsa_target,
                                the_prefix=True))

                        if alias_state is cbsa_main_place.path_parent:
                            new_cbsa_target = greater_cbsa_alias

                new_cbsa_target.promote_to_alias_target()

    print 'CBSAs with unnamed main places...'
    for cbsa, (cbsa_places, cbsa_main_place) in (
                                cbsas_with_unnamed_main_places.iteritems()):
        sorted_places = sorted(cbsa_places.keys(),
                               key=lambda p: cbsa_places[p],
                               reverse=True)
        print u'\t{cbsa}:'.format(cbsa=cbsa.trepr())
        for i, place in enumerate(sorted_places):
            if i == 10:
                print '\t\t(10 of {} places)'.format(len(sorted_places))
                break
            cbsa_pop = cbsa_places[place]
            pop_total = place.data.total_pop
            print (u'\t\t{place}{main}: {cbsa_pop:,}'.format(
                    place=place.trepr(),
                    main='*' if place == cbsa_main_place else '',
                    cbsa_pop=cbsa_pop) +
                   (' of {pop_total:,}'.format(
                    pop_total=pop_total) if cbsa_pop != pop_total else ''))

    print 'CBSAs without main places...'
    for cbsa, (p1_tuple, p2_tuple) in cbsas_without_main_places.iteritems():
        p1_geo, p1_pop = p1_tuple
        p2_geo, p2_pop = p2_tuple
        p1_total, p2_total = p1_geo.data.total_pop, p2_geo.data.total_pop
        print u'\t{cbsa}:'.format(cbsa=cbsa.trepr())
        print (u'\t\t{p1_geo}: {p1_pop:,}'.format(
                    p1_geo=p1_geo.trepr(),
                    p1_pop=p1_pop) +
               (' of {p1_total:,}'.format(
                    p1_total=p1_total) if p1_pop != p1_total else ''))
        print (u'\t\t{p2_geo}: {p2_pop:,} of {p2_total:,}'.format(
                    p2_geo=p2_geo.trepr(),
                    p2_pop=p2_pop) +
               (' of {p2_total:,}'.format(
                    p2_total=p2_total) if p2_pop != p2_total else ''))

if __name__ == '__main__':
    # Session for geo.db, which contains the geo source data
    geo_dsm = DataSessionManager(db_config=DevConfig.GEO_DATABASE,
                                 ModelBases=[BaseGeoDataModel])
    geo_session = geo_dsm.session

    # Session for main Intertwine db, where geo data is loaded
    db = Manager(Model=BaseGeoModel, config=DevConfig)
    session = db.session
    extend_declarative_base(BaseGeoModel, session=session)
    db.create_all()

    Trackable.register_existing(session, Geo, GeoData, GeoLevel, GeoID)
    Trackable.clear_updates()

    load_geos(geo_session, session)