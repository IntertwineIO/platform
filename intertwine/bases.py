# -*- coding: utf-8 -*-
from collections import OrderedDict
from itertools import chain, groupby
from urllib.parse import parse_qsl, urlencode, urlparse

from alchy.model import ModelBase

from intertwine.initiation import InitiationMixin, InitiationMetaMixin
from intertwine.trackable import Trackable
from intertwine.trackable.utils import build_table_model_map
from intertwine.utils.duck_typing import isnamedtuple
from intertwine.utils.enums import UriType
from intertwine.utils.jsonable import Jsonable, JsonProperty
from intertwine.utils.mixins import AutoTableMixin
from intertwine.utils.tools import get_value


class BaseIntertwineMeta(InitiationMetaMixin, Trackable):
    pass


class BaseIntertwineModel(InitiationMixin, Jsonable, AutoTableMixin,
                          ModelBase):

    ID_FIELDS = Jsonable.ID_FIELDS | {'uri'}
    URI_TYPE = UriType.NATURAL
    URI_QUERY_PARAMETERS = {'org'}

    @property
    def model_class(self):
        return self.__class__

    jsonified_model_class = JsonProperty(name='model_class', hide=True)

    def json_key(self, key_type=None, raw=False, tight=True, **kwds):
        """JSON key supports URI (default), NATURAL, and PRIMARY"""
        if key_type:
            if key_type is self.JsonKeyType.URI:
                uri = self.uri
                if uri:
                    return uri
                raise NotImplementedError('{cls} instance missing URI'
                                          .format(cls=self.model_class))
            if key_type is self.JsonKeyType.NATURAL:
                return self.trepr(raw=raw, tight=tight)
            return super(BaseIntertwineModel, self).json_key(
                key_type=key_type, raw=raw, tight=tight, **kwds)

        for default_key_type in reversed(self.JsonKeyType):
            try:
                return self.json_key(default_key_type, raw, tight, **kwds)
            except (AttributeError, TypeError, NotImplementedError):
                pass

        raise KeyError('Unable to create JSON key')

    @property
    def uri(self):
        """Default URI property based on natural or primary key"""
        cls = self.model_class
        try:
            if cls.URI_TYPE is UriType.NATURAL:
                key = self.derive_key()
                return cls.form_uri(key)
            if cls.URI_TYPE is UriType.PRIMARY:
                return cls.form_uri(self.pk)
            raise ValueError('Unknown UriType: {}'.format(cls.URI_TYPE))
        except AttributeError:
            return None

    jsonified_uri = JsonProperty(name='uri', before='json_key', hide=True)

    @classmethod
    def form_uri(cls, key, sub_only=False):
        """
        Form URI from given key

        key: object key namedtuple, typically a Trackable or primary key
        sub_only=False: If True, start with sub-blueprint, not blueprint
        return: URI composed from the key components
        """
        if not isnamedtuple(key):
            key = cls.create_key(*key)

        query_fields = cls.URI_QUERY_PARAMETERS
        path, query = cls.deconstruct_key(key, query_fields=query_fields)
        key_path = (str(component) if component is not None else ''
                    for component in path.values())

        base_path = [''] if sub_only else ['', cls.blueprint_name()]  # '' to prefix '/'
        sub_blueprint = cls.sub_blueprint_name()
        if sub_blueprint:
            base_path.append(sub_blueprint)

        path_string = '/'.join(chain(base_path, key_path))
        query_string = urlencode(query)
        uri = '?'.join((path_string, query_string)) if query_string else path_string
        return uri

    @classmethod
    def instantiate_uri(cls, uri):
        url_components = urlparse(uri)
        path_string, query_string = url_components.path, url_components.query
        path_components = path_string.strip('/').split('/')
        blueprint_sub_map = cls.blueprint_sub_map()

        if path_components[0] in blueprint_sub_map:
            blueprint_name = path_components[0]
            if path_components[1] in blueprint_sub_map[blueprint_name]:
                sub_blueprint_name = path_components[1]
                path = path_components[2:]
            else:
                sub_blueprint_name = None
                path = path_components[1:]
            model = cls.blueprint_model(blueprint_name, sub_blueprint_name)
        else:
            path = path_components
            model = cls

        if model.URI_TYPE is UriType.NATURAL:
            query = OrderedDict(parse_qsl(query_string))
            query_fields = getattr(cls, 'URI_QUERY_PARAMETERS', None)
            return model.reconstruct(path, query, query_fields=query_fields)

        if model.URI_TYPE is UriType.PRIMARY:
            pk_fields = model.PrimaryKeyTuple()._fields
            pk_values = (int(v) for v in path)
            pk_kwargs = dict(zip(pk_fields, pk_values))
            return model.query.filter_by(**pk_kwargs).one()

    @classmethod
    def validate_against_sub_blueprints(cls, include=True, **kwds):
        blueprint_name = cls.blueprint_name()
        blueprint_sub_map = cls.blueprint_sub_map()
        sub_blueprints = blueprint_sub_map[blueprint_name]
        if include:
            for field, value in kwds.items():
                if value not in sub_blueprints:
                    raise ValueError('{field} must be one of: {subs}'
                                     .format(field=field, subs=sub_blueprints))
        else:
            for field, value in kwds.items():
                if value in sub_blueprints:
                    raise ValueError('{field} may not be any of: {subs}'
                                     .format(field=field, subs=sub_blueprints))

    @classmethod
    def blueprint_name(cls):
        """Get blueprint name from containing module"""
        try:
            return cls._blueprint_name
        except AttributeError:
            if cls.__name__ in {'BaseIntertwineModel', 'Base'}:
                raise
            cls._blueprint_name = cls.__module__.split('.')[-2]
            return cls._blueprint_name

    @classmethod
    def sub_blueprint_name(cls):
        """Get sub-blueprint name from class constant"""
        try:
            return cls.SUB_BLUEPRINT
        except AttributeError:
            return None

    @classmethod
    def blueprint_subs(cls, blueprint_name):
        """Retrieve sub-blueprint names given blueprint name"""
        blueprint_sub_map = cls.blueprint_sub_map()
        return blueprint_sub_map[blueprint_name]

    @classmethod
    def blueprint_sub_map(cls):
        """Sorted map of blueprint names to sub-blueprint name sets"""
        try:
            return cls._blueprint_sub_map
        except AttributeError:
            blueprint_model_map = cls.blueprint_model_map()
            cls._blueprint_sub_map = OrderedDict(
                (key, {g[1] for g in group if g[1]})
                for key, group in groupby(
                    blueprint_model_map.keys(), lambda x: x[0]))
            return cls._blueprint_sub_map

    @classmethod
    def blueprint_model(cls, blueprint_name, sub_blueprint_name=None):
        """Retrieve model given blueprint/sub-blueprint names"""
        blueprint_key = (blueprint_name, sub_blueprint_name)
        blueprint_model_map = cls.blueprint_model_map()
        return blueprint_model_map[blueprint_key]

    @classmethod
    def blueprint_model_map(cls):
        """Sorted map of (blueprint, sub-blueprint) tuples to models"""
        try:
            return cls._blueprint_model_map
        except AttributeError:
            models = sorted(
                Trackable._classes.values(),
                key=lambda x: (x.blueprint_name(),
                               get_value(x.sub_blueprint_name(), '')))
            cls._blueprint_model_map = OrderedDict(
                ((m.blueprint_name(), m.sub_blueprint_name()), m)
                for m in models)
            return cls._blueprint_model_map

    @classmethod
    def initialize_table_model_map(cls):
        """Initialize table model map; invoke after loading all models"""
        cls._table_model_map = build_table_model_map(cls)
