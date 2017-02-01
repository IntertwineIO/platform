# -*- coding: utf-8 -*-
import functools
from types import FunctionType, MethodType


class login_required(object):
    """Login decorator controls permissions for a function

    The login_required decorator can decorate a function (preferred) or
    a class or a class method.

    user has roles
    role has permissions

    user is a member of groups
    group has permissions
    """

    def __init__(self, *args, **kwds):
        args = list(args)
        self.args = args
        self.kwds = kwds
        fields = ['permission', 'user', 'role', 'group']
        for field_name, value in kwds.items():
            if field_name in fields:
                setattr(self, field_name, value)

        # Check for first argument as the decorated call
        # --------------------------------------------------------------
        # Note: On an empty decorator, the first argument will be the
        # function being decorated.  However, if the decorator has
        # parameters passed in, then the first argument will be a
        # decorator parameter.  Currently, there is an underlying
        # assumption that the decorator does not have a call
        # function or method or class as one of its parameters.
        # --------------------------------------------------------------
        if len(args) > 0:
            # Check for Functions and Class Methods
            valid_calls = (FunctionType, MethodType, type)
            if isinstance(args[0], valid_calls):
                self.call = args.pop(0)

        # Check for any remaining arguments
        for field_name, arg in zip(fields, args):
            setattr(self, field_name, arg)

    def __call__(self, *args, **kwds):
        args = list(args)

        # grab the call found in initialization if it was available
        # otherwise grab that function from the current set of arguments
        call = getattr(self, 'call', None)
        needs_wrapping = False
        if call is None:
            call = args.pop(0)
            if isinstance(call, (FunctionType, type)):
                needs_wrapping = True

        def wrap(*args, **kwds):
            value = call(*args, **kwds)
            return value

        if needs_wrapping:
            return functools.update_wrapper(wrap, call)

        return call(*args, **kwds)

        # Wrap the actual call and return the wrapper
        #

    def __repr__(self):
        cname = self.__class__.__name__  # noqa: ignore=F841
        args = getattr(self, 'args', None)
        kwds = getattr(self, 'kwds', None)
        permission = getattr(self, 'permission', None)
        call = getattr(self, 'call', None)
        if call is not None:
            call = call.__name__
        wrapped = isinstance(call, (FunctionType, type))
        string = '<@{cname}'
        extras = ''  # noqa: ignore=F841
        if permission is not None:
            string += '(permission={permission})'
        if call is not None:
            string += ' [{call}' if wrapped is not None else ' {call}'
            if args and kwds:
                string += '({args}, {kwds})'
            elif args:
                string += '{args}'
            elif kwds:
                string += '({kwds})'
            else:
                string += '()'
            string += ']' if wrapped is not None else ''
        string += '>'
        data = {k: v for k, v in locals().items()}
        string = string.format(**data)
        return string
