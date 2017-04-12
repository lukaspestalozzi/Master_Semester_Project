from decorator import contextmanager


# unicode characters:


# functions

def raiser(ex):
    """
    :param ex: the exception to be raised
    :raise raises the given Exception
    """
    raise ex


def flatten(iterable):
    """
    >>> list(flatten(1))
    [1]
    >>> list(flatten(None))
    [None]
    >>> list(flatten("abc"))
    ['abc']
    >>> list(flatten([1]))
    [1]
    >>> list(flatten([1, "abc", [["de", 3]], "fg", 9]))
    [1, 'abc', 'de', 3, 'fg', 9]
    >>> list(flatten([1, 2, [3, [4, 5, 6], 7], [8, 9], (10, 11, {12}), 13, 14, [[[[[[15, 16]]], 17]], 18]]))
    [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18]


    Flattens the given iterable. Does treat strings and bytes not as iterables.
    if iterable is not an iterable, yields the element

    :param iterable: any iterable
    :return: a generator yielding all non iterable elements in the iterable.
    """
    if isinstance(iterable, (str, bytes)):
        yield iterable
        return
    try:
        for item in iterable:
            yield from flatten(item)
    except TypeError:
        yield iterable


def indent(n, s="-"):
    """
    :param n: number >= 0
    :param s: string
    :return: string containing a copy of n times the string s
    """
    return s.join("" for _ in range(n))


def check_true(expr, ex=AssertionError, msg="expr was not True"):
    """
    Raises an Exception when expr evaluates to False.

    :param expr: The expression
    :param ex: (optional, default AssertionError) exception to raise.
    :param msg: (optional) The message for the exception
    :return: True otherwise
    """
    if not bool(expr):
        raise ex(msg)
    else:
        return True


def check_all_isinstance(iterable, clazzes):
    """
    :return: True
    :raises: TypeError when for one of the items in iterable isinstance(item, clazzes) is False
    """
    for item in iterable:
        check_isinstance(item, clazzes)
    return True


def check_isinstance(item, clazzes, msg=None):
    """
    >>> check_isinstance(1, int)
    True
    >>> check_isinstance(1.1, (int, float))
    True
    >>> check_isinstance(1.1, [int, float])
    Traceback (most recent call last):
        ...
    TypeError: isinstance() arg 2 must be a type or tuple of types
    >>> check_isinstance(1.1, int, float)  # note that msg=float in this case
    Traceback (most recent call last):
        ...
    TypeError: <class 'float'>
    >>> check_isinstance(1.1, 1)
    Traceback (most recent call last):
        ...
    TypeError: isinstance() arg 2 must be a type or tuple of types
    >>> check_isinstance(1, float)
    Traceback (most recent call last):
        ...
    TypeError: item must be instance of at least one of: [<class 'float'>], but was 1

    :param item:
    :param clazzes: must be a type or tuple of types
    :param msg: (optional) The message for the exception
    :return: True
    :raises: TypeError when isinstance(item, clazzes) is False
    """
    if not isinstance(item, clazzes):
        message = msg if msg is not None else "item must be instance of at least one of: [{}], but was {}".format(clazzes, item.__class__)
        raise TypeError(message)
    else:
        return True


def check_param(expr, param="[No Parameter given]", msg=None):
    """
    :param expr:
    :param param: optional, the parameter to be checked, is only used in the error message
    :param msg: optional, In case the expr is False, show this message instead of the default one
    :return: True
    :raises: ValueError when the expr is Falsy (bool(expr) is False)
    """
    if not bool(expr):
        message = msg if msg is not None else "The Expression must be true, but was False. (param:{})".format(param)
        raise ValueError(message)
    else:
        return True


def crange(start, stop, modulo):
    """
    Circular range generator.
    :param start: int, start integer (included)
    :param stop: stop integer (excluded), If start == stop, then a whole circle is returned. ie. crange(0, 0, 4) -> [0, 1, 2, 3]
    :param modulo: the modulo of the range
    >>> list(crange(0, 5, 10))
    [0, 1, 2, 3, 4]
    >>> list(crange(7, 3, 10))
    [7, 8, 9, 0, 1, 2]
    >>> list(crange(0, 10, 4))
    [0, 1]
    >>> list(crange(13, 10, 4))
    [1]
    >>> list(crange(0, 0, 4))
    [0, 1, 2, 3]
    >>> list(crange(6, 6, 4))
    [2, 3, 0, 1]
    >>> list(crange(1, 2, 4))
    [1]
    >>> list(crange(1, 4, 4))
    [1, 2, 3]
    >>> list(crange(3, 2, 4))
    [3, 0, 1]
    >>> list(crange(3, 0, 4))
    [3]
    >>> list(crange(2, 3, 4))
    [2]
    >>> list(crange(2, 1, 4))
    [2, 3, 0]
    """
    startmod = start % modulo
    stopmod = stop % modulo
    yield startmod
    k = (startmod + 1) % modulo
    while k != stopmod:
        yield k
        k = (k + 1) % modulo



@contextmanager
def ignored(*exceptions):
    try:
        yield
    except exceptions:
        pass


class Final(type):
    """
    Class that can not be subclassed.
    """
    def __new__(mcs, name, bases, classdict):
        for b in bases:
            if isinstance(b, Final):
                raise TypeError("type '{0}' is not an acceptable base type".format(b.__name__))
        return type.__new__(mcs, name, bases, dict(classdict))


class Singleton(type):
    """
    Class that has only one instance
    """
    instance = None

    def __call__(cls, *args, **kw):
        if not cls.instance:
            cls.instance = super(Singleton, cls).__call__(*args, **kw)
        return cls.instance
