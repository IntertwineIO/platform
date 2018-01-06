#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
Builders for instantiating test data
'''

from __future__ import (absolute_import, division, print_function,
                        unicode_literals)
import datetime
import string
import sys
import uuid
from collections import OrderedDict
from functools import partial

import pendulum
from faker import Faker

from intertwine import IntertwineModel
from intertwine.utils.space import Area, Coordinate, GeoLocation
from intertwine.utils.tools import derive_args, get_value

SQLALCHEMY_MODEL_BASE = IntertwineModel


class Builder(object):

    MODEL_BUILDER_TAG = 'Builder'
    BUILDER_FIELD_TAG = 'builder'
    BUILD_FIELD_TAG = 'build'
    DEFAULT_FIELD_TAG = 'default'

    DEFAULT_MAX_STRING_LENGTH = 255
    DEFAULT_ALPHABET = string.digits + string.letters + string.punctuation
    DEFAULT_TEXT = '''
    Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do
    eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim
    ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut
    aliquip ex ea commodo consequat. Duis aute irure dolor in
    reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla
    pariatur. Excepteur sint occaecat cupidatat non proident, sunt in
    culpa qui officia deserunt mollit anim id est laborum.
    '''
    DEFAULT_WORDS = DEFAULT_TEXT.split()
    NOW = pendulum.now()
    SEED = int(NOW.strftime('%Y%m%d'))  # Daily seed: YYYYMMDD

    fake = Faker()
    fake.seed(SEED)
    random = fake.random  # All random usages should use this

    _builder_count = 0

    def build(self, _query_on_miss=False, _stack=None, **kwds):

        self.instance_id = self._instance_count
        self._instance_count += 1

        unique_id = self.unique_id
        stack = _stack if _stack else []
        stack.append(unique_id)

        self.model_init_kwds = kwds.copy()
        arg_names = derive_args(self.model.__init__, include_self=False,
                                include_private=False,
                                include_optional=self.optional)

        for arg in arg_names:
            if arg in kwds:
                continue
            try:
                field_builder = self.get_field_builder(field_name=arg, **kwds)
            except AttributeError:
                # Skip any argument without an instrumented attribute
                continue
            else:
                self.model_init_kwds[arg] = field_builder(_stack=stack)

        stack.pop()
        inst, created = self.model.get_or_create(
            _query_on_miss=_query_on_miss, _save=False, **self.model_init_kwds)
        return inst

    @classmethod
    def get_model_map(cls):
        '''Build model map from configured SQLAlchemy declarative base'''
        try:
            return cls._model_map
        except AttributeError:
            base = SQLALCHEMY_MODEL_BASE
            cls._model_map = {model.__name__: model
                              for model in base._decl_class_registry.values()
                              if hasattr(model, '__table__')}
            return cls._model_map

    @classmethod
    def get_model(cls, name=None):
        '''Get specified model or builder-implied model from model map'''
        if not name:
            name = cls.__name__.split(cls.MODEL_BUILDER_TAG)[0]
        try:
            return cls.get_model_map()[name]
        except KeyError:
            if not name and cls is Builder:
                raise TypeError('Base {cls} has no model'.format(cls=cls))
            raise TypeError('No model found for {name}'.format(name=name))

    @classmethod
    def get_builder(cls, name):
        '''Get specified builder by name from subclasses'''
        try:
            builder_map = Builder._builder_map
        except AttributeError:
            builder_map = Builder._builder_map = {
                b.__name__: b for b in Builder.__subclasses__()}
        return builder_map[name]

    @classmethod
    def get_model_builder(cls, model):
        '''Get builder class for given model'''
        model_name = model.__name__
        model_builder_name = ''.join((model_name, cls.MODEL_BUILDER_TAG))
        try:
            return cls.get_builder(model_builder_name)
        except KeyError:
            return cls

    def get_field_builder(self, field_name, **kwds):
        '''Get specified field builder by field name or default'''
        build_field_name = '_'.join((self.BUILD_FIELD_TAG, field_name))
        field_builder = getattr(self, build_field_name, None)
        if not field_builder:
            field_builder = self.get_default_field_builder(field_name, **kwds)
        return field_builder

    def get_default_field_builder(self, field_name, **kwds):
        '''Get default field/model builder from specified field type'''
        model = self.model
        try:
            related_model = model.related_model(field_name)
            related_builder = self.__class__(model=related_model, derive=True)
            related_builder_field = '_'.join((field_name,
                                              self.BUILDER_FIELD_TAG))
            setattr(self, related_builder_field, related_builder)
            return related_builder.build

        except AttributeError:
            field = model.instrumented_attribute(field_name)
            field_type = field.expression.type
            field_type_name = field_type.__class__.__name__
            build_default_type_name = '_'.join((self.DEFAULT_FIELD_TAG,
                                                field_type_name.lower()))
            build_default_type = getattr(self, build_default_type_name)
            return partial(build_default_type, field_type=field_type, **kwds)

    def default_boolean(self, field_type, **kwds):
        '''Default random boolean value'''
        return bool(self.random.randint(0, 1))

    def default_datetime(self, field_type, **kwds):
        '''Default random datetime value'''
        now = datetime.datetime.utcnow()
        start = datetime.datetime(1900, 1, 1)
        naive_dt = self.fake.date_time_between_dates(datetime_start=start,
                                                     datetime_end=now)
        utc_tz = pendulum.timezone('UTC')
        utc_dt = utc_tz.convert(naive_dt)
        local_tz_name = self.fake.timezone()
        local_tz = pendulum.timezone(local_tz_name)
        local_dt = local_tz.convert(utc_dt)
        return local_dt

    def default_float(self, field_type, **kwds):
        '''Default random float value'''
        maxsize = sys.maxsize
        max_divisor_power = len(str(maxsize))
        divisor_power = self.random.randint(0, max_divisor_power)
        divisor = 10 ** divisor_power
        return self.random.randint(-maxsize - 1, maxsize) / divisor

    def default_integer(self, field_type, **kwds):
        '''Default random integer value'''
        return self.random.randint(-sys.maxsize - 1, sys.maxsize)

    def default_string(self, field_type, **kwds):
        '''Default random string value'''
        field_length = field_type.length
        num_chars = (self.random.randint(1, field_length) if field_length
                     else self.DEFAULT_MAX_STRING_LENGTH)
        if num_chars < 5:
            characters = []
            for i in range(num_chars):
                characters.append(self.random.choice(string.lowercase))
            return ''.join(characters)

        default_text = self.default_text(field_type, max_length=num_chars)
        return default_text[:field_length]

    def default_text(self, field_type, max_length=None, **kwds):
        '''Default random text value'''
        num_words = self.random.randint(1, len(self.DEFAULT_WORDS))
        words = []
        length = -1  # First word has no space
        for i in range(num_words):
            random_word = self.random.choice(self.DEFAULT_WORDS)
            length += len(random_word) + 1
            words.append(random_word)
            if max_length and length >= max_length - 1:
                break
        rejoined = ' '.join(words)
        capitalized = '. '.join(s.capitalize() for s in rejoined.split('. '))
        return capitalized

    @property
    def unique_id(self):
        return '.'.join((self.__class__.__name__,
                         str(self.builder_id), str(self.instance_id)))

    def __new__(cls, model=None, derive=True, **kwds):

        if derive and model:
            model_builder_class = cls.get_model_builder(model)
            if model_builder_class is not cls:
                inst = model_builder_class.__new__(
                    model_builder_class, model=model, derive=False, **kwds)
                inst.__init__(model=model, derive=False, **kwds)
                return inst

        return super(Builder, cls).__new__(cls)

    def __init__(self, model=None, derive=True, optional=False, **kwds):

        super(Builder, self).__init__()
        cls = self.__class__
        if not model:
            model = self.get_model()
        self.model = model
        self.optional = optional
        self.builder_id = cls._builder_count
        cls._builder_count += 1
        self._instance_count = 0


class ProblemBuilder(Builder):

    NAMES = {
        'You Know Who',
        'The Dark Arts',
        'Orphaned',
        'Identity Crisis',
        'Daddy Issues',
        'Mommy Issues',
        'A Cursed Broomstick',
        'Bludgeoned by Bludgers',
        'Pummeled by Whomping Willow',
        'Trolls in the Bathroom',
        'Paralyzed by a Basilisk',
        'Contaminated Polyjuice Potion',
        'Singed by Dragonfire',
        'A Broken Wand',
        'A Lost Pet',
        'Flying Car Taken for Joy Ride',
        'Afflicted by Full Body-Bind Curse',
        'Vomiting Slugs',
        'Memory Loss',
    }

    def build_name(self, **kwds):
        include = self.include or self.NAMES
        exclude = self.exclude
        names = include - exclude
        return self.random.choice(tuple(names))

    def __init__(self, model=None, include=None, exclude=None, **kwds):
        super(ProblemBuilder, self).__init__(**kwds)
        self.include = include or set()
        self.exclude = exclude or set()


class ProblemConnectionBuilder(Builder):
    '''
    ProblemConnectionBuilder

    If the net includes contains 2 or more names, both problem names are
    selected from these names. If the net includes contains 1 name, the
    name is randomly assigned to problem A or problem B, with the other
    name selected randomly from the default list of problem names.
    for
    I/O:
    include=None: set of problem names to include
    exclude=None: set of problem names to exclude
    '''

    def build(self, **kwds):
        net_include = self.include - self.exclude
        self.problem_position = (
            self.random.choice((self.model.PROBLEM_A, self.model.PROBLEM_B))
            if len(net_include) == 1 else None)

        return super(ProblemConnectionBuilder, self).build(**kwds)

    def build_axis(self, **kwds):
        return self.random.choice(tuple(self.model.AXES))

    def build_problem_a(self, _stack=None, **kwds):
        PROBLEM_A, PROBLEM_B = self.model.PROBLEM_A, self.model.PROBLEM_B
        additional_exclude = (
            {self.model_init_kwds[PROBLEM_B].name}
            if PROBLEM_B in self.model_init_kwds else set())

        exclude = self.exclude | additional_exclude
        original_net_include = self.include - self.exclude
        net_include = original_net_include - additional_exclude
        include = (net_include
                   if ((net_include and self.problem_position == PROBLEM_A) or
                       len(original_net_include) > 1)
                   else None)

        self.problem_a_builder = ProblemBuilder(include=include,
                                                exclude=exclude)
        return self.problem_a_builder.build(_stack=_stack)

    def build_problem_b(self, _stack=None, **kwds):
        PROBLEM_A, PROBLEM_B = self.model.PROBLEM_A, self.model.PROBLEM_B
        additional_exclude = (
            {self.model_init_kwds[PROBLEM_A].name}
            if PROBLEM_A in self.model_init_kwds else set())

        exclude = self.exclude | additional_exclude
        original_net_include = self.include - self.exclude
        net_include = original_net_include - additional_exclude
        include = (net_include
                   if ((net_include and self.problem_position == PROBLEM_B) or
                       len(original_net_include) > 1)
                   else None)

        self.problem_b_builder = ProblemBuilder(include=include,
                                                exclude=exclude)
        return self.problem_b_builder.build(_stack=_stack)

    def __init__(self, model=None, include=None, exclude=None, **kwds):
        super(ProblemConnectionBuilder, self).__init__(**kwds)
        self.include = include or set()
        self.exclude = exclude or set()


class ProblemConnectionRatingBuilder(Builder):

    def build_rating(self, **kwds):
        model = self.model
        return self.random.randint(model.MIN_RATING, model.MAX_RATING)

    def build_weight(self, **kwds):
        model = self.model
        return self.random.randint(model.MIN_WEIGHT, model.MAX_WEIGHT)

    def build_connection(self, _stack=None, **kwds):
        if 'problem' in self.model_init_kwds:
            problem = self.model_init_kwds['problem']
            include = {problem.name}
        else:
            include = None

        self.connection_builder = ProblemConnectionBuilder(include=include)
        return self.connection_builder.build(_stack=_stack)

    def build_problem(self, _stack=None, **kwds):
        if 'connection' in self.model_init_kwds:
            connection = self.model_init_kwds['connection']
            include = {connection.problem_a.name, connection.problem_b.name}
        else:
            include = None

        self.problem_builder = ProblemBuilder(include=include)
        return self.problem_builder.build(_stack=_stack)

    def build_org(self, **kwds):
        self.org_builder = OrgBuilder()
        return self.org_builder.build()


class AggregateProblemConnectionRatingBuilder(Builder):

    MIN_RATING = -1
    MAX_RATING = 4
    MIN_WEIGHT = 0
    MAX_WEIGHT = 10 ** 10

    def build_rating(self, **kwds):
        model = self.model
        return self.random.randint(
            model.MIN_RATING * 100, model.MAX_RATING * 100) / 100

    def build_weight(self, **kwds):
        model = self.model
        return self.random.randint(model.MIN_WEIGHT, sys.maxsize)

    def build_aggregation(self, **kwds):
        model = self.model
        return self.random.choice(tuple(model.AGGREGATIONS))

    def build_connection(self, _stack=None, **kwds):
        if 'community' in self.model_init_kwds:
            community = self.model_init_kwds['community']
            problem = community.problem
            include = {problem.name}
        else:
            include = None

        self.connection_builder = ProblemConnectionBuilder(include=include)
        return self.connection_builder.build(_stack=_stack)

    def build_community(self, _stack=None, **kwds):
        if 'connection' in self.model_init_kwds:
            connection = self.model_init_kwds['connection']
            problem_include = {connection.problem_a.name,
                               connection.problem_b.name}
        else:
            problem_include = None

        self.community_builder = CommunityBuilder(
            problem_include=problem_include)
        return self.community_builder.build(_stack=_stack)

    def build_org(self, **kwds):
        self.org_builder = OrgBuilder()
        return self.org_builder.build()


class ImageBuilder(Builder):

    URLS = {
        'https://static0.srcdn.com/wp-content/uploads/2017/05/Voldemort.jpg',
        'https://qph.ec.quoracdn.net/main-qimg-'
        '266d3136d495cda1cf3946529738e901-c',
        'https://www.polyvore.com/cgi/img-thing?.out=jpg&size=l&tid=12885161'
    }

    def build_url(self, **kwds):
        return self.random.choice(tuple(self.URLS))


class OrgBuilder(Builder):

    NAMES = {
        'Hogwarts School of Witchcraft and Wizardry',
        'Durmstrang Institute',
        'Beauxbatons Academy of Magic',
        'Ministry of Magic',
        'Department of Magical Law Enforcement',
        'Department of Magical Accidents and Catastrophes',
        'Department for the Regulation and Control of Magical Creatures',
        'Department of International Magical Cooperation',
        'Department of Magical Transportation',
        'Department of Magical Games and Sports',
        'Department of Mysteries',
    }

    def build(self, **kwds):
        return self.build_name(**kwds)

    def build_name(self, **kwds):
        include = self.include or self.NAMES
        exclude = self.exclude
        names = include - exclude
        return self.random.choice(tuple(names))

    def __init__(self, model=None, include=None, exclude=None, **kwds):
        # No super call because there's no org model (yet)
        self.include = include or set()
        self.exclude = exclude or set()


class GeoBuilder(Builder):

    PROBABILITY_TAG = 'probability'

    ABBREV_TAG = 'abbrev'
    QUALIFIER_TAG = 'qualifier'
    PATH_PARENT_TAG = 'path_parent'
    ALIAS_TARGETS_TAG = 'alias_targets'
    ALIASES_TAG = 'aliases'
    PARENTS_TAG = 'parents'
    CHILDREN_TAG = 'children'

    DEFAULT_PROBABILITIES = OrderedDict((
        (ABBREV_TAG, 0.2),
        (QUALIFIER_TAG, 0.2),
        (PATH_PARENT_TAG, 0),
        (ALIAS_TARGETS_TAG, 1),  # all aliases must have a target
        (ALIASES_TAG, 0),
        (PARENTS_TAG, 0),
        (CHILDREN_TAG, 0),
    ))

    NAMES = {
        'Diagon Alley',
        'Forbidden Forest',
        'Black Lake',
        'Azkaban',
        'Little Whinging',
        'Surrey',
        'London',
        'Greater London',
        'England',
        'Somewhere in the Pyrenees',
        'Andorra',
        'France',
        'Far North of Europe',
        'Europe',
        'Middle of the North Sea',
        'North Sea',
    }

    QUALIFIERS = {
        'in our imagination',
        'of Harry Potter fame',
        'we know and love',
        'as we read somewhere',
        '...you know the one',
    }

    def build_name(self, **kwds):
        include = self.include or self.NAMES
        related = self._get_related_geo_names()
        exclude = self.exclude | related
        names = include - exclude
        return self.random.choice(tuple(names))

    def _get_related_geo_names(self):
        path_parent_name = ({self.model_init_kwds[self.PATH_PARENT_TAG].name}
                            if self.model_init_kwds.get(self.PATH_PARENT_TAG)
                            else set())
        parents_names = (
            {g.name for g in self.model_init_kwds[self.PARENTS_TAG]}
            if self.model_init_kwds.get(self.PARENTS_TAG) else set())
        children_names = (
            {g.name for g in self.model_init_kwds[self.CHILDREN_TAG]}
            if self.model_init_kwds.get(self.CHILDREN_TAG) else set())

        return path_parent_name | parents_names | children_names

    def build_abbrev(self, **kwds):
        if self.random.uniform(0, 1) > self.abbrev_probability:
            return
        name = self.model_init_kwds['name']
        name_words = name.split()
        if len(name_words) > 1:
            return ''.join((w[0] for w in name_words)).upper()
        return name[:3].upper()

    def build_qualifier(self, **kwds):
        if self.only_new:
            # Ensure the geo is new via a unique qualifier
            return 'in dimension {}'.format(uuid.uuid4())
        if self.random.uniform(0, 1) > self.qualifier_probability:
            return
        return self.random.choice(tuple(self.QUALIFIERS))

    def _build_related_geo(self, relation, is_alias=False, _stack=None,
                           **build_kwds):
        probability_name = '_'.join((relation, self.PROBABILITY_TAG))
        probability = getattr(self, probability_name)
        if self.random.uniform(0, 1) > probability:
            return

        name = self.model_init_kwds['name']
        if relation == self.ALIASES_TAG:
            include = {name}
            exclude = None
        else:
            include = None
            exclude = self.exclude | {self.model_init_kwds['name']}
            if not (self.NAMES - exclude):
                return

        geo_builder = GeoBuilder(include=include, exclude=exclude,
                                 is_alias=is_alias, optional=self.optional)
        builder_field_name = '_'.join((relation, self.BUILDER_FIELD_TAG))
        setattr(self, builder_field_name, geo_builder)
        geo = geo_builder.build(_stack=_stack, **build_kwds)

        if not is_alias:
            assert not geo.alias_targets, ('{relation} may not be an alias'
                                           .format(relation=relation))
        return geo

    def build_path_parent(self, _stack=None, **kwds):
        if self.is_alias:
            return
        return self._build_related_geo(self.PATH_PARENT_TAG, is_alias=False,
                                       _stack=_stack)

    def build_alias_targets(self, _stack=None, **kwds):
        if not self.is_alias:
            return
        geo = self._build_related_geo(self.ALIAS_TARGETS_TAG, is_alias=False,
                                      _stack=_stack)
        return [geo] if geo else None

    def build_aliases(self, _stack=None, **kwds):
        if self.is_alias:
            return
        # Create alias without targets since its target is being built
        geo = self._build_related_geo(self.ALIASES_TAG, is_alias=True,
                                      _stack=_stack, alias_targets=None)
        return [geo] if geo else None

    def build_parents(self, _stack=None, **kwds):
        if self.is_alias:
            return
        geo = self._build_related_geo(self.PARENTS_TAG, is_alias=False,
                                      _stack=_stack)
        return [geo] if geo else None

    def build_children(self, _stack=None, **kwds):
        if self.is_alias:
            return
        geo = self._build_related_geo(self.CHILDREN_TAG, is_alias=False,
                                      _stack=_stack)
        return [geo] if geo else None

    def build_data(self, _stack=None, **kwds):
        return

    def build_levels(self, _stack=None, **kwds):
        return

    def __init__(self, model=None, include=None, exclude=None, only_new=False,
                 is_alias=False, abbrev_probability=None,
                 qualifier_probability=None, path_parent_probability=None,
                 alias_targets_probability=None, aliases_probability=None,
                 parents_probability=None, children_probability=None, **kwds):
        super(GeoBuilder, self).__init__(**kwds)
        self.include = include or set()
        self.exclude = exclude or set()
        self.only_new = only_new or is_alias
        self.is_alias = is_alias

        for field_name, default in self.DEFAULT_PROBABILITIES.items():
            probability_name = '_'.join((field_name, self.PROBABILITY_TAG))
            value = get_value(locals()[probability_name], default)
            setattr(self, probability_name, value)


class GeoDataBuilder(Builder):

    MIN_TOTAL_POP = 10
    MAX_TOTAL_POP = 10 ** 7
    MIN_URBAN_POP = 0
    MAX_URBAN_POP = 10 ** 7
    MIN_LATITUDE = GeoLocation.MIN_LATITUDE
    MAX_LATITUDE = GeoLocation.MAX_LATITUDE
    MIN_LONGITUDE = GeoLocation.MIN_LONGITUDE
    MAX_LONGITUDE = GeoLocation.MAX_LONGITUDE
    MIN_LAND_AREA = 10
    MAX_LAND_AREA = 10 ** 6
    MIN_WATER_AREA = 0
    MAX_WATER_AREA = 10 ** 3

    COORDINATE_PRECISION = Coordinate.DEFAULT_PRECISION
    AREA_PRECISION = Area.DEFAULT_PRECISION

    def build_geo(self, _stack=None, **kwds):
        self.geo_builder = GeoBuilder(only_new=True, is_alias=False,
                                      optional=self.optional)
        return self.geo_builder.build(_stack=_stack)

    def build_total_pop(self, **kwds):
        if 'urban_pop' in self.model_init_kwds:
            urban_pop = self.model_init_kwds['urban_pop']
            minimum, maximum = urban_pop, self.MAX_TOTAL_POP
        else:
            minimum, maximum = self.MIN_TOTAL_POP, self.MAX_TOTAL_POP
        return self.random.randint(minimum, maximum)

    def build_urban_pop(self, **kwds):
        if 'total_pop' in self.model_init_kwds:
            total_pop = self.model_init_kwds['total_pop']
            minimum, maximum = self.MIN_URBAN_POP, total_pop
        else:
            minimum, maximum = self.MIN_URBAN_POP, self.MAX_URBAN_POP
        return self.random.randint(minimum, maximum)

    def build_latitude(self, **kwds):
        minimum, maximum = self.MIN_LATITUDE, self.MAX_LATITUDE
        precision = self.COORDINATE_PRECISION
        factor = 10 ** precision
        return self.random.randint(minimum * factor, maximum * factor) / factor

    def build_longitude(self, **kwds):
        minimum, maximum = self.MIN_LONGITUDE, self.MAX_LONGITUDE
        precision = self.COORDINATE_PRECISION
        factor = 10 ** precision
        return self.random.randint(minimum * factor, maximum * factor) / factor

    def build_land_area(self, **kwds):
        minimum, maximum = self.MIN_LAND_AREA, self.MAX_LAND_AREA
        precision = self.AREA_PRECISION
        factor = 10 ** precision
        return self.random.randint(minimum * factor, maximum * factor) / factor

    def build_water_area(self, **kwds):
        minimum, maximum = self.MIN_WATER_AREA, self.MAX_WATER_AREA
        precision = self.AREA_PRECISION
        factor = 10 ** precision
        return self.random.randint(minimum * factor, maximum * factor) / factor


class GeoLevelBuilder(Builder):

    def build_geo(self, _stack=None, **kwds):
        self.geo_builder = GeoBuilder(only_new=True, is_alias=False,
                                      optional=self.optional)
        return self.geo_builder.build(_stack=_stack)

    def build_level(self, **kwds):
        return self.random.choice(self.model.UP.keys())


class GeoIDBuilder(Builder):

    def build_standard(self, **kwds):
        return self.random.choice(tuple(self.model.STANDARDS))


class CommunityBuilder(Builder):

    MAX_NUM_FOLLOWERS = 10 ** 9

    def build_problem(self, _stack=None, **kwds):
        self.problem_builder = ProblemBuilder(
            include=self.problem_include, exclude=self.problem_exclude)
        return self.problem_builder.build(_stack=_stack)

    def build_org(self, **kwds):
        self.org_builder = OrgBuilder()
        return self.org_builder.build()

    def build_num_followers(self, **kwds):
        return self.random.randint(0, self.MAX_NUM_FOLLOWERS)

    def __init__(self, model=None, problem_include=None, problem_exclude=None,
                 **kwds):
        super(CommunityBuilder, self).__init__(**kwds)
        self.problem_include = problem_include or set()
        self.problem_exclude = problem_exclude or set()


class ContentBuilder(Builder):

    MAX_AUTHORS = 5

    PUBLICATION_NAMES = {
        'The Daily Prophet',
        'The Evening Prophet',
        'The Sunday Prophet',
        'The Quibbler',
        'Wizarding Wireless Network',
        'Potterwatch',
        'Mystic, International Journal of Magic',
        'Journal of Charms & Wards',
        'Defense Against the Dark Arts',
        'Curses & Counterspells',
        'New Wizard & Witch',
        'Wizardry & Witchcraft',
        'The Magical Review',
    }

    def build_author_names(self, **kwds):
        num_authors = self.random.randint(1, self.MAX_AUTHORS)
        authors = (self.fake.name() for _ in xrange(num_authors))
        author_names = '; '.join(authors)
        return author_names

    def build_publication(self, **kwds):
        return self.random.choice(tuple(self.PUBLICATION_NAMES))
