# This module defines some immutable datatypes.
# Instead for mutating, they return a complete copy (with the mutation applied) of the datatype.

from collections import abc

from itertools import chain


class UnsupportedOperationError(Exception): pass


class frozenlist(tuple, abc.MutableSequence):
    """
    >>> frozenlist([1, 2, 3])
    frozenlist[1, 2, 3]
    >>> frozenlist([1, 2, 3]).pop()
    Traceback (most recent call last):
    ...
    immutable_collections.UnsupportedOperationError
    >>> frozenlist([1, 2, 3]).clear()
    Traceback (most recent call last):
    ...
    immutable_collections.UnsupportedOperationError
    >>> frozenlist([1, 2, 3]).reverse()
    Traceback (most recent call last):
    ...
    immutable_collections.UnsupportedOperationError
    >>> frozenlist([1, 2, 3])[1] = 6
    Traceback (most recent call last):
    ...
    immutable_collections.UnsupportedOperationError
    >>> l = frozenlist([1, 2, 3])
    >>> del l[1]
    Traceback (most recent call last):
    ...
    immutable_collections.UnsupportedOperationError
    """

    __slots__ = ()

    def append(self, element):
        """
        Creates a new *frozenlist* instance with the *element* appended to it.
        
        :param element: The element to be appended to the new frozenlist
        :return: The new frozenlist instance.
        
        >>> l1 = frozenlist([1, 2, 3])
        >>> l2 = l1.append(4)
        >>> l1, l2
        (frozenlist[1, 2, 3], frozenlist[1, 2, 3, 4])
        """
        return frozenlist(chain(self, (element,)))

    def extend(self, iterable):
        """Creates a new *frozenlist* instance composed of the calling instance and followed by the elements in the given iterator
        
        :param iterable: any iterable
        :return: The new frozenlist instance.
        
        >>> l1 = frozenlist([1, 2, 3])
        >>> l2 = l1.extend([4, 5, 6])
        >>> l1, l2
        (frozenlist[1, 2, 3], frozenlist[1, 2, 3, 4, 5, 6])
        """
        return frozenlist(chain(self, iterable))

    def insert(self, idx, element):
        """
        Creates a new *frozenlist* instance from the calling instance with the *element* at the given index. 
        
        :param element: The element to be inserted
        :return: The new frozenlist instance.
        
        >>> l1 = frozenlist([1, 2, 3])
        >>> l2 = l1.insert(1, 4)
        >>> l1, l2
        (frozenlist[1, 2, 3], frozenlist[1, 4, 2, 3])
        """
        return frozenlist(chain(self[:idx], (element,), self[idx:]))

    def remove(self, element):
        """
        Creates a new *frozenlist* instance with the first occurence of the *element* removed.
        
        :param element: The element to be removed
        :return: The new frozenlist instance.
        :raises: ValueError if no such element is in the list
        
        >>> l1 = frozenlist([1, 2, 3])
        >>> l2 = l1.remove(2)
        >>> l1, l2
        (frozenlist[1, 2, 3], frozenlist[1, 3])
        """
        idx = self.index(element)
        return frozenlist(self[:idx] + self[idx+1:])

    def copy(self):
        """
        **Note:** Since this class is immutable, there is no reason to call this function.
        
        :return: A shallow copy of this instance.
        
        >>> frozenlist([1, 2, 3]).copy()
        frozenlist[1, 2, 3]
        """
        return frozenlist(iter(self))

    def __repr__(self):
        return 'frozenlist[{}]'.format(', '.join(repr(e) for e in self))

    # Methods not supported:
    def pop(self, idx=-1):
        raise UnsupportedOperationError()

    def clear(self):
        raise UnsupportedOperationError()

    def reverse(self):
        raise UnsupportedOperationError()

    def __setitem__(self, index, item):
        raise UnsupportedOperationError()

    def __delitem__(self, item):
        raise UnsupportedOperationError()


class frozendict(dict):

    __slots__ = ()

    def __setitem__(self, *args, **kwargs):
        raise UnsupportedOperationError()

    def clear(self):
        raise UnsupportedOperationError()

    def pop(self, *args, **kwargs):
        raise UnsupportedOperationError()

    def popitem(self):
        raise UnsupportedOperationError()

    def update(self, m):
        raise UnsupportedOperationError()

    def __del__(self):
        raise UnsupportedOperationError()

    def __delitem__(self, *args, **kwargs):
        raise UnsupportedOperationError()

