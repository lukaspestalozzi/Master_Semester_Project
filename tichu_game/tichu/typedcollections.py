

# TODO use hypothesis for tests


class TypedFrozenSet(frozenset):
    """frozenset containing only elements of a given type"""
    __slots__ = ()

    def __new__(cls, dtype, iterable):
        """
        :param dtype: the type
        :param args: iterable
        """
        if not isinstance(dtype, type):
            raise TypeError("t must be a type")
        if not all((e for e in iterable)):
            raise TypeError("All elements must be instance of {}".format(dtype))
        return frozenset.__new__(cls, iterable)


class TypedSet(set):
    """(mutable) set containing only elements of the given type

    >>> TypedSet(int, (1, 3, 4))
    TypedSet({1, 3, 4})
    >>> TypedSet(int, (1, 3, 4, 's'))
    Traceback (most recent call last):
    ...
    TypeError: All elements must be instance of <class 'int'>
    >>> TypedSet(int, (1, 2, 4)).difference(TypedSet(int, (1, 3, 4, 5)))
    TypedSet({2})
    >>> TypedSet(int, (1, 3, 4)).difference(TypedSet(str, ('a', 'b', 'd')))
    TypedSet({1, 3, 4})

    >>> TypedSet(int, (1, 3, 4)).intersection(TypedSet(int, (1, 3, 4, 5)))
    TypedSet({1, 3, 4})
    >>> TypedSet(int, (1, 3, 4)).intersection(TypedSet(str, ('a', 'b', 'd')))
    TypedSet()

    >>> TypedSet(int, (1, 3, 4)).symmetric_difference(TypedSet(int, (1, 3, 4, 5)))
    TypedSet({5})
    >>> TypedSet(int, (1, 3, 4)).symmetric_difference(TypedSet(str, ('a', 'b', 'd')))
    Traceback (most recent call last):
    ...
    TypeError: All elements must be instance of <class 'int'>

    >>> TypedSet(int, (1, 3, 4)).union(TypedSet(int, (1, 3, 4, 5)))
    TypedSet({1, 3, 4, 5})
    >>> TypedSet(int, (1, 3, 4)).union(TypedSet(str, ('a', 'b', 'd')))
    Traceback (most recent call last):
    ...
    TypeError: All elements must be instance of <class 'int'>

    >>> TypedSet(int, (1, 3, 4)).update(TypedSet(int, (1, 3, 4, 5)))

    >>> TypedSet(int, (1, 3, 4)).update(TypedSet(str, ('a', 'b', 'd')))
    Traceback (most recent call last):
    ...
    TypeError: Operation only permitted with a TypedSet of the same type (<class 'int'>)
    >>> TypedSet(int, (1, 3, 4)).intersection_update(TypedSet(int, (1, 3, 4, 5)))

    >>> TypedSet(int, (1, 3, 4)).intersection_update(TypedSet(str, ('a', 'b', 'd')))
    Traceback (most recent call last):
    ...
    TypeError: Operation only permitted with a TypedSet of the same type (<class 'int'>)
    >>> TypedSet(int, (1, 3, 4)).difference_update(TypedSet(int, (1, 3, 4, 5)))

    >>> TypedSet(int, (1, 3, 4)).difference_update(TypedSet(str, ('a', 'b', 'd')))
    Traceback (most recent call last):
    ...
    TypeError: Operation only permitted with a TypedSet of the same type (<class 'int'>)
    >>> TypedSet(int, (1, 3, 4)).symmetric_difference_update(TypedSet(int, (1, 3, 4, 5)))

    >>> TypedSet(int, (1, 3, 4)).symmetric_difference_update(TypedSet(str, ('a', 'b', 'd')))
    Traceback (most recent call last):
    ...
    TypeError: Operation only permitted with a TypedSet of the same type (<class 'int'>)
    >>> TypedSet(int, (1, 3, 4)).add(5)

    >>> TypedSet(int, (1, 3, 4)).add('d')
    Traceback (most recent call last):
    ...
    TypeError: elem must be of type <class 'int'>
    """
    __slots__ = ("_dtype",)

    def __init__(self, dtype, iterable):
        if not isinstance(dtype, type):
            raise TypeError("t must be a type")
        if any((not isinstance(e, dtype) for e in iterable)):
            raise TypeError("All elements must be instance of {}".format(dtype))
        super().__init__(iterable)
        self._dtype = dtype

    @property
    def dtype(self):
        return self._dtype

    def difference(self, *others):
        sup = super().difference(*others)
        return TypedSet(self._dtype, sup)

    def intersection(self, *others):
        sup = super().intersection(*others)
        return TypedSet(self._dtype, sup)

    def symmetric_difference(self, other):
        sup = super().symmetric_difference(other)
        return TypedSet(self._dtype, sup)

    def union(self, *others):
        sup = super().union(*others)
        return TypedSet(self._dtype, sup)

    def _check_same_type(self, *others):
        if not all((isinstance(o, TypedSet) and o.dtype == self.dtype for o in others)):
            raise TypeError("Operation only permitted with a TypedSet of the same type ({})".format(self._dtype))
        return True

    def update(self, *others):
        self._check_same_type(*others)
        return super().update(*others)

    def intersection_update(self, *others):
        self._check_same_type(*others)
        return super().intersection_update(*others)

    def difference_update(self, *others):
        self._check_same_type(*others)
        return super().difference_update(*others)

    def symmetric_difference_update(self, other):
        self._check_same_type(other)
        return super().symmetric_difference_update(other)

    def add(self, elem):
        if not isinstance(elem, self._dtype):
            raise TypeError("elem must be of type {}".format(self._dtype))
        return super().add(elem)


class TypedTuple(tuple):
    """tuple containing only elements of a given type"""
    __slots__ = ()

    def __new__(cls, dtype, iterable):
        """
        :param dtype: the type
        :param args: iterable
        """
        if not isinstance(dtype, type):
            raise TypeError("t must be a type")
        if not all((e for e in iterable)):
            raise TypeError("All elements must be instance of {}".format(dtype))
        return tuple.__new__(cls, iterable)


class TypedList(list):
    """
    >>> TypedList(int, (1, 3, 4))
    [1, 3, 4]
    >>> TypedList(int, (1, 3, 4, 's'))
    Traceback (most recent call last):
    ...
    TypeError: All elements must be instance of <class 'int'>
    >>> tl = TypedList(int, (1, 2, 4))
    >>> tl.append(3)
    >>> tl
    [1, 2, 4, 3]
    >>> TypedList(int, (1, 3, 4)).append('a')
    Traceback (most recent call last):
    ...
    TypeError: elem must be of type <class 'int'>

    >>> TypedList(int, (1, 2, 4))[0]
    1
    >>> tl = TypedList(int, (1, 3, 4))
    >>> tl[2] = 10
    >>> tl[2] == 10
    True
    >>> tl = TypedList(int, (1, 3, 4))
    >>> tl[2] = 'a'
    Traceback (most recent call last):
    ...
    TypeError: value must be of type <class 'int'>

    """
    __slots__ = ("_dtype",)

    def __init__(self, dtype, iterable):
        if not isinstance(dtype, type):
            raise TypeError("t must be a type")
        if any((not isinstance(e, dtype) for e in iterable)):
            raise TypeError("All elements must be instance of {}".format(dtype))
        super().__init__(iterable)
        self._dtype = dtype

    @property
    def dtype(self):
        return self._dtype

    def append(self, elem):
        if not isinstance(elem, self._dtype):
            raise TypeError("elem must be of type {}, but was {}".format(self._dtype, elem.__class__))
        return super().append(elem)

    def __setitem__(self, key, value):
        if not isinstance(value, self._dtype):
            raise TypeError("value must be of type {}".format(self._dtype))
        return super().__setitem__(key, value)



