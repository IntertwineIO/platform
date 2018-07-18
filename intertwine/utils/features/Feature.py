# -*- coding: utf-8 -*-
import json

# from ..registry import RegistryObject


class Feature(object):
    """
    Feature flag

    Args:
        name(string):  The name of the feature
        activate(bool):  Set the initial state [default: None]

    Example:
    >>> f = Feature('test')
    >>> f
    <Feature test {'active': None}>
    """

    def disable(self):
        """
        Disable feature flag

        Return:
            bool: current state
        """
        self.activated = False
        self.registry.set(self, self.activated)
        return self.activated

    def enable(self):
        """
        Enable feature flag

        Return:
            bool: current state
        """
        self.activated = True
        self.registry.set(self, self.activated)
        return self.activated

    def toggle(self):
        """
        Switch feature flag off and on

        Return:
            bool: current state
        """
        if self.activated is False:
            self.activated = True
        else:
            self.activated = False
        self.registry.set(self, self.activated)
        return self.activated

    def __init__(self, name, activate=None, registry=None):
        self.name = name
        self.activated = activate
        self.registry = registry
        self.registry.add(self)

    def __repr__(self):
        classname = self.__class__.__name__  # noqa: F841
        name = self.name  # noqa: F841
        fields = [
            'activated',
            'registry'
        ]
        feature_data = json.dumps({  # noqa: F841
            k: getattr(self, k) for k in fields
            if hasattr(self, k) and getattr(self, k) is not None})
        ldata = {k: v for k, v in locals().items()}
        rstring = '<{classname} {name} {feature_data}>'.format(**ldata)
        return rstring


f = Feature('test')
print(f)
