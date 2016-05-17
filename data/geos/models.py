#!/usr/bin/env python
# -*- coding: utf-8 -*-
from alchy.model import ModelBase, make_declarative_base
from sqlalchemy import (orm, types, Column, ForeignKey, Index,
                        PrimaryKeyConstraint, ForeignKeyConstraint)

from intertwine.utils import AutoTablenameMixin

BaseGeoDataModel = make_declarative_base(Base=ModelBase)


class State(BaseGeoDataModel, AutoTablenameMixin):
    statefp = Column(types.String(2), primary_key=True)  # 48
    stusps = Column(types.String(2), unique=True)       # TX
    name = Column(types.String(60), unique=True)        # Texas
    statens = Column(types.String(8), unique=True)      # 01779801


class CBSA(BaseGeoDataModel, AutoTablenameMixin):
    cbsa_code = Column(types.String(5))                 # 12420
    metro_division_code = Column(types.String(5))
    csa_code = Column(types.String(3))
    cbsa_name = Column(types.String(60))                # Austin-Round Rock, TX
    cbsa_type = Column(types.String(30))                # Metro...(vs Micro...)
    metro_division_name = Column(types.String(60))
    csa_name = Column(types.String(60))
    county_name = Column(types.String(60))              # Travis County
    state_name = Column(types.String(60))               # Texas
    statefp = Column(types.String(2))                   # 48
    countyfp = Column(types.String(3))                  # 453
    county = orm.relationship('County', back_populates='cbsa', uselist=False)
    county_type = Column(types.String(30))              # Central (vs Outlying)

    __table_args__ = (
        PrimaryKeyConstraint('statefp', 'countyfp'),
        {}
        )


class County(BaseGeoDataModel, AutoTablenameMixin):
    stusps = Column(types.String(2),                    # TX
                    ForeignKey('state.stusps'))
    state = orm.relationship('State')
    statefp = Column(types.String(2))                   # 48
    countyfp = Column(types.String(3))                  # 453
    name = Column(types.String(60))                     # Travis County
    classfp = Column(types.String(2))                   # H1
    cbsa = orm.relationship('CBSA', back_populates='county')

    __table_args__ = (
        PrimaryKeyConstraint('statefp', 'countyfp'),
        ForeignKeyConstraint(['statefp', 'countyfp'],
                             ['cbsa.statefp', 'cbsa.countyfp']),
        {}
        )


class Place(BaseGeoDataModel, AutoTablenameMixin):
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


class LSAD(BaseGeoDataModel, AutoTablenameMixin):
    lsad_code = Column(types.String(2), primary_key=True)  # 25
    lsad_description = Column(types.String(60))         # 'city (suffix)'
    geo_entity_type = Column(types.String(600))         # 'Consolidated City,
    # County or Equivalent Feature, County Subdivision, Economic Census Place,
    # Incorporated Place'


class GHR(BaseGeoDataModel):
    __tablename__ = 'ghr'

    # RECORD CODES
    fileid = Column(types.String(6))
    stusab = Column(types.String(2))
    sumlev = Column(types.String(3))
    geocomp = Column(types.String(2))
    chariter = Column(types.String(3))
    cifsn = Column(types.String(2))
    logrecno = Column(types.Integer, primary_key=True)  # Change to Integer
    f02 = orm.relationship('F02', back_populates='ghr', uselist=False)

    # GEOGRAPHIC AREA CODES
    region = Column(types.String(1))
    division = Column(types.String(1))
    statefp = Column(types.String(2), ForeignKey('state.statefp'))
    state = orm.relationship('State', viewonly=True)

    countyfp = Column(types.String(3))
    county = orm.relationship('County')

    countycc = Column(types.String(2))
    countysc = Column(types.String(2))
    cousub = Column(types.String(5))
    cousubcc = Column(types.String(2))
    cousubsc = Column(types.String(2))
    placefp = Column(types.String(5))
    place = orm.relationship('Place')

    placecc = Column(types.String(2))
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
    arealand = Column(types.Integer)
    areawatr = Column(types.Integer)
    name = Column(types.String(90))
    funcstat = Column(types.String(1))
    gcuni = Column(types.String(1))
    pop100 = Column(types.Integer)
    hu100 = Column(types.Integer)
    intptlat = Column(types.Float)
    intptlon = Column(types.Float)
    lsadc = Column(types.String(2))
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

    geoid = Column(types.String(7), ForeignKey('place.geoid'))

    __table_args__ = (
        ForeignKeyConstraint(['statefp', 'countyfp'],
                             ['county.statefp', 'county.countyfp']),
        {}
        )


class F02(BaseGeoDataModel):
    __tablename__ = 'f02'
    fileid = Column(types.String(6))
    stusab = Column(types.String(2))
    chariter = Column(types.String(3))
    cifsn = Column(types.String(2))
    logrecno = Column(types.Integer,
                      ForeignKey('ghr.logrecno'),
                      primary_key=True)
    ghr = orm.relationship('GHR', back_populates='f02')

    p0020001 = Column(types.Integer)
    p0020002 = Column(types.Integer)
    p0020003 = Column(types.Integer)
    p0020004 = Column(types.Integer)
    p0020005 = Column(types.Integer)
    p0020006 = Column(types.Integer)
