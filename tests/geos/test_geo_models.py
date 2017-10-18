#!/usr/bin/env python
# -*- coding: utf-8 -*-
import pytest


@pytest.mark.unit
@pytest.mark.parametrize("parent_name, parent_abbrev, child_name", [
    ('Parent Test Republic', 'PTR', 'Child Test Geo'),
])
def test_geo_model_create(session, parent_name, parent_abbrev, child_name):
    '''Tests simple geo model interaction'''
    from intertwine.geos.models import Geo

    parent = Geo(name=parent_name, abbrev=parent_abbrev)
    child = Geo(name=child_name, path_parent=parent, parents=[parent])

    session.add(parent)
    session.add(child)
    session.commit()

    assert Geo[parent.derive_key()] is parent
    assert Geo[child.derive_key()] is child
    assert parent[child_name] is child

    parent_from_db = (
        session
        .query(Geo)
        .filter(Geo.human_id == parent.human_id)
        .first()
    )

    child_from_db = (
        session
        .query(Geo)
        .filter(Geo.human_id == child.human_id)
        .first()
    )

    assert parent_from_db is parent
    assert parent_from_db.name == parent_name
    assert parent_from_db.abbrev == parent_abbrev
    assert parent_from_db.uses_the is True
    assert parent_from_db.human_id == parent_abbrev.lower()
    assert parent_from_db.path_children.all()[0] is child_from_db
    assert parent_from_db.children.all()[0] is child_from_db

    assert child_from_db is child
    assert child_from_db.name == child_name
    assert child_from_db.abbrev is None
    assert child_from_db.uses_the is False
    assert child_from_db.human_id == Geo.PATH_DELIMITER.join(
                [child.path_parent.human_id,
                 child.name.lower().replace(' ', '_')])

    assert child_from_db.path_parent is parent_from_db
    assert child_from_db.parents.all()[0] is parent_from_db


@pytest.mark.unit
@pytest.mark.smoke
def test_geo_data_model(session):
    '''Tests simple geo data model interaction'''
    from intertwine.geos.models import Geo, GeoData

    total_pop, urban_pop = 1000, 800
    latitude, longitude = 30.0, -97.0
    land_area, water_area = 4321, 1234

    geo = Geo(name='Test Geo')
    GeoData(geo=geo,
            total_pop=total_pop,
            urban_pop=urban_pop,
            latitude=latitude,
            longitude=longitude,
            land_area=land_area,
            water_area=water_area)

    session.add(geo)
    session.commit()

    assert geo.data.total_pop == total_pop
    assert geo.data.urban_pop == urban_pop
    assert geo.data.latitude.value == latitude
    assert geo.data.longitude.value == longitude
    assert geo.data.land_area == land_area
    assert geo.data.water_area == water_area

    assert GeoData[geo.data.derive_key()] is geo.data

    geo_data_from_db = session.query(GeoData).filter(
                            GeoData.geo == geo).first()

    assert geo_data_from_db is geo.data
    assert geo_data_from_db.total_pop == geo.data.total_pop
    assert geo_data_from_db.urban_pop == geo.data.urban_pop
    assert geo_data_from_db.latitude == geo.data.latitude
    assert geo_data_from_db.longitude == geo.data.longitude
    assert geo_data_from_db.land_area == geo.data.land_area
    assert geo_data_from_db.water_area == geo.data.water_area


@pytest.mark.unit
@pytest.mark.smoke
def test_geo_level_model(session):
    '''Tests simple geo level model interaction'''
    from intertwine.geos.models import Geo, GeoLevel

    level = 'place'
    designation = 'city'
    geo = Geo(name='Test Geo Place')
    glvl = GeoLevel(geo=geo, level=level, designation=designation)

    session.add(geo)
    session.add(glvl)
    session.commit()

    assert geo.levels[level] is glvl
    assert glvl.geo is geo
    assert glvl.level == level
    assert glvl.designation == designation

    assert GeoLevel[glvl.derive_key()] is glvl

    glvl_from_db = session.query(GeoLevel).filter(
                    GeoLevel.geo == geo, GeoLevel.level == level).first()

    assert glvl_from_db is glvl
    assert glvl_from_db.geo is geo
    assert glvl_from_db.level == level
    assert glvl_from_db.designation == designation


@pytest.mark.unit
@pytest.mark.smoke
def test_geo_id_model(session):
    '''Tests simple geo id model interaction'''
    from intertwine.geos.models import Geo, GeoLevel, GeoID

    TEST_STANDARD = 'Test Standard'

    GeoID.STANDARDS.add(TEST_STANDARD)
    standard = TEST_STANDARD
    code = '12345'

    geo = Geo(name='Test Geo Place')
    glvl = GeoLevel(geo=geo, level='place', designation='city')
    gid = GeoID(level=glvl, standard=standard, code=code)

    session.add(geo)
    session.add(glvl)
    session.add(gid)
    session.commit()

    assert gid.level is glvl
    assert gid.standard == standard
    assert gid.code == code

    assert GeoID[gid.derive_key()] is gid
    assert GeoID[(standard, code)] is gid

    gid_from_db = session.query(GeoID).filter(
                    GeoID.standard == standard, GeoID.code == code).first()

    assert gid_from_db is gid
    assert gid_from_db.level is glvl
    assert gid_from_db.standard == standard
    assert gid_from_db.code == code


@pytest.mark.unit
@pytest.mark.smoke
def test_form_aggregate_geo(session):
    '''Tests geo creation that aggregates children data at a geo level'''
    from intertwine.geos.models import Geo, GeoData, GeoLevel
    from intertwine.utils.space import GeoLocation

    data_level = 'place'

    child_a_dict = {'total_pop': 100,
                    'urban_pop': 80,
                    'latitude': 42.0,
                    'longitude': -71.0,
                    'land_area': 321,
                    'water_area': 123}

    child_a_geo = Geo(name='Child Test Geo A')
    GeoData(geo=child_a_geo, **child_a_dict)
    GeoLevel(geo=child_a_geo, level='place', designation='village')

    child_b_dict = {'total_pop': 300,
                    'urban_pop': 240,
                    'latitude': 44.0,
                    'longitude': -73.0,
                    'land_area': 645,
                    'water_area': 21}

    child_b_geo = Geo(name='Child Test Geo B')
    GeoData(geo=child_b_geo, **child_b_dict)
    GeoLevel(geo=child_b_geo, level='place', designation='town')

    child_c_dict = {'total_pop': 1000,
                    'urban_pop': 800,
                    'latitude': 30.0,
                    'longitude': -97.0,
                    'land_area': 4321,
                    'water_area': 1234}

    child_c_geo = Geo(name='Child Test Geo C')
    GeoData(geo=child_c_geo, **child_c_dict)
    GeoLevel(geo=child_c_geo, level='subdivision2', designation='county')

    child_a_area = child_a_dict['land_area'] + child_a_dict['water_area']
    child_b_area = child_b_dict['land_area'] + child_b_dict['water_area']

    geo_location_a = GeoLocation(child_a_dict['latitude'],
                                 child_a_dict['longitude'])
    geo_location_b = GeoLocation(child_b_dict['latitude'],
                                 child_b_dict['longitude'])

    geo_location = GeoLocation.combine_locations(
        (geo_location_a, child_a_area),
        (geo_location_b, child_b_area))

    sum_fields = ('total_pop', 'urban_pop', 'land_area', 'water_area')

    aggregate_dict = {f: child_a_dict[f] + child_b_dict[f] for f in sum_fields}

    aggregate_dict['latitude'], aggregate_dict['longitude'] = (
        geo_location.coordinates)

    parent_geo = Geo(name='Parent Test Geo',
                     children=[child_a_geo, child_b_geo, child_c_geo],
                     child_data_level=data_level)  # aggregate places only

    session.add(parent_geo)
    session.add(child_a_geo)
    session.add(child_b_geo)
    session.add(child_c_geo)
    session.commit()

    parent_data = parent_geo.data
    assert parent_data is not None
    assert parent_data.total_pop == aggregate_dict['total_pop']
    assert parent_data.urban_pop == aggregate_dict['urban_pop']
    assert parent_data.latitude == aggregate_dict['latitude']
    assert parent_data.longitude == aggregate_dict['longitude']
    assert parent_data.land_area == aggregate_dict['land_area']
    assert parent_data.water_area == aggregate_dict['water_area']

    parent_geo_data_from_db = session.query(GeoData).filter(
        GeoData.geo == parent_geo).first()

    assert parent_geo_data_from_db is not None
    assert parent_geo_data_from_db is parent_geo.data
    assert parent_geo_data_from_db.total_pop == aggregate_dict['total_pop']
    assert parent_geo_data_from_db.urban_pop == aggregate_dict['urban_pop']
    assert parent_geo_data_from_db.latitude == aggregate_dict['latitude']
    assert parent_geo_data_from_db.longitude == aggregate_dict['longitude']
    assert parent_geo_data_from_db.land_area == aggregate_dict['land_area']
    assert parent_geo_data_from_db.water_area == aggregate_dict['water_area']


@pytest.mark.unit
@pytest.mark.smoke
def test_geo_aliases(session):
    '''Tests creation of geo aliases and promoting an alias'''
    from intertwine.geos.models import Geo, GeoData, GeoLevel

    geo_data_dict = {'total_pop': 100,
                     'urban_pop': 80,
                     'latitude': 42,
                     'longitude': -71,
                     'land_area': 321,
                     'water_area': 123}

    level = 'place'
    geo = Geo(name='Test Geo')
    gdata = GeoData(geo=geo, **geo_data_dict)
    glvl = GeoLevel(geo=geo, level=level, designation='city')

    parent_geo = Geo(name='Test Parent Geo', abbrev='TPG')
    geo.path_parent = parent_geo
    geo.parents = [parent_geo]

    sibling_geo = Geo(name='Test Sibling Geo')
    sibling_geo.path_parent = parent_geo
    sibling_geo.parents = [parent_geo]

    child_geo = Geo(name='Test Child Geo')
    child_geo.path_parent = geo
    child_geo.parents = [geo]

    geo_alias_1 = Geo(name='Test Geo Alias 1', alias_targets=[geo],
                      path_parent=geo)
    geo_alias_2 = Geo(name='Test Geo Alias 2', alias_targets=[geo],
                      path_parent=parent_geo)
    geo_alias_3 = Geo(name='Test Geo Alias 3', alias_targets=[geo],
                      path_parent=parent_geo)

    session.add(geo)
    session.commit()

    assert geo.data is gdata
    assert geo.levels[level] is glvl
    assert parent_geo in geo.parents
    assert geo in child_geo.parents

    assert geo.path_parent is parent_geo
    assert child_geo.path_parent is geo
    assert geo_alias_1.path_parent is geo
    assert geo_alias_2.path_parent is parent_geo
    assert geo_alias_3.path_parent is parent_geo

    assert geo_alias_1.alias_targets[0] is geo
    assert geo_alias_2.alias_targets[0] is geo
    assert geo_alias_3.alias_targets[0] is geo

    aliases = geo.aliases.all()
    assert geo_alias_1 in aliases
    assert geo_alias_2 in aliases
    assert geo_alias_3 in aliases

    geo_from_db = session.query(Geo).filter_by(
        human_id=geo.human_id).first()

    aliases = geo_from_db.aliases.all()
    assert geo_alias_1 in aliases
    assert geo_alias_2 in aliases
    assert geo_alias_3 in aliases

    geo_alias_1.promote_to_alias_target()
    assert not geo_alias_1.alias_targets
    assert geo_alias_2.alias_targets[0] is geo_alias_1
    assert geo_alias_3.alias_targets[0] is geo_alias_1
    assert geo.alias_targets[0] is geo_alias_1

    assert geo_alias_1.data is gdata
    assert geo_alias_1.levels[level] is glvl
    assert parent_geo in geo_alias_1.parents
    assert geo_alias_1 in child_geo.parents

    # paths are unchanged by design
    assert geo.path_parent is parent_geo
    assert child_geo.path_parent is geo
    assert geo_alias_1.path_parent is geo
    assert geo_alias_2.path_parent is parent_geo
    assert geo_alias_3.path_parent is parent_geo
