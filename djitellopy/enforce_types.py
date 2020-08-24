import inspect
import typing
from contextlib import suppress
from functools import wraps

# this file is based on a StackOverflow post by @301_Moved_Permanently
# see https://stackoverflow.com/a/50622643

# the code was adapted to be able to wrap all methods of a class by simply
# adding the decorator to the class itself

def enforce_types(target):
    def check_types(spec, *args, **kwargs):
        parameters = dict(zip(spec.args, args))
        parameters.update(kwargs)
        for name, value in parameters.items():
            with suppress(KeyError):  # Assume un-annotated parameters can be any type
                type_hint = spec.annotations[name]
                if isinstance(type_hint, typing._SpecialForm):
                    # No check for typing.Any, typing.Union, typing.ClassVar (without parameters)
                    continue
                try:
                    actual_type = type_hint.__origin__
                except AttributeError:
                    # In case of non-typing types (such as <class 'int'>, for instance)
                    actual_type = type_hint
                # In Python 3.8 one would replace the try/except with
                # actual_type = typing.get_origin(type_hint) or type_hint
                if isinstance(actual_type, typing._SpecialForm):
                    # case of typing.Union[…] or typing.ClassVar[…]
                    actual_type = type_hint.__args__

                if not isinstance(value, actual_type):
                    raise TypeError('Unexpected type for \'{}\' (expected {} but found {})'.format(name, type_hint, type(value)))

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