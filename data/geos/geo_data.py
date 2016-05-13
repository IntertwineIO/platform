#!/usr/bin/env python
# -*- coding: utf-8 -*-
from alchy.model import ModelBase, make_declarative_base
from sqlalchemy import (orm, types, Column, ForeignKey, Index,
                        PrimaryKeyConstraint, ForeignKeyConstraint)

from intertwine.utils import AutoTablenameMixin

BaseGeoDataModel = make_declarative_base(Base=ModelBase)


class State(BaseGeoDataModel, AutoTablenameMixin):
    STATEFP = Column(types.String(2), primary_key=True)  # 48
    STUSPS = Column(types.String(2), unique=True)       # TX
    NAME = Column(types.String(60), unique=True)        # Texas
    STATENS = Column(types.String(8), unique=True)      # 01779801


class CBSA(BaseGeoDataModel, AutoTablenameMixin):
    CBSA_CODE = Column(types.String(5))                 # 12420
    METRO_DIVISION_CODE = Column(types.String(5))
    CSA_CODE = Column(types.String(3))
    CBSA_NAME = Column(types.String(60))                # Austin-Round Rock, TX
    CBSA_TYPE = Column(types.String(30))                # Metro...(vs Micro...)
    METRO_DIVISION_NAME = Column(types.String(60))
    CSA_NAME = Column(types.String(60))
    COUNTY_NAME = Column(types.String(60))              # Travis County
    STATE_NAME = Column(types.String(60))               # Texas
    STATEFP = Column(types.String(2))                   # 48
    COUNTYFP = Column(types.String(3))                  # 453
    COUNTY = orm.relationship('County', back_populates='CBSA', uselist=False)
    COUNTY_TYPE = Column(types.String(30))              # Central (vs Outlying)

    __table_args__ = (
        PrimaryKeyConstraint('STATEFP', 'COUNTYFP'),
        {}
        )


class County(BaseGeoDataModel, AutoTablenameMixin):
    STUSPS = Column(types.String(2),                    # TX
                    ForeignKey('state.STUSPS'))
    STATE = orm.relationship('State')
    STATEFP = Column(types.String(2))                   # 48
    COUNTYFP = Column(types.String(3))                  # 453
    NAME = Column(types.String(60))                     # Travis County
    CLASSFP = Column(types.String(2))                   # H1
    CBSA = orm.relationship('CBSA', back_populates='COUNTY')

    __table_args__ = (
        PrimaryKeyConstraint('STATEFP', 'COUNTYFP'),
        ForeignKeyConstraint(['STATEFP', 'COUNTYFP'],
                             ['cbsa.STATEFP', 'cbsa.COUNTYFP']),
        {}
        )


class Place(BaseGeoDataModel, AutoTablenameMixin):
    STUSPS = Column(types.String(2),                    # TX
                    ForeignKey('state.STUSPS'))
    STATE = orm.relationship('State')
    GEOID = Column(types.String(7), primary_key=True)   # 4805000
    ANSICODE = Column(types.String(8), unique=True)     # 02409761
    NAME = Column(types.String(60))                     # Austin city
    LSAD_CODE = Column(types.String(2),
                       ForeignKey('lsad.LSAD_CODE'))    # 25
    LSAD = orm.relationship('LSAD')
    FUNCSTAT = Column(types.String(1))                  # A
    POP10 = Column(types.Integer)                       # 790390
    HU10 = Column(types.Integer)                        # 354241
    ALAND = Column(types.Integer)                       # 771546901
    AWATER = Column(types.Integer)                      # 18560605
    ALAND_SQMI = Column(types.Float)                    # 297.896
    AWATER_SQMI = Column(types.Float)                   # 7.166
    INTPTLAT = Column(types.Float)                      # 30.307182
    INTPTLONG = Column(types.Float)                     # -97.755996


class LSAD(BaseGeoDataModel, AutoTablenameMixin):
    LSAD_CODE = Column(types.String(2), primary_key=True)  # 25
    LSAD_DESCRIPTION = Column(types.String(60))         # 'city (suffix)'
    GEO_ENTITY_TYPE = Column(types.String(600))         # 'Consolidated City,
    # County or Equivalent Feature, County Subdivision, Economic Census Place,
    # Incorporated Place'


class GHR(BaseGeoDataModel):
    __tablename__ = 'ghr'

    # RECORD CODES
    FILEID = Column(types.String(6))
    STUSAB = Column(types.String(2))
    SUMLEV = Column(types.String(3))
    GEOCOMP = Column(types.String(2))
    CHARITER = Column(types.String(3))
    CIFSN = Column(types.String(2))
    LOGRECNO = Column(types.Integer, primary_key=True)  # Change to Integer
    F02 = orm.relationship('F02', back_populates='GHR', uselist=False)

    # GEOGRAPHIC AREA CODES
    REGION = Column(types.String(1))
    DIVISION = Column(types.String(1))
    STATEFP = Column(types.String(2), ForeignKey('state.STATEFP'))
    STATE = orm.relationship('State', viewonly=True)

    COUNTYFP = Column(types.String(3))
    COUNTY = orm.relationship('County')

    COUNTYCC = Column(types.String(2))
    COUNTYSC = Column(types.String(2))
    COUSUB = Column(types.String(5))
    COUSUBCC = Column(types.String(2))
    COUSUBSC = Column(types.String(2))
    PLACEFP = Column(types.String(5))
    PLACE = orm.relationship('Place')

    PLACECC = Column(types.String(2))
    PLACESC = Column(types.String(2))
    TRACT = Column(types.String(6))
    BLKGRP = Column(types.String(1))
    BLOCK = Column(types.String(4))
    IUC = Column(types.String(2))
    CONCIT = Column(types.String(5))
    CONCITCC = Column(types.String(2))
    CONCITSC = Column(types.String(2))
    AIANHH = Column(types.String(4))
    AIANHHFP = Column(types.String(5))
    AIANHHCC = Column(types.String(2))
    AIHHTLI = Column(types.String(1))
    AITSCE = Column(types.String(3))
    AITS = Column(types.String(5))
    AITSCC = Column(types.String(2))
    TTRACT = Column(types.String(6))
    TBLKGRP = Column(types.String(1))
    ANRC = Column(types.String(5))
    ANRCCC = Column(types.String(2))
    CBSA = Column(types.String(5))
    CBSASC = Column(types.String(2))
    METDIV = Column(types.String(5))
    CSA = Column(types.String(3))
    NECTA = Column(types.String(5))
    NECTASC = Column(types.String(2))
    NECTADIV = Column(types.String(5))
    CNECTA = Column(types.String(3))
    CBSAPCI = Column(types.String(1))
    NECTAPCI = Column(types.String(1))
    UA = Column(types.String(5))
    UASC = Column(types.String(2))
    UATYPE = Column(types.String(1))
    UR = Column(types.String(1))
    CD = Column(types.String(2))
    SLDU = Column(types.String(3))
    SLDL = Column(types.String(3))
    VTD = Column(types.String(6))
    VTDI = Column(types.String(1))
    RESERVE2 = Column(types.String(3))
    ZCTA5 = Column(types.String(5))
    SUBMCD = Column(types.String(5))
    SUBMCDCC = Column(types.String(2))
    SDELM = Column(types.String(5))
    SDSEC = Column(types.String(5))
    SDUNI = Column(types.String(5))

    # AREA CHARACTERISTICS
    AREALAND = Column(types.Integer)
    AREAWATR = Column(types.Integer)
    NAME = Column(types.String(90))
    FUNCSTAT = Column(types.String(1))
    GCUNI = Column(types.String(1))
    POP100 = Column(types.Integer)
    HU100 = Column(types.Integer)
    INTPTLAT = Column(types.Float)
    INTPTLON = Column(types.Float)
    LSADC = Column(types.String(2))
    PARTFLAG = Column(types.String(1))

    # SPECIAL AREA CODES
    RESERVE3 = Column(types.String(6))
    UGA = Column(types.String(5))
    STATENS = Column(types.String(8))
    COUNTYNS = Column(types.String(8))
    COUSUBNS = Column(types.String(8))
    PLACENS = Column(types.String(8))
    CONCITNS = Column(types.String(8))
    AIANHHNS = Column(types.String(8))
    AITSNS = Column(types.String(8))
    ANRCNS = Column(types.String(8))
    SUBMCDNS = Column(types.String(8))
    CD113 = Column(types.String(2))
    CD114 = Column(types.String(2))
    CD115 = Column(types.String(2))
    SLDU2 = Column(types.String(3))
    SLDU3 = Column(types.String(3))
    SLDU4 = Column(types.String(3))
    SLDL2 = Column(types.String(3))
    SLDL3 = Column(types.String(3))
    SLDL4 = Column(types.String(3))
    AIANHHSC = Column(types.String(2))
    CSASC = Column(types.String(2))
    CNECTASC = Column(types.String(2))
    MEMI = Column(types.String(1))
    NMEMI = Column(types.String(1))
    PUMA = Column(types.String(5))
    RESERVED = Column(types.String(18))
    GEOID = Column(types.String(7), ForeignKey('place.GEOID'))

    __table_args__ = (
        ForeignKeyConstraint(['STATEFP', 'COUNTYFP'],
                             ['county.STATEFP', 'county.COUNTYFP']),
        {}
        )


class F02(BaseGeoDataModel):
    __tablename__ = 'f02'
    FILEID = Column(types.String(6))
    STUSAB = Column(types.String(2))
    CHARITER = Column(types.String(3))
    CIFSN = Column(types.String(2))
    LOGRECNO = Column(types.Integer,
                      ForeignKey('ghr.LOGRECNO'),
                      primary_key=True)
    GHR = orm.relationship('GHR', back_populates='F02')

    P0020001 = Column(types.Integer)
    P0020002 = Column(types.Integer)
    P0020003 = Column(types.Integer)
    P0020004 = Column(types.Integer)
    P0020005 = Column(types.Integer)
    P0020006 = Column(types.Integer)
