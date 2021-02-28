"""
This file is based on a StackOverflow post by @301_Moved_Permanently.
See https://stackoverflow.com/a/50622643

The code was adapted to be able to wrap all methods of a class by simply
adding the decorator to the class itself.
"""

import inspect
import typing
from contextlib import suppress
from functools import wraps


def _is_unparameterized_special_typing(type_hint):
    # Check for typing.Any, typing.Union, typing.ClassVar (without parameters)
    if hasattr(typing, "_SpecialForm"):
        return isinstance(type_hint, typing._SpecialForm)
    elif hasattr(type_hint, "__origin__"):
        return type_hint.__origin__ is None
    else:
        return False


def enforce_types(target):
    """Class decorator adding type checks to all member functions
    """
    def check_types(spec, *args, **kwargs):
        parameters = dict(zip(spec.args, args))
        parameters.update(kwargs)
        for name, value in parameters.items():
            with suppress(KeyError):  # Assume un-annotated parameters can be any type
                type_hint = spec.annotations[name]
                if _is_unparameterized_special_typing(type_hint):
                    continue

                if hasattr(type_hint, "__origin__") and type_hint.__origin__ is not None:
                    actual_type = type_hint.__origin__
                elif hasattr(type_hint, "__args__") and type_hint.__args__ is not None:
                    actual_type = type_hint.__args__
                else:
                    actual_type = type_hint

                if not isinstance(value, actual_type):
                    raise TypeError("Unexpected type for '{}' (expected {} but found {})"
                                    .format(name, type_hint, type(value)))

    def decorate(func):
        spec = inspect.getfullargspec(func)

        @wraps(func)
        def wrapper(*args, **kwargs):
            check_types(spec, *args, **kwargs)
            return func(*args, **kwargs)

        return wrapper

    if inspect.isclass(target):
        members = inspect.getmembers(target, predicate=inspect.isfunction)
        for name, func in members:
            setattr(target, name, decorate(func))

        return target
    else:
        return decorate(target)
