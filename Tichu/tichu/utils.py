

def raiser(ex):
    """
    :param ex: the exception to be raised
    :raise raises the given Exception
    """
    raise ex


def assert_(expr, e=None, msg="personal assert_ failed"):
    """
    Raises an Exception when expr evaluates to False.

    :param expr: The expression
    :param e: (default AssertionError) exception to raise.
    :return: None
    """
    bool(expr) or raiser(AssertionError(msg) if not e else e)


def try_ignore(fun_to_call, *args, **kwargs):
    """
    callf fun_to_call with the args and kwargs. If an exeption occures, then ignores it and returns None
    :param fun_to_call: a function to be called
    :return: the result of the function call or None if an exception was thrown
    """
    try:
        res = fun_to_call(*args, **kwargs)
        return res
    except Exception:
        return None

class Final(type):
    """
    Class that can not be subclassed.
    """
    def __new__(mcs, name, bases, classdict):
        for b in bases:
            if isinstance(b, Final):
                raise TypeError("type '{0}' is not an acceptable base type".format(b.__name__))
        return type.__new__(mcs, name, bases, dict(classdict))