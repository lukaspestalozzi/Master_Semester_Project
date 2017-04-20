from .card import Card


class BitCards(object):
    """
    Immutable set of cards represented as a single number interpreted as a bit array.
    
    """
    _index_to_card = tuple([c for c in Card])
    _card_to_index = {c: idx for idx, c in enumerate(_index_to_card)}

    def __init__(self, n: int):
        self._n = n
        self._len = bin(n).count('1')  # TODO faster?

    @property
    def n(self):
        return self._n

    @property
    def cards_list(self):
        raise NotImplementedError()

    @property
    def cards(self):
        raise NotImplementedError()

    @property
    def any_card(self):
        raise NotImplementedError()

    @property
    def highest_card(self):
        raise NotImplementedError()

    @property
    def lowest_card(self):
        raise NotImplementedError()

    def copy(self):
        """

        :return: copy of this ImmutableCards instance
        """
        raise NotImplementedError()

    def union(self, other):
        """

        :param other:
        :return: frozenset of the union of both cards sets
        """
        raise NotImplementedError()

    def count_points(self):
        """
        :return the Tichu points in this set of cards.
        """
        raise NotImplementedError()

    def issubset(self, other):
        """
        :param other: Cards instance
        :return True iff this cards all appear in 'other'.
        """
        return self.n & other.n == other.n

    def partitions(self):
        """
        :return: a set of partitions of the cards
        """
        raise NotImplementedError()

    def value_dict(self, include_special=True):
        """
        :type include_special: bool: if False, the special cards are not in the dict
        :return: a dict mapping the card_values appearing in self._cards to the list of corresponding cards.
        """
        raise NotImplementedError()

    # TODO cache the results -> (only in immutable cards)

    def all_bombs(self, contains_value=None):
        raise NotImplementedError()

    def squarebombs(self, contains_value=None):
        raise NotImplementedError()

    def straightbombs(self, contains_value=None):
        raise NotImplementedError()

    def singles(self, contains_value=None):
        raise NotImplementedError()

    def pairs(self, ignore_phoenix=False, contains_value=None):
        raise NotImplementedError()

    def trios(self, ignore_phoenix=False, contains_value=None):
        raise NotImplementedError()

    def straights(self, length=None, ignore_phoenix=False, contains_value=None):
        raise NotImplementedError()

    def fullhouses(self, ignore_phoenix=False, contains_value=None):
        raise NotImplementedError()

    def pairsteps(self, ignore_phoenix=False, length=None, contains_value=None):
        raise NotImplementedError()

    def pairsteps_old(self, ignore_phoenix=False, length=None, contains_value=None):
        raise NotImplementedError()

    def all_combinations(self, played_on=None, ignore_phoenix=False, contains_value=None):
        raise NotImplementedError()

    def random_cards(self, n=1):
        """
        :param n: int > 0
        :return: n random cards.
        """
        raise NotImplementedError()

    def pretty_string(self):
        raise NotImplementedError()

    def __str__(self):
        raise NotImplementedError()

    def __repr__(self):
        raise NotImplementedError()

    def __len__(self):
        return self._len

    def __iter__(self):
        raise NotImplementedError()

    def __contains__(self, item):
        raise NotImplementedError()

    def __add__(self, other):
        raise NotImplementedError()

    def __hash__(self):
        raise NotImplementedError()

    def __eq__(self, other):
        raise NotImplementedError()
