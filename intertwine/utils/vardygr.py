#!/usr/bin/env python
# -*- coding: utf-8 -*-
from sqlalchemy.orm.attributes import InstrumentedAttribute, QueryableAttribute
# from sqlalchemy.orm.instrumentation import ClassManager
# from sqlalchemy.sql.schema import MetaData


class Vardygr(type):
    u"""
    Vardygr

    A metaclass for uninstrumented imitation of SQLAlchemy models, used
    by the vardygrify utility to create unpersisted model instances.
    Read-only content must be furnished for visitors, but bots crawl the
    site generating a large number of objects. Vardygr allows objects to
    be furnished, but not persisted.

    Each Vardygr class is cached in memory to speed instance generation.
    The initial implementation utilized create_autospec from the mock
    library, but this was so slow that it was a serious bottleneck. This
    version is about 9,000 times (i.e. 900,000%) faster.

    The original model is referenced by the 'model_class' attribute.
    Class references for model instances may utilize a property:

        @property
        def model_class(self):
            return self.__class__

    About the name:

        Vardoger, also known as vardyvle or vardyger [or vardygr], is a
        spirit predecessor in Scandinavian folklore. Stories typically
        include instances that are nearly deja vu in substance, but in
        reverse, where a spirit with the subject's footsteps, voice,
        scent, or appearance and overall demeanor precedes them in a
        location or activity, resulting in witnesses believing they've
        seen or heard the actual person before the person physically
        arrives. This bears a subtle difference from a doppelganger,
        with a less sinister connotation. It has been likened to being a
        phantom double, or form of bilocation.

        Source: https://en.wikipedia.org/wiki/Vard%C3%B8ger
    """
    MODEL_CLASS_TAG = 'model_class'
    VARDYGR_EXCLUDED = {MODEL_CLASS_TAG, 'object_session'}
    VARDYGR_INCLUDED = {'__repr__', '__str__', '__unicode__'}
    # Vardygr class must not be ORM-instrumented (the whole point)
    VARDYGR_NULLIFIED = (InstrumentedAttribute, QueryableAttribute)

    _vardygr_classes = {}

    @classmethod
    def _set_vardygr_attributes(meta, model_class, attrs):
        for attr_name in dir(model_class):
            if ((attr_name[:2] == '__' and attr_name not in meta.VARDYGR_INCLUDED) or
                    attr_name in meta.VARDYGR_EXCLUDED):
                continue

            try:
                attr_value = getattr(model_class, attr_name)
                if isinstance(attr_value, meta.VARDYGR_NULLIFIED):
                    attr_value = None

            except Exception:
                attr_value = None

            # print(f'{attr_name}: {attr_value} of type {type(attr_value)}')
            attrs[attr_name] = attr_value

    def __new__(meta, name, bases, attrs):
        model_class = attrs['model_class']
        vardygr_class_name = name or f'Vardygr{model_class.__name__}'
        if vardygr_class_name in meta._vardygr_classes:
            return meta._vardygr_classes[vardygr_class_name]

        meta._set_vardygr_attributes(model_class, attrs)
        vardygr_class = super().__new__(meta, vardygr_class_name, bases, attrs)
        meta._vardygr_classes[vardygr_class_name] = vardygr_class
        return vardygr_class

    def __call__(cls, **kwds):
        instance = super().__call__()
        for k, v in kwds.items():
            setattr(instance, k, v)
        return instance


def vardygrify(model_class, **kwds):
    attrs = {}
    attrs[Vardygr.MODEL_CLASS_TAG] = model_class
    vardygr_class = Vardygr(None, (), attrs)
    vardygr_instance = vardygr_class(**kwds)
    return vardygr_instance
