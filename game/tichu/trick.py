import abc

from .cards import Card
# from .tichu_actions import CombinationAction  Info: imported later
from game.utils import TypedList, TypedTuple, indent


class CombinationActionList(TypedList):
    """ List only accepting Combination instances
    """
    __slots__ = ()

    def __new__(cls, iterable=list()):
        from .tichu_actions import CombinationAction
        return TypedList.__new__(cls, CombinationAction, iterable)

    def __init__(self, iterable):
        from .tichu_actions import CombinationAction
        super().__init__(CombinationAction, iterable)


class CombinationActionTuple(TypedTuple):
    __slots__ = ()

    def __new__(cls, iterable=list()):
        from .tichu_actions import CombinationAction
        return TypedTuple.__new__(cls, CombinationAction, iterable)


class BaseTrick(metaclass=abc.ABCMeta):

    @property
    def last_combination(self):
        return self[-1].combination if len(self) > 0 else None

    @property
    def last_combination_action(self):
        return self[-1] if len(self) > 0 else None

    @property
    def points(self):
        return self.count_points()

    @property
    def winner(self):
        return self.last_combination_action.player_pos

    def count_points(self):
        return sum([comb.combination.points for comb in self])

    def is_empty(self):
        return len(self) == 0

    def unique_id(self) -> str:
        """
        A string that has following property: 

        - A.unique_id() == B.unique_id() implies A == B
        - A.unique_id() != B.unique_id() implies A != B

        :return: A unique string for this instance 
        """
        idstr = ''
        for comb_action in self:
            idstr += str(comb_action.player_pos) + comb_action.combination.unique_id()
        return idstr

    def pretty_string(self, indent_=0):
        ind_str = indent(indent_, s=" ")
        if self.is_empty():
            return f"{self.__class__.__name__}(empty)"
        else:
            return f"{ind_str}{self.__class__.__name__}[{self[-1].player_pos}]: {' -> '.join([comb.pretty_string() for comb in self])}"

    def __str__(self):
        return self.pretty_string()


class UnfinishedTrick(CombinationActionList, BaseTrick):
    """Mutable Trick (list of combinations) instance
    >>> UnfinishedTrick()
    []
    >>> UnfinishedTrick().is_empty()
    True
    >>> UnfinishedTrick().count_points()
    0
    >>> UnfinishedTrick().last_combination_action

    >>> UnfinishedTrick().last_combination

    """
    __slots__ = ()

    def __init__(self, comb_actions=list()):
        super().__init__(comb_actions)

    @classmethod
    def from_trick(cls, trick):
        return cls(list(trick))

    def copy(self):
        return UnfinishedTrick(list(self))

    def finish(self):
        """
        :return: An (immutable) Trick
        """
        return Trick(list(self))


class Trick(CombinationActionTuple, BaseTrick):
    """ (Immutable) List of Combinations
    >>> Trick([])
    Trick()
    >>> Trick([]).is_empty()
    True
    >>> Trick([]).count_points()
    0
    >>> Trick([]).last_combination_action

    >>> Trick([]).last_combination

    >>> Trick([CombinationAction(1, Pair(Card.A_HOUSE, Card.A_JADE))])
    Trick(CombinationAction(1, PAIR(A♣,A♦)))
    >>> Trick([CombinationAction(1, Pair(Card.A_HOUSE, Card.A_JADE))]).is_empty()
    False
    >>> Trick([CombinationAction(1, Pair(Card.K_HOUSE, Card.K_JADE))]).count_points()
    20
    >>> Trick([CombinationAction(1, Pair(Card.A_HOUSE, Card.A_JADE))]).last_combination_action
    CombinationAction(1, PAIR(A♣,A♦))
    >>> Trick([CombinationAction(1, Pair(Card.A_HOUSE, Card.A_JADE))]).last_combination
    PAIR(A♣,A♦)
    """
    __slots__ = ()

    def __init__(self, comb_actions=list()):
        """
        :param comb_actions: a sequence of combinations.
        """
        super().__init__()

    @property
    def combinations(self):
        return list(self)

    @property
    def last_combination_action(self):
        return self[-1] if len(self) > 0 else None

    def add_combination_action(self, combination_action):
        ut = UnfinishedTrick.from_trick(self)
        ut.append(combination_action)
        return ut.finish()

    def is_dragon_trick(self):
        return Card.DRAGON in self.last_combination

    def __repr__(self):
        return "{}({})".format(self.__class__.__name__, ' -> '.join([repr(com) for com in self]))

