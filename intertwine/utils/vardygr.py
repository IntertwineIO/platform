#!/usr/bin/env python
# -*- coding: utf-8 -*-
import enum
from functools import partial

from .jsonable import Jsonable
from .tools import gethalffullargspec


class Vardygr(Jsonable):
    u"""
    Vardygrify

    A non-persisted, imitation instance of a SQLAlchemy model class.

    From Wikipedia (https://en.wikipedia.org/wiki/Vard%C3%B8ger):

        Vardoger, also known as vardyvle or vardyger, is a spirit
        predecessor in Scandinavian folklore. Stories typically include
        instances that are nearly deja vu in substance, but in reverse,
        where a spirit with the subject's footsteps, voice, scent, or
        appearance and overall demeanor precedes them in a location or
        activity, resulting in witnesses believing they've seen or heard
        the actual person before the person physically arrives. This
        bears a subtle difference from a doppelganger, with a less
        sinister connotation. It has been likened to being a phantom
        double, or form of bilocation.
    """
    EXCLUDED = {'model_class', 'object_session'}
    INCLUDED = set()  # {'__repr__', '__str__', '__unicode__'}

    @property
    def model_class(self):
        return self._model_class_

    # All class methods follow this pattern:

    def fields(self):
        """Return fields & SQLAlchemy/JSON properties of model class"""
        return self._model_class_.fields()

    def PrimaryKeyTuple(self):
        """PrimaryKey namedtuple constructor of model class"""
        return self._model_class_.PrimaryKeyTuple()

    def primary_key_fields(self):
        """Primary key fields from PrimaryKey namedtuple of model class"""
        return self._model_class_.primary_key_fields()

    @property
    def qualified_pk(self):
        return self.QualifiedPrimaryKey(self._model_class_, self.pk)

    def __repr__(self):
        return self.model_class.__repr__(self)

    def __str__(self):
        return self.model_class.__str__(self)

    def __unicode__(self):
        return self.model_class.__unicode__(self)

    def __init__(self, model_class, **kwds):
        self._model_class_ = model_class
        # fields = model_class.fields()

        for k, v in kwds.items():
            setattr(self, k, v)

        for attr_name in dir(model_class):
            if (attr_name in kwds or (attr_name[:2] == '__' and attr_name not in self.INCLUDED) or
                    attr_name in self.EXCLUDED):
                continue

            # print(attr_name)
            # if attr_name == 'uri':
            #     import ipdb; ipdb.set_trace()

            attribute = getattr(model_class, attr_name)

            if hasattr(attribute, '__call__'):
                fullargspec = gethalffullargspec(attribute)
                args = fullargspec.args
                if (len(args) > 0 and args[0] == 'self'):
                    setattr(self, attr_name, partial(attribute, self))
                    # if hasattr(attribute, '__get__'):  # descriptor
                    #     bind(attribute, attr_name, self)
                    # else:
                    #     setattr(self, attr_name, partial(attribute, self))
                else:  # classmethod, staticmethod, or included builtin
                    setattr(self, attr_name, attribute)
                continue

            if isinstance(attribute, enum.EnumMeta):
                # setattr(type(self), attr_name, attribute)
                continue

            try:
                if isinstance(attribute, property):
                    # TODO: either set at class level or process properties last
                    # properties must be set on the class to be used on an instance
                    # setattr(type(self), attr_name, property(attribute.fget))
                    value = attribute.fget(self)
                    setattr(self, attr_name, value)
                # not a descriptor
                elif not hasattr(attribute, '__get__'):
                    setattr(self, attr_name, attribute)
                else:
                    # print(f"Unhandled '{attr_name}' of type {type(attribute)}: {attribute}")
                    raise

            except Exception:
                try:
                    setattr(self, attr_name, None)
                except AttributeError:
                    pass
                    # print(f'Unable to assign {attr_name} to {value}')
