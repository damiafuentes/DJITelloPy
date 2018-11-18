import sys


# Decorator to check method param type, raise needed exception type
# http://code.activestate.com/recipes/578809-decorator-to-check-method-param-types/
def accepts(**types):
    def check_accepts(f):
        if sys.version_info >= (3, 0):
            fun_code = f.__code__
            fun_name = f.__name__
        else:
            fun_code = f.func_code
            fun_name = f.func_name

        argcount = fun_code.co_argcount
        if 'self' in fun_code.co_varnames:
            argcount -= 1

        s = "accept number of arguments not equal with function number of arguments in ", fun_name, ", argcount ", \
            argcount
        assert len(types) == argcount, s

        def new_f(*args, **kwds):
            for i, v in enumerate(args):
                if fun_code.co_varnames[i] in types and \
                        not isinstance(v, types[fun_code.co_varnames[i]]):
                    raise TypeError("arg '%s'=%r does not match %s" % (fun_code.co_varnames[i], v,
                                                                       types[fun_code.co_varnames[i]]))

            for k, v in kwds.items():
                if k in types and not isinstance(v, types[k]):
                    raise TypeError("arg '%s'=%r does not match %s" % (k, v, types[k]))

            return f(*args, **kwds)

        if sys.version_info >= (3, 0):
            new_f.__name__ = fun_name
        else:
            new_f.func_name = fun_name
        return new_f

    return check_accepts
