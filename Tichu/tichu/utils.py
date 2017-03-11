

def raiser(ex):
    """
    :param ex: the exception to be raised
    :raise raises the given Exception
    """
    raise ex


def assert_(expr, e=AssertionError("personal assert_ failed")):
    """
    Raises an Exception when expr evaluates to False.

    :param expr: The expression
    :param e: (default AssertionError) exception to raise.
    :return: None
    """
    bool(expr) or raiser(e)


class Final(type):
    """
    Class that can not be subclassed.
    """
    def __new__(mcs, name, bases, classdict):
        for b in bases:
            if isinstance(b, Final):
                raise TypeError("type '{0}' is not an acceptable base type".format(b.__name__))
        return type.__new__(mcs, name, bases, dict(classdict))