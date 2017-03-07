from collections import abc

from game.cards.card import Card

__author__ = 'Lukas Pestalozzi'


class ImmutableCards(abc.Collection):

    def __init__(self, cards):
        if all([isinstance(c, Card) for c in cards]) and cards is not None:
            self._cards = frozenset(cards)
            assert len(self._cards) == len(cards)  # make sure no card is 'lost' due to duplicated cards in 'cards'
        else:
            raise TypeError("Only instances of 'Card' can be put into 'Cards'.")

        self._hash = hash(self._cards)
        self._repr = "(len: {}, cards: {})".format(len(self._cards), repr(self._cards))
        self._str = "({})".format(', '.join([str(c) for c in self._cards]))

    def __hash__(self):
        return self._hash

    def __eq__(self, other):
        if self.__class__ is other.__class__ and len(self) == len(other):
            for c in self._cards:
                if c not in other:
                    return False
            return True
        else:
            return False

    @property
    def cards_list(self):
        return list(self._cards)

    @property
    def any_card(self):
        return next(iter(self._cards))

    @property
    def highest_card(self):
        return max(self._cards, key=lambda c: c.card_value)

    @property
    def lowest_card(self):
        return min(self._cards, key=lambda c: c.card_value)

    def count_points(self):
        """
        :return the Tichu points in this set of cards.
        """
        return sum([c.points for c in self._cards])

    def issubset(self, other):
        """
        :param other: Cards instance
        :return True iff this cards all appear in 'other'.
        """
        return self._cards.issubset(other._cards)

    def sorted_tuple(self, *args, **kwargs):
        """
        :param args, kwargs: same parameters as for the built in 'sorted' method
        :return: The elements as a sorted tuple
        """
        return sorted(tuple(self._cards), *args, **kwargs)

    def partitions(self):
        """
        :return: a set of partitions of the cards
        """

        # TODO speed, use other algorithm
        # TODO implement

        def powerset(seq):
            """
            Returns all the possible combinations of this set. This is a generator.
            """
            if len(seq) <= 1:
                yield seq  # single combination
                yield []
            else:
                for item in powerset(seq[1:]):
                    # item is a list of cards.
                    # cards_seq[0] is a single card.
                    yield [seq[0]] + item
                    yield item

    def __str__(self):
        return type(self).__name__+self._str

    def __repr__(self):
        return type(self).__name__+self._repr

    def __len__(self):
        return len(self._cards)

    def __length_hint__(self):
        return len(self._cards)

    def __iter__(self):
        return self._cards.__iter__()

    def __contains__(self, item):
        return self._cards.__contains__(item)


class Cards(ImmutableCards):
    """
    A mutable set of Cards with some helpful functions.
    """

    def __init__(self, cards):
        super().__init__(cards)
        self._cards = set(self._cards)

    def add(self, card):
        """
        Adds the card to this Cards set
        :param card: the Card to add
        :return: Nothing
        """
        if isinstance(card, Card):
            self._cards.add(card)
        else:
            raise TypeError("Only instances of 'Card' can be put into 'Cards', but was {}.".format(card))

    def add_all(self, other):
        """
        Adds all elements in 'other' to this Cards set.
        :param other: Iterable containing only Card instances.
        :return Nothing
        """
        for card in other:
            self.add(card)

    def remove(self, card):
        """
        Removes the card to this Cards set
        :param card: the Card to remove
        :return: Nothing
        """
        assert card in self._cards
        self._cards.remove(card)

    def remove_all(self, other):
        """
        Removes all elements in 'other' from this Cards set.
        :param other: Iterable containing only Card instances.
        :return: Nothing
        """
        for card in other:
            self.remove(card)

    def to_immutable(self):
        """
        :return: An ImmutableCards instance containing the same cards as calling instance
        """
        return ImmutableCards(self._cards)






