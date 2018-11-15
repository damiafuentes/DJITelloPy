# Decorator to check method param type, raise needed exception type
# http://code.activestate.com/recipes/578809-decorator-to-check-method-param-types/
def accepts(**types):
    def check_accepts(f):
        argcount = f.func_code.co_argcount
        if 'self' in f.func_code.co_varnames:
            argcount -= 1

        s = "accept number of arguments not equal with function number of arguments in ", f.func_name, ", argcount ", argcount
        assert len(types) == argcount, s

        def new_f(*args, **kwds):
            for i, v in enumerate(args):
                if types.has_key(f.func_code.co_varnames[i]) and \
                        not isinstance(v, types[f.func_code.co_varnames[i]]):
                    raise TypeError("arg '%s'=%r does not match %s" % \
                                    (f.func_code.co_varnames[i], v, types[f.func_code.co_varnames[i]]))

            for k, v in kwds.iteritems():
                if types.has_key(k) and not isinstance(v, types[k]):
                    raise TypeError("arg '%s'=%r does not match %s" % (k, v, types[k]))

            return f(*args, **kwds)

        new_f.func_name = f.func_name
        return new_f

    return check_accepts
