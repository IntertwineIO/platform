# -*- coding: utf-8 -*-
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)
import sys
from collections import OrderedDict
from itertools import chain, groupby

from alchy.model import ModelBase

from intertwine.initiation import InitiationMixin, InitiationMetaMixin
from intertwine.trackable import Trackable
from intertwine.trackable.utils import build_table_model_map
from intertwine.utils.enums import UriType
from intertwine.utils.jsonable import Jsonable, JsonProperty
from intertwine.utils.mixins import AutoTableMixin

if sys.version_info >= (3,):
    unicode = str


class BaseIntertwineMeta(InitiationMetaMixin, Trackable):
    pass


class BaseIntertwineModel(InitiationMixin, Jsonable, AutoTableMixin,
                          ModelBase):

    ID_FIELDS = Jsonable.ID_FIELDS | {'uri'}
    URI_TYPE = UriType.NATURAL
    URI_EXCLUSIONS = {'org'}  # Org is not yet supported

    def json_key(self, key_type=None, raw=False, tight=True, **kwds):
        '''JSON key supports URI (default), NATURAL, and PRIMARY'''
        if key_type:
            if key_type is self.JsonKeyType.URI:
                uri = self.uri
                if uri:
                    return uri
                raise NotImplementedError('{cls} instance missing URI'
                                          .format(cls=self.__class__))
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
        '''Default URI property based on natural or primary key'''
        try:
            if self.__class__.URI_TYPE is UriType.NATURAL:
                return self.form_uri(self.derive_key())
            elif self.__class__.URI_TYPE is UriType.PRIMARY:
                return self.form_uri(self.pk)
            else:
                raise ValueError('Unknown UriType: {}'.format(
                    self.__class__.URI_TYPE))
        except AttributeError:
            return None

    jsonified_uri = JsonProperty(name='uri', before='json_key')

    @classmethod
    def form_uri(cls, components, sub=False, deconstruct=True):
        '''
        Form URI from given components

        components: Iterable of URL components, usually a Trackable Key
            namedtuple derived from the instance or formed manually. Any
            top-level exclusions can only be applied if a namedtuple.
        sub=False: If True, start with sub-blueprint (exclude blueprint)
        deconstruct=True If True, recursively deconstruct components
        return: URI composed from the components
        '''
        # Check for exclusions and filter them out
        exclusions = None
        try:
            exclusions = cls.URI_EXCLUSIONS  # raise if no URI_EXCLUSIONS
            components_dict = components._asdict()  # raise if not namedtuple
            components = (
                component for field, component in components_dict.items()
                if field not in exclusions)
        except AttributeError:
            pass
        # Recursively deconstruct components if flag is True (default)
        if deconstruct:
            components = chain(*(
                component.deconstruct(exclusions=exclusions)
                if hasattr(component, 'deconstruct')
                else (component,) for component in components))

        components = (unicode(component) if component is not None else ''
                      for component in components)

        sub_blueprint = cls.sub_blueprint_name()

        if sub:
            all_components = (
                chain(('', sub_blueprint), components)  # '' to prefix /
                if sub_blueprint else chain(('',), components))
        else:
            blueprint = cls.blueprint_name()
            all_components = (
                chain(('', blueprint, sub_blueprint), components)
                if sub_blueprint else chain(('', blueprint), components))

        return '/'.join(all_components)

    @classmethod
    def instantiate_uri(cls, uri):
        uri_components = uri.strip('/').split('/')
        blueprint_sub_map = cls.blueprint_sub_map()
        if uri_components[0] in blueprint_sub_map:
            blueprint_name = uri_components[0]
            if uri_components[1] in blueprint_sub_map[blueprint_name]:
                sub_blueprint_name = uri_components[1]
                components = uri_components[2:]
            else:
                sub_blueprint_name = None
                components = uri_components[1:]
            model = cls.blueprint_model(blueprint_name, sub_blueprint_name)
        else:
            components = uri_components
            model = cls

        exclusions = getattr(cls, 'URI_EXCLUSIONS', None)
        return model.reconstruct(components, exclusions=exclusions)

    @classmethod
    def blueprint_name(cls):
        '''Get blueprint name from containing module'''
        try:
            return cls._blueprint_name
        except AttributeError:
            if cls.__name__ in {'BaseIntertwineModel', 'Base'}:
                raise
            cls._blueprint_name = cls.__module__.split('.')[-2]
            return cls._blueprint_name

    @classmethod
    def sub_blueprint_name(cls):
        '''Get sub-blueprint name from class constant'''
        try:
            return cls.SUB_BLUEPRINT
        except AttributeError:
            return None

    @classmethod
    def blueprint_subs(cls, blueprint_name):
        '''Retrieve sub-blueprint names given blueprint name'''
        blueprint_sub_map = cls.blueprint_sub_map()
        return blueprint_sub_map[blueprint_name]

    @classmethod
    def blueprint_sub_map(cls):
        '''Sorted map of blueprint names to sub-blueprint name sets'''
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
        '''Retrieve model given blueprint/sub-blueprint names'''
        blueprint_key = (blueprint_name, sub_blueprint_name)
        blueprint_model_map = cls.blueprint_model_map()
        return blueprint_model_map[blueprint_key]

    @classmethod
    def blueprint_model_map(cls):
        '''Sorted map of (blueprint, sub-blueprint) tuples to models'''
        try:
            return cls._blueprint_model_map
        except AttributeError:
            models = sorted(
                Trackable._classes.values(),
                key=lambda x: (x.blueprint_name(), x.sub_blueprint_name()))
            cls._blueprint_model_map = OrderedDict(
                ((m.blueprint_name(), m.sub_blueprint_name()), m)
                for m in models)
            return cls._blueprint_model_map

    @classmethod
    def initialize_table_model_map(cls):
        '''Initialize table model map; invoke after loading all models'''
        cls._table_model_map = build_table_model_map(cls)
