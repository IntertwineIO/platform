#!/usr/bin/env python
# -*- coding: utf-8 -*-
import re
from collections import namedtuple

from alchy.model import ModelBase, make_declarative_base
from sqlalchemy import (orm, types, Column, ForeignKey, Index,
                        PrimaryKeyConstraint, ForeignKeyConstraint)

from intertwine.utils.mixins import AutoTablenameMixin, KeyedUp

BaseGeoDataModel = make_declarative_base(Base=ModelBase)


class State(KeyedUp, AutoTablenameMixin, BaseGeoDataModel):
    STATE = 'state'
    TERRITORY = 'territory'
    FEDERAL_DISTRICT = 'federal district'

    name = Column(types.String(60), unique=True)         # Texas
    stusps = Column(types.String(2), unique=True)        # TX
    statefp = Column(types.String(2), primary_key=True)  # 48
    statens = Column(types.String(8), unique=True)       # 01779801

    KEYED_UP_FIELDS = ('name', 'stusps', 'statefp', 'statens')

    TERRITORIES = {'PR', 'AS', 'GU', 'MP', 'UM', 'VI'}
    SMALL_TERRITORIES = {'AS', 'GU', 'MP', 'UM', 'VI'}

    STATES_WITH_MCDS = {
        'AR', 'CT', 'IA', 'IL', 'IN', 'KS', 'LA', 'MA', 'MD', 'ME', 'MI', 'MN',
        'MO', 'MS', 'NC', 'ND', 'NE', 'NH', 'NJ', 'NY', 'OH', 'PA', 'RI', 'SD',
        'TN', 'VA', 'VT', 'WI', 'WV', 'PR', 'AS', 'GU', 'MP', 'VI'}

    STATES_WITH_MCDS_AS_GOVERNMENTAL_UNITS = {
        'CT', 'IL', 'IN', 'KS', 'ME', 'MA', 'MI', 'MN', 'MO', 'NE', 'NH', 'NJ',
        'NY', 'ND', 'OH', 'PA', 'RI', 'SD', 'VT', 'WI'}

    STATES_WHERE_MCDS_SERVE_AS_PLACES = {
        'CT', 'ME', 'MA', 'MI', 'MN', 'NH', 'NJ', 'NY', 'PA', 'RI', 'VT', 'WI'}

    STATES_WITH_NON_PLACE_COUSUBS = {
        'AR', 'IL', 'KS', 'LA', 'MD', 'MN', 'MS', 'NC', 'NE', 'TN', 'VA', 'WV'}


class CBSA(AutoTablenameMixin, BaseGeoDataModel):
    '''Core Based Statistical Area (CBSA)'''
    CORE_BASED_STATISTICAL_AREA = 'core based statistical area'

    cbsa_code = Column(types.String(5))                 # 12420
    metro_division_code = Column(types.String(5))
    csa_code = Column(types.String(3))
    cbsa_name = Column(types.String(60))                # Austin-Round Rock, TX
    cbsa_type = Column(types.String(30))                # Metro...(vs Micro...)
    metro_division_name = Column(types.String(60))
    csa_name = Column(types.String(60))
    county_name = Column(types.String(60))              # Travis County
    state_name = Column(types.String(60))               # Texas
    statefp = Column(types.String(2), ForeignKey('state.statefp'))  # 48
    state = orm.relationship('State', viewonly=True)

    countyfp = Column(types.String(3))                  # 453
    county_type = Column(types.String(30))              # Central (vs Outlying)

    countyid = Column(types.String(5), ForeignKey('county.geoid'),
                      primary_key=True)
    county = orm.relationship('County', uselist=False, back_populates='cbsa')


class County(AutoTablenameMixin, BaseGeoDataModel):
    COUNTY = 'county'

    stusps = Column(types.String(2),                    # TX
                    ForeignKey('state.stusps'))
    state = orm.relationship('State')
    geoid = Column(types.String(5), primary_key=True)   # 48453
    cbsa = orm.relationship('CBSA', uselist=False, back_populates='county')

    ansicode = Column(types.String(8), unique=True)     # 01384012
    name = Column(types.String(60))                     # Travis County
    pop10 = Column(types.Integer)                       # 1024266
    hu10 = Column(types.Integer)                        # 441240
    aland = Column(types.Integer)                       # 2564612388
    awater = Column(types.Integer)                      # 84967219
    aland_sqmi = Column(types.Float)                    # 990.202
    awater_sqmi = Column(types.Float)                   # 32.806
    intptlat = Column(types.Float)                      # 30.239513
    intptlong = Column(types.Float)                     # -97.69127


class Cousub(AutoTablenameMixin, BaseGeoDataModel):
    COUNTY_SUBDIVISION = 'county subdivision'

    BRONX = '00978756'
    BROOKLYN = '00978759'
    MANHATTAN = '00979190'
    QUEENS = '00979404'
    STATEN_ISLAND = '00979522'

    NYC_ANSI_CODES = {BRONX, BROOKLYN, MANHATTAN, QUEENS, STATEN_ISLAND}

    stusps = Column(types.String(2),                    # MA
                    ForeignKey('state.stusps'))
    state = orm.relationship('State')
    geoid = Column(types.String(10), primary_key=True)  # 2502178690
    ansicode = Column(types.String(8), unique=True)     # 00618333
    name = Column(types.String(60))                     # Westwood town
    funcstat = Column(types.String(1))                  # A
    pop10 = Column(types.Integer)                       # 14618
    hu10 = Column(types.Integer)                        # 5431
    aland = Column(types.Integer)                       # 28182837
    awater = Column(types.Integer)                      # 740388
    aland_sqmi = Column(types.Float)                    # 10.881
    awater_sqmi = Column(types.Float)                   # 0.286
    intptlat = Column(types.Float)                      # 42.219645
    intptlong = Column(types.Float)                     # -71.216769

    invalid_name_pattern = re.compile(r'\d+')


class Place(AutoTablenameMixin, BaseGeoDataModel):
    PLACE = 'place'
    CDP = 'CDP'

    stusps = Column(types.String(2),                    # TX
                    ForeignKey('state.stusps'))
    state = orm.relationship('State')
    geoid = Column(types.String(7), primary_key=True)   # 4805000
    ansicode = Column(types.String(8), unique=True)     # 02409761
    name = Column(types.String(60))                     # Austin city
    lsad_code = Column(types.String(2),
                       ForeignKey('lsad.lsad_code'))    # 25
    lsad = orm.relationship('LSAD')
    funcstat = Column(types.String(1))                  # A
    pop10 = Column(types.Integer)                       # 790390
    hu10 = Column(types.Integer)                        # 354241
    aland = Column(types.Integer)                       # 771546901
    awater = Column(types.Integer)                      # 18560605
    aland_sqmi = Column(types.Float)                    # 297.896
    awater_sqmi = Column(types.Float)                   # 7.166
    intptlat = Column(types.Float)                      # 30.307182
    intptlong = Column(types.Float)                     # -97.755996


class LSAD(KeyedUp, AutoTablenameMixin, BaseGeoDataModel):
    PREFIX = 'prefix'
    SUFFIX = 'suffix'
    AFFIXES = {PREFIX, SUFFIX}

    ACTUAL_TEXT_TAG = '(actual text)'

    PREFIX_TAG_PREFIX = '(prefix)'
    PREFIX_TAG_OF = ' of'
    PREFIX_TAG_DE = ' de'
    PREFIX_TAGS = (PREFIX_TAG_PREFIX, PREFIX_TAG_OF, PREFIX_TAG_DE)

    SUFFIX_TAG_SUFFIX = '(suffix)'
    SUFFIX_TAG_BALANCE = '(balance)'
    SUFFIX_TAGS = (SUFFIX_TAG_SUFFIX, SUFFIX_TAG_BALANCE)

    LSAD_ANNOTATIONS = (ACTUAL_TEXT_TAG, PREFIX_TAG_PREFIX, SUFFIX_TAG_SUFFIX)

    PREFIX_REMAINDER_OF = 'Remainder of'
    EXTRA_PREFIXES = (PREFIX_REMAINDER_OF,)

    SUFFIX_PART = '(part)'
    SUFFIX_BALANCE = '(balance)'
    EXTRA_SUFFIXES = (SUFFIX_PART, SUFFIX_BALANCE)

    lsad_code = Column(types.String(2), primary_key=True)  # 25
    description = Column(types.String(60))              # 'city (suffix)'
    geo_entity_type = Column(types.String(600))         # 'Consolidated City,
    # County or Equivalent Feature, County Subdivision, Economic Census Place,
    # Incorporated Place'

    LSADMapRecord = namedtuple(
        'LSADMapRecord',
        ('lsad_code', 'description', 'geo_entity_type', 'display', 'affix',
            'display_affix'))

    KEYED_UP_FIELDS = ('lsad_code', 'display_affix')

    @classmethod
    def _all_the_keyed_up_things(cls):
        lsads = cls.query.order_by(cls.lsad_code)
        lsad_records = [
            cls.LSADMapRecord(
                lsad_code=lsad.lsad_code,
                description=lsad.description,
                geo_entity_type=lsad.geo_entity_type,
                display=lsad.display,
                affix=lsad.affix,
                display_affix=(lsad.display, lsad.affix))
            for lsad in lsads]
        return lsad_records

    @property
    def display(self):
        text = self.description
        for annotation in self.LSAD_ANNOTATIONS:
            annotation_len = len(annotation)
            if text[-annotation_len:] == annotation:
                text = text[:-annotation_len].strip()
        return text

    @property
    def affix(self):
        for suffix_tag in self.SUFFIX_TAGS:
            suffix_tag_len = len(suffix_tag)
            if self.description[-suffix_tag_len:] == suffix_tag:
                return self.SUFFIX

        for prefix_tag in self.PREFIX_TAGS:
            prefix_tag_len = len(prefix_tag)
            if self.description[-prefix_tag_len:] == prefix_tag:
                return self.PREFIX

    @classmethod
    def deaffix(cls, affixed_name, lsad_code):
        deannotated_name = affixed_name

        extra_prefixes, extra_suffixes = set(), set()

        # Add all extra prefixes/suffixes found, but only remove first?
        # Or remove extras 1 by 1 checking for LSAD match?

        for prefix in cls.EXTRA_PREFIXES:
            prefix_len = len(prefix)
            if affixed_name[:prefix_len] == prefix:
                extra_prefixes.add(prefix)
                deannotated_name = deannotated_name[prefix_len:].strip()
                break

        for suffix in cls.EXTRA_SUFFIXES:
            suffix_len = len(suffix)
            if affixed_name[-suffix_len:] == suffix:
                extra_suffixes.add(suffix)
                deannotated_name = deannotated_name[:-suffix_len].strip()
                break

        lsad_record = cls.get_by('lsad_code', lsad_code)

        if not lsad_record:
            return deannotated_name, None, None, extra_prefixes, extra_suffixes

        lsad, affix = lsad_record.display, lsad_record.affix

        lsad = lsad if lsad else None

        if lsad is None or affix is None:
            return (deannotated_name, lsad, affix, extra_prefixes,
                    extra_suffixes)

        lsad_len = len(lsad)

        if affix == cls.SUFFIX:
            name = deannotated_name[:-lsad_len].strip()
            removed_value = deannotated_name[-lsad_len:]

        elif affix == cls.PREFIX:
            name = deannotated_name[lsad_len:].strip()
            removed_value = deannotated_name[:lsad_len]

        else:
            raise ValueError("Affix '{affix}' must be in {affixes}"
                             .format(affix=affix, affixes=cls.AFFIXES))

        if removed_value != lsad:
            raise ValueError(
                "'{lsad}' not found as {affix} of '{name}'"
                .format(lsad=lsad, affix=affix, name=affixed_name))

        return name, lsad, affix, extra_prefixes, extra_suffixes


class Geoclass(AutoTablenameMixin, BaseGeoDataModel):
    # renamed from classfp
    geoclassfp = Column(types.String(2), primary_key=True)  # C1
    category = Column(types.String(60))                 # Incorporated Place
    name = Column(types.String(60))                     # Incorporated Place
    description = Column(types.String(300))             # An active
    # incorporated place that does not serve as a county subdivision equivalent


class GHRP(BaseGeoDataModel):
    '''
    Geographic Header Row Plus (GHRP)

    Contains all columns from the Geographic Header Row (GHR) plus:
    county_id, the concatenation of statefp and countyfp
    cousub_id, the concatenation of statefp, countyfp, and cousubfp
    place_id, the concatenation of statefp and placefp
    all columns from File 02.
    '''
    DATA_FIELDS = (
        'p0020001', 'p0020002', 'intptlat', 'intptlon', 'arealand', 'areawatr')

    __tablename__ = 'ghrp'

    # RECORD CODES
    fileid = Column(types.String(6))
    stusab = Column(types.String(2))
    sumlev = Column(types.String(3))
    geocomp = Column(types.String(2))
    chariter = Column(types.String(3))
    cifsn = Column(types.String(2))
    logrecno = Column(types.Integer, primary_key=True)  # Changed to Integer
    # f02 = orm.relationship('F02', back_populates='ghrp', uselist=False)

    # GEOGRAPHIC AREA CODES
    region = Column(types.String(1))
    division = Column(types.String(1))

    # Renamed from state
    statefp = Column(types.String(2), ForeignKey('state.statefp'))
    state = orm.relationship('State', viewonly=True)

    # Renamed from county
    countyfp = Column(types.String(3))
    countycc = Column(types.String(2), ForeignKey('geoclass.geoclassfp'))
    countyclass = orm.relationship('Geoclass', foreign_keys='GHRP.countycc')
    countysc = Column(types.String(2))

    # Renamed from cousub
    cousubfp = Column(types.String(5))
    cousubcc = Column(types.String(2), ForeignKey('geoclass.geoclassfp'))
    cousubclass = orm.relationship('Geoclass', foreign_keys='GHRP.cousubcc')
    cousubsc = Column(types.String(2))

    # Renamed from place
    placefp = Column(types.String(5))
    placecc = Column(types.String(2), ForeignKey('geoclass.geoclassfp'))
    placeclass = orm.relationship('Geoclass', foreign_keys='GHRP.placecc')
    placesc = Column(types.String(2))

    tract = Column(types.String(6))
    blkgrp = Column(types.String(1))
    block = Column(types.String(4))
    iuc = Column(types.String(2))
    concit = Column(types.String(5))
    concitcc = Column(types.String(2))
    concitsc = Column(types.String(2))
    aianhh = Column(types.String(4))
    aianhhfp = Column(types.String(5))
    aianhhcc = Column(types.String(2))
    aihhtli = Column(types.String(1))
    aitsce = Column(types.String(3))
    aits = Column(types.String(5))
    aitscc = Column(types.String(2))
    ttract = Column(types.String(6))
    tblkgrp = Column(types.String(1))
    anrc = Column(types.String(5))
    anrccc = Column(types.String(2))
    cbsa = Column(types.String(5))
    cbsasc = Column(types.String(2))
    metdiv = Column(types.String(5))
    csa = Column(types.String(3))
    necta = Column(types.String(5))
    nectasc = Column(types.String(2))
    nectadiv = Column(types.String(5))
    cnecta = Column(types.String(3))
    cbsapci = Column(types.String(1))
    nectapci = Column(types.String(1))
    ua = Column(types.String(5))
    uasc = Column(types.String(2))
    uatype = Column(types.String(1))
    ur = Column(types.String(1))
    cd = Column(types.String(2))
    sldu = Column(types.String(3))
    sldl = Column(types.String(3))
    vtd = Column(types.String(6))
    vtdi = Column(types.String(1))
    reserve2 = Column(types.String(3))
    zcta5 = Column(types.String(5))
    submcd = Column(types.String(5))
    submcdcc = Column(types.String(2))
    sdelm = Column(types.String(5))
    sdsec = Column(types.String(5))
    sduni = Column(types.String(5))

    # AREA CHARACTERISTICS
    arealand = Column(types.Integer)  # in sq. meters
    areawatr = Column(types.Integer)  # in sq. meters
    name = Column(types.String(90))
    funcstat = Column(types.String(1))
    gcuni = Column(types.String(1))
    pop100 = Column(types.Integer)
    hu100 = Column(types.Integer)
    intptlat = Column(types.Float)
    intptlon = Column(types.Float)
    lsadc = Column(types.String(2), ForeignKey('lsad.lsad_code'))
    lsad = orm.relationship('LSAD')

    partflag = Column(types.String(1))

    # SPECIAL AREA CODES
    reserve3 = Column(types.String(6))
    uga = Column(types.String(5))
    statens = Column(types.String(8))
    countyns = Column(types.String(8))
    cousubns = Column(types.String(8))
    placens = Column(types.String(8))
    concitns = Column(types.String(8))
    aianhhns = Column(types.String(8))
    aitsns = Column(types.String(8))
    anrcns = Column(types.String(8))
    submcdns = Column(types.String(8))
    cd113 = Column(types.String(2))
    cd114 = Column(types.String(2))
    cd115 = Column(types.String(2))
    sldu2 = Column(types.String(3))
    sldu3 = Column(types.String(3))
    sldu4 = Column(types.String(3))
    sldl2 = Column(types.String(3))
    sldl3 = Column(types.String(3))
    sldl4 = Column(types.String(3))
    aianhhsc = Column(types.String(2))
    csasc = Column(types.String(2))
    cnectasc = Column(types.String(2))
    memi = Column(types.String(1))
    nmemi = Column(types.String(1))
    puma = Column(types.String(5))
    reserved = Column(types.String(18))

    # Added - concatenation of statefp and countyfp
    countyid = Column(types.String(5), ForeignKey('county.geoid'))
    county = orm.relationship('County')

    # Added - concatenation of statefp, countyfp, and cousubfp
    cousubid = Column(types.String(10), ForeignKey('cousub.geoid'))
    cousub = orm.relationship('Cousub')

    # Added - concatenation of statefp and placefp
    placeid = Column(types.String(7), ForeignKey('place.geoid'))
    place = orm.relationship('Place')

    # Added File 02 columns:
    p0020001 = Column(types.Integer)
    p0020002 = Column(types.Integer)
    p0020003 = Column(types.Integer)
    p0020004 = Column(types.Integer)
    p0020005 = Column(types.Integer)
    p0020006 = Column(types.Integer)

    __table_args__ = (
        Index('ix_ghrp',
              # ix for index
              'sumlev',
              'geocomp'),
        {}
        )


# class F02(BaseGeoDataModel):
#     __tablename__ = 'f02'
#     fileid = Column(types.String(6))
#     stusab = Column(types.String(2))
#     chariter = Column(types.String(3))
#     cifsn = Column(types.String(2))
#     logrecno = Column(types.Integer,
#                       ForeignKey('ghrp.logrecno'),
#                       primary_key=True)
#     ghrp = orm.relationship('GHRP', back_populates='f02')

#     p0020001 = Column(types.Integer)
#     p0020002 = Column(types.Integer)
#     p0020003 = Column(types.Integer)
#     p0020004 = Column(types.Integer)
#     p0020005 = Column(types.Integer)
#     p0020006 = Column(types.Integer)

#     __table_args__ = (
#         Index('ix_f02',
#               # ix for index
#               'logrecno'),
#         )
