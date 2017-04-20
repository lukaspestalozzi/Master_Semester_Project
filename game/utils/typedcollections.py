"""
This Module is not yet correct!!
"""

class TypedCollectionCreator(object):
    """
    Class enforcing that the iterable only contains elements of the given type (or subclasses) at initialisation. 
    
    That is, checks in the __new__ function that only elements of the given dtype are contained in the given sequence.
    
    It also stores the dtype in the dtype property.
    
    **Note:** This class is designed to be used in multiple inheritance in the form: 'class X(TypedCollectionCreator, some_builtin_collection)'
    
    """
    #__slots__ = ('_dtype',)

    def __new__(cls, dtype: type, sequence=()):
        if not isinstance(dtype, type):
            raise TypeError("t must be a type but was "+repr(dtype))
        if not all((isinstance(e, dtype) for e in sequence)):
            raise TypeError("All elements must be instance of {}".format(dtype))
        inst = super().__new__(cls, sequence)
        inst._dtype = dtype
        return inst

    @property
    def dtype(self):
        return self._dtype

    def __repr__(self):
        return '{name}{dtype}({elems})'.format(name=self.__class__.__name__, dtype=repr(self.dtype), elems=', '.join(repr(e) for e in self))


class TypedMutableCollectionCreator(TypedCollectionCreator):
    """
    Class calling the super __init__ with the given sequence argument.
    
    """

    __slots__ = ()

    def __init__(self, dtype: type, sequence=()):
        super().__init__(sequence)


class TypedFrozenSet(TypedCollectionCreator, frozenset):
    """frozenset containing only elements of a given type
    
    >>> TypedFrozenSet(int, (1, 3, 4))
    TypedFrozenSet<class 'int'>(1, 3, 4)
    >>> TypedFrozenSet(int, (1, 3, 4, 's'))
    Traceback (most recent call last):
    ...
    TypeError: All elements must be instance of <class 'int'>
    >>> TypedFrozenSet(int, (1, 3, 4)) | TypedFrozenSet(int, (5, 6, 7))
    TypedFrozenSet<class 'int'>(1, 3, 4, 5, 6, 7)
    >>> TypedFrozenSet(int, (1, 3, 4)).union( TypedFrozenSet(int, (5, 6, 7)))
    TypedFrozenSet<class 'int'>(1, 3, 4, 5, 6, 7) 
    """
    __slots__ = ()


class TypedSet(TypedMutableCollectionCreator, set):
    """(mutable) set containing only elements of the given type

    >>> TypedSet(int, (1, 3, 4))
    TypedSet<class 'int'>(1, 3, 4)
    >>> TypedSet(int, (1, 3, 4, 's'))
    Traceback (most recent call last):
    ...
    TypeError: All elements must be instance of <class 'int'>
    >>> TypedSet(int, (1, 2, 4)).difference(TypedSet(int, (1, 3, 4, 5)))
    TypedSet<class 'int'>(2)
    >>> TypedSet(int, (1, 3, 4)).difference(TypedSet(str, ('a', 'b', 'd')))
    TypedSet<class 'int'>(1, 3, 4)
    >>> TypedSet(int, (1, 3, 4)).intersection(TypedSet(int, (1, 3, 4, 5)))
    TypedSet<class 'int'>(1, 3, 4)
    >>> TypedSet(int, (1, 3, 4)).intersection(TypedSet(str, ('a', 'b', 'd')))
    TypedSet<class 'int'>()

    >>> TypedSet(int, (1, 3, 4)).symmetric_difference(TypedSet(int, (1, 3, 4, 5)))
    TypedSet<class 'int'>(5)
    >>> TypedSet(int, (1, 3, 4)).symmetric_difference(TypedSet(str, ('a', 'b', 'd')))
    Traceback (most recent call last):
    ...
    TypeError: All elements must be instance of <class 'int'>

    >>> TypedSet(int, (1, 3, 4)).union(TypedSet(int, (1, 3, 4, 5)))
    TypedSet<class 'int'>(1, 3, 4, 5)
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
    __slots__ = ()

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


class TypedTuple(TypedCollectionCreator, tuple):
    """tuple containing only elements of a given type
    
    >>> TypedTuple(int, (1, 3, 4))
    TypedTuple<class 'int'>(1, 3, 4)
    >>> TypedTuple(int, (1, 3, 4, 's'))
    Traceback (most recent call last):
    ...
    TypeError: All elements must be instance of <class 'int'>
    >>> TypedTuple(int, (1, 3, 4)) + TypedTuple(int, (1, 3, 4))
    TypedTuple<class 'int'>(1, 3, 4, 1, 3, 4)
    """
    __slots__ = ()


class TypedList(TypedMutableCollectionCreator, list):
    """
    >>> TypedList(int, (1, 3, 4))
    TypedList([1, 3, 4])
    >>> TypedList(int, (1, 3, 4, 's'))
    Traceback (most recent call last):
    ...
    TypeError: All elements must be instance of <class 'int'>
    >>> tl = TypedList(int, (1, 2, 4))
    >>> tl.append(3)
    >>> tl
    TypedList([1, 2, 4, 3])
    >>> TypedList(int, (1, 3, 4)).append('a')
    Traceback (most recent call last):
    ...
    TypeError: elem must be of type <class 'int'>, but was <class 'str'>

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
    >>> TypedList(int, (1, 3, 4)) + TypedList(int, (1, 3, 4))
    TypedList([1, 3, 4, 1, 3, 4])
    """
    __slots__ = ()

    def append(self, elem):
        if not isinstance(elem, self._dtype):
            raise TypeError("elem must be of type {}, but was {}".format(self._dtype, elem.__class__))
        return super().append(elem)

    def __setitem__(self, key, value):
        if not isinstance(value, self._dtype):
            raise TypeError("value must be of type {}".format(self._dtype))
        return super().__setitem__(key, value)


