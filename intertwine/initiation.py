# -*- coding: utf-8 -*-


class InitiationMetaMixin:

    def __init__(cls, name, bases, attr):
        super(InitiationMetaMixin, cls).__init__(name, bases, attr)
        cls._class_init_()


class InitiationMixin:

    @classmethod
    def _class_init_(cls):
        # the delegation chain stops here
        assert not hasattr(super(InitiationMixin, cls), '_class_init_')
