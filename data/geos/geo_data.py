#!/usr/bin/env python
# -*- coding: utf-8 -*-
from alchy.model import ModelBase, make_declarative_base
from sqlalchemy import (orm, types, Column, ForeignKey, Index,
                        PrimaryKeyConstraint)

from intertwine.utils import AutoTablenameMixin

BaseGeoDataModel = make_declarative_base(Base=ModelBase)


class State(BaseGeoDataModel, AutoTablenameMixin):
    STATE = Column(types.String(2), primary_key=True)   # 48
    STUSAB = Column(types.String(2), unique=True)       # TX
    STATE_NAME = Column(types.String(60), unique=True)  # Texas
    STATENS = Column(types.String(8), unique=True)      # 01779801


class CBSA(BaseGeoDataModel, AutoTablenameMixin):
    CBSA_CODE = Column(types.String(5))  # 12420
    METRO_DIVISION_CODE = Column(types.String(5))
    CSA_CODE = Column(types.String(3))
    CBSA_NAME = Column(types.String(60))                # Austin-Round Rock, TX
    METRO_VS_MICRO = Column(types.String(30))
    METRO_DIVISION_NAME = Column(types.String(60))
    CSA_NAME = Column(types.String(60))
    COUNTY_NAME = Column(types.String(60))              # Travis County
    STATE_NAME = Column(types.String(60))               # Texas
    STATE_FIPS_CODE = Column(types.String(2))           # 48
    COUNTY_FIPS_CODE = Column(types.String(3))          # 453
    CENTRAL_VS_OUTLYING = Column(types.String(30))      # Central
    __table_args__ = (
        PrimaryKeyConstraint('STATE_FIPS_CODE', 'COUNTY_FIPS_CODE'),
        {}
        )


class County(BaseGeoDataModel, AutoTablenameMixin):
    STATE = Column(types.String(2))         # TX
    STATEFP = Column(types.String(2))       # 48
    COUNTYFP = Column(types.String(3))      # 453
    COUNTYNAME = Column(types.String(60))   # Travis County
    CLASSFP = Column(types.String(2))       # H1
    __table_args__ = (
        PrimaryKeyConstraint('STATEFP', 'COUNTYFP'),
        {}
        )


# class Place(BaseGeoDataModel, AutoTablenameMixin):
#     USPS
#     GEOID
#     ANSICODE
#     NAME
#     LSAD
#     FUNCSTAT
#     POP10
#     HU10
#     ALAND
#     AWATER
#     ALAND_SQMI
#     AWATER_SQMI
#     INTPTLAT
#     INTPTLONG


# class LSAD(BaseGeoDataModel, AutoTablenameMixin):
#     LSAD_CODE
#     LSAD_DESCRIPTION
#     GEO_ENTITY_TYPE


# class UR1_US_GHR_070(BaseGeoDataModel):
#     __tablename__ = 'ur1_us_ghr_070'


# class UR1_US_F02_070(BaseGeoDataModel):
#     __tablename__ = 'ur1_us_f02_070'
