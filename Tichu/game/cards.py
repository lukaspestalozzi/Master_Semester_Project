from collections import defaultdict
from enum import Enum
import random as rnd

from game.exceptions import LogicError
from game.utils import raiser

__author__ = 'Lukas Pestalozzi'


class ComparableEnum(Enum):
    """
    Enum that allows comparing instances with >, >=, <=, <
    """

    # functions to compare the enum
    def _raise_cant_compare(self, other):
        raise TypeError(
                "operation not supported between instances of {} and {}.".format(self.__class__, other.__class__))

    def __ge__(self, other):
        if self.__class__ is other.__class__:
            return self.value >= other.height
        self._raise_cant_compare(other)

    def __gt__(self, other):
        if self.__class__ is other.__class__:
            return self.value > other.height
        self._raise_cant_compare(other)

    def __le__(self, other):
        if self.__class__ is other.__class__:
            return self.value <= other.height
        self._raise_cant_compare(other)

    def __lt__(self, other):
        if self.__class__ is other.__class__:
            return self.value < other.height
        self._raise_cant_compare(other)


class CardValue(ComparableEnum):
    TWO = 2
    THREE = 3
    FOUR = 4
    FIVE = 5
    SIX = 6
    SEVEN = 7
    EIGHT = 8
    NINE = 9
    TEN = 10
    J = 11
    Q = 12
    K = 13
    A = 14
    DRAGON = 15
    PHOENIX = 1.5
    MAHJONG = 1
    DOG = 0

    def __init__(self, _):
        if self.value is 5:
            self._points = 5
        elif self.value in [10, 13]:
            self._points = 10
        elif self.value is 15:
            self._points = 25
        elif self.value is 1.5:
            self._points = -25
        else:
            self._points = 0

    @property
    def height(self):
        return self.value

    @property
    def points(self):
        return self._points

    def __repr__(self):
        return "{}({})".format(self.name, self.value)


class CardSuit(Enum):
    SWORD = 'Black'
    PAGODA = 'Red'
    HOUSE = 'Blue'
    JADE = 'Green'
    SPECIAL = 'Special'

    def __init__(self, color):
        self._value_ = self._name_
        self._color = color

    @property
    def color(self):
        return self._color

    def __repr__(self):
        return "Suit({})".format(self.name)


class Card(ComparableEnum):
    DRAGON = (CardValue.DRAGON, CardSuit.SPECIAL)
    PHOENIX = (CardValue.PHOENIX, CardSuit.SPECIAL)
    MAHJONG = (CardValue.MAHJONG, CardSuit.SPECIAL)
    DOG = (CardValue.DOG, CardSuit.SPECIAL)

    TWO_JADE = (CardValue.TWO, CardSuit.JADE)
    THREE_JADE = (CardValue.THREE, CardSuit.JADE)
    FOUR_JADE = (CardValue.FOUR, CardSuit.JADE)
    FIVE_JADE = (CardValue.FIVE, CardSuit.JADE)
    SIX_JADE = (CardValue.SIX, CardSuit.JADE)
    SEVEN_JADE = (CardValue.SEVEN, CardSuit.JADE)
    EIGHT_JADE = (CardValue.EIGHT, CardSuit.JADE)
    NINE_JADE = (CardValue.NINE, CardSuit.JADE)
    TEN_JADE = (CardValue.TEN, CardSuit.JADE)
    J_JADE = (CardValue.J, CardSuit.JADE)
    Q_JADE = (CardValue.Q, CardSuit.JADE)
    K_JADE = (CardValue.K, CardSuit.JADE)
    A_JADE = (CardValue.A, CardSuit.JADE)

    TWO_HOUSE = (CardValue.TWO, CardSuit.HOUSE)
    THREE_HOUSE = (CardValue.THREE, CardSuit.HOUSE)
    FOUR_HOUSE = (CardValue.FOUR, CardSuit.HOUSE)
    FIVE_HOUSE = (CardValue.FIVE, CardSuit.HOUSE)
    SIX_HOUSE = (CardValue.SIX, CardSuit.HOUSE)
    SEVEN_HOUSE = (CardValue.SEVEN, CardSuit.HOUSE)
    EIGHT_HOUSE = (CardValue.EIGHT, CardSuit.HOUSE)
    NINE_HOUSE = (CardValue.NINE, CardSuit.HOUSE)
    TEN_HOUSE = (CardValue.TEN, CardSuit.HOUSE)
    J_HOUSE = (CardValue.J, CardSuit.HOUSE)
    Q_HOUSE = (CardValue.Q, CardSuit.HOUSE)
    K_HOUSE = (CardValue.K, CardSuit.HOUSE)
    A_HOUSE = (CardValue.A, CardSuit.HOUSE)

    TWO_SWORD = (CardValue.TWO, CardSuit.SWORD)
    THREE_SWORD = (CardValue.THREE, CardSuit.SWORD)
    FOUR_SWORD = (CardValue.FOUR, CardSuit.SWORD)
    FIVE_SWORD = (CardValue.FIVE, CardSuit.SWORD)
    SIX_SWORD = (CardValue.SIX, CardSuit.SWORD)
    SEVEN_SWORD = (CardValue.SEVEN, CardSuit.SWORD)
    EIGHT_SWORD = (CardValue.EIGHT, CardSuit.SWORD)
    NINE_SWORD = (CardValue.NINE, CardSuit.SWORD)
    TEN_SWORD = (CardValue.TEN, CardSuit.SWORD)
    J_SWORD = (CardValue.J, CardSuit.SWORD)
    Q_SWORD = (CardValue.Q, CardSuit.SWORD)
    K_SWORD = (CardValue.K, CardSuit.SWORD)
    A_SWORD = (CardValue.A, CardSuit.SWORD)

    TWO_PAGODA = (CardValue.TWO, CardSuit.PAGODA)
    THREE_PAGODA = (CardValue.THREE, CardSuit.PAGODA)
    FOUR_PAGODA = (CardValue.FOUR, CardSuit.PAGODA)
    FIVE_PAGODA = (CardValue.FIVE, CardSuit.PAGODA)
    SIX_PAGODA = (CardValue.SIX, CardSuit.PAGODA)
    SEVEN_PAGODA = (CardValue.SEVEN, CardSuit.PAGODA)
    EIGHT_PAGODA = (CardValue.EIGHT, CardSuit.PAGODA)
    NINE_PAGODA = (CardValue.NINE, CardSuit.PAGODA)
    TEN_PAGODA = (CardValue.TEN, CardSuit.PAGODA)
    J_PAGODA = (CardValue.J, CardSuit.PAGODA)
    Q_PAGODA = (CardValue.Q, CardSuit.PAGODA)
    K_PAGODA = (CardValue.K, CardSuit.PAGODA)
    A_PAGODA = (CardValue.A, CardSuit.PAGODA)

    def __init__(self, cardvalue, cardsuit):
        self._suit = cardsuit
        self._cardvalue = cardvalue
        self._color = cardsuit.color
        self._hash = hash((cardvalue, cardsuit))

    @property
    def suit(self):
        return self._suit

    @property
    def card_value(self):
        return self._cardvalue

    @property
    def card_height(self):
        return self._cardvalue.height

    @property
    def color(self):
        return self._color

    @property
    def points(self):
        return self._cardvalue.points

    def __eq__(self, other):  # TODO question, raise error when classes not the same?
        return self.__class__ is other.__class__ and self.card_value == other.card_value and self._suit == other.suit

    def __ne__(self, other):
        return not self.__eq__(other)

    def __repr__(self):
        return "Card({}, {})".format(repr(self._cardvalue), repr(self._suit))

    def __hash__(self):
        return self._hash


class Cards(object):  # TODO inherit from collections.abc? Sequence?
    """
    A mutable set of Cards with some helpful functions.

    """

    def __init__(self, cards):
        if all([isinstance(c, Card) for c in cards]):
            self._cards = set(cards)
        else:
            raise TypeError("Only instances of 'Card' can be put into 'Cards'.")

    def count_points(self):
        """
        :return the Tichu points in this set of cards.
        """
        return sum([c.points for c in self._cards])

    def issubset(self, other):
        """
        :param other: Iterable
        :return True iff this cards all appear in 'other'.
        """
        return all([(c in other) for c in
                    self._cards])  # TODO replace with self._cards <= other._cards, or issubset(other._cards)

    def add(self, card):
        """
        Adds the card to this Cards set
        :param card: the Card to add
        :return: self
        """
        if isinstance(card, Card):
            self._cards.add(card)
        else:
            raise TypeError("Only instances of 'Card' can be put into 'Cards'.")
        return self

    def add_all(self, other):
        """
        Adds all elements in 'other' to this Cards set.
        :param other: Iterable containing only Card instances.
        :return self
        """
        for card in other:
            self.add(card)
        return self

    def remove(self, card):
        """
        Removes the card to this Cards set
        :param card: the Card to remove
        :return: self
        """
        self._cards.remove(card)
        return self

    def remove_all(self, other):
        """
        Removes all elements in 'other' from this Cards set.
        :param other: Iterable containing only Card instances.
        :return self
        """
        for card in other:
            self.remove(card)
        return self

    def sorted_tuple(self, *args, **kwargs):
        """
        :param args, kwargs: same parameters as for the built in 'sorted' method
        :return: The elements as a sorted tuple
        """
        return sorted(tuple(self._cards), *args, **kwargs)

    # TODO question, add <, <=, >, >= ?

    def __repr__(self):
        return "Cards{}".format(str(self._cards))

    def __str__(self):
        return self.__repr__()

    def __eq__(self, other):
        return len(other) == len(self._cards) and all([(c in other) for c in self._cards])

    def __len__(self):
        return len(self._cards)

    def __length_hint__(self):
        return len(self._cards)

    def __iter__(self):
        return self._cards.__iter__()

    def __reversed__(self):
        return Cards(reversed(list(self._cards)))

    def __contains__(self, item):
        return self._cards.__contains__(item)


class CombinationType(ComparableEnum):
    DOG = None  # Dog (must be played alone, can't be compared to any other card)
    SINGLE_MAHJONG = 1  # Mahjong played alone (lowest possible value)
    SINGLE_PHOENIX = 2  # Phoenix played alone (value 1/2 higher than the last played single card)
    SINGLE_CARD = 10  # single (non special) card
    DRAGON = 100  # the Dragon (must be played alone)
    PAIR = 200  # two cards with same value
    TRIO = 300  # three cards with same value
    FULLHOUSE = 500  # a Pair and a Trio
    PAIR_STEPS = 600  # 2 or more consecutive Pairs
    STRAIGHT = 700  # 5 or more consecutive cards
    SQUAREBOMB = 1000  # four cards with same value
    STRAIGHTBOMB = 2000  # 5 or more consecutive cards with the same suit

    @property
    def numeric_value(self):
        return self.value


class Combination(Cards):

    def __init__(self, cards, phoenix_as=None):
        """
        :param cards: an iterable of Card instances.
        :param phoenix_as: Card or None; The card the PHOENIX should represent in the Combination.
        If the phoenix is not in the combination, this argument is ignored. Also, the phoenix can't take on a card already in the combination.
        """
        if Card.PHOENIX in cards:
            if len(cards) == 1 and phoenix_as is not Card.PHOENIX:  # A phoenix played alone is a valid combination. But the phoenix counts 1/2 higher than the last played combination.
                raise ValueError("When The phoenix is played alone, then phoenix_as mut be the phoenix itself..")
            elif phoenix_as is None:
                raise ValueError("When The phoenix appears in the cards, then phoenix_as must be a Card.")
            elif not isinstance(phoenix_as, Card):
                raise ValueError("The phoenix must be a Card.")
            elif phoenix_as in cards:
                raise ValueError("The phoenix can't take on a card already in the combination.")
            elif phoenix_as.suit is CardSuit.SPECIAL:
                raise ValueError("The phoenix can't take on a special card.")

        super().__init__(cards)
        self._cards = frozenset(self._cards)  # make Combination immutable
        self._phoenix = phoenix_as if phoenix_as else None
        self._cards_with_phoenix_replaced = frozenset([c for c in self._cards if c is not Card.PHOENIX] + [self._phoenix]) if self._phoenix else self._cards
        self._comb_type = self._combination_type()
        if self._comb_type is None:
            raise ValueError("{} is no valid combination.".format(str(cards)))
        self._comb_height = self._init_height()

    @property
    def type(self):
        return self._comb_type

    @property
    def height(self):
        return self._comb_height

    def add(self, card):
        raise TypeError("Combination is immutable")

    def remove(self, card):
        raise TypeError("Combination is immutable")

    def is_bomb(self):
        return self.type is CombinationType.SQUAREBOMB or self.type is CombinationType.STRAIGHTBOMB

    def contains_phoenix(self):
        return bool(self._phoenix)
    
    def _combination_type(self):
        # TODO improvement: test only possible combinations depending on len(cards)
        """
        :return the CombinationType of this combination. if the cards don't constitute a valid Combination returns None
        """
        nbr_cards = len(self._cards_with_phoenix_replaced)
        if nbr_cards == 0 or nbr_cards > 15:
            return None

        elif Combination.is_dog(self._cards):
            return CombinationType.DOG

        elif Combination.is_single_mahjong(self._cards):
            return CombinationType.SINGLE_MAHJONG

        elif Combination.is_single_phoenix(self._cards):
            return CombinationType.SINGLE_PHOENIX

        elif Combination.is_single_dragon(self._cards):
            return CombinationType.SINGLE_DRAGON

        elif Combination.is_single(self._cards):
            return CombinationType.SINGLE_CARD

        elif Combination.is_pair(self._cards_with_phoenix_replaced):
            return CombinationType.PAIR

        elif Combination.is_pair_step(self._cards_with_phoenix_replaced):
            return CombinationType.PAIR_STEPS

        elif Combination.is_trio(self._cards_with_phoenix_replaced):
            return CombinationType.TRIO

        elif Combination.is_sqarebomb(self._cards):
            return CombinationType.SQUAREBOMB

        elif Combination.is_fullhouse(self._cards_with_phoenix_replaced):
            return CombinationType.FULLHOUSE

        elif Combination.is_straightbomb(self._cards):  # Important: bomb test before straight test.
            return CombinationType.STRAIGHTBOMB

        elif Combination.is_straight(self._cards_with_phoenix_replaced):
            return CombinationType.STRAIGHT

        return None

    def _init_height(self):
        if self._comb_type is CombinationType.FULLHOUSE:  # the triple counts.
            # TODO improvement, make nicer
            counts = defaultdict(lambda: 0)
            for c in self._cards:
                counts[c] += 1
            for c in counts:
                if counts[c] == 3:
                    return self._comb_type.numeric_value + c.card_height
            raise LogicError("This seems not to be a FULLHOUSE")

        if self._comb_type is CombinationType.STRAIGHT or self._comb_type is CombinationType.STRAIGHTBOMB:
            # a straight is strictly higher if it is longer.
            # combination value + length (-5 because it is at least 5 long) + height of lowest card
            assert len(self._cards) >= 5
            return self._comb_type.numeric_value + 20 * (len(self._cards) - 5) + min(self._cards, key=lambda x: x.card_height).card_height

        else:  # in all other cases, the highest card counts.
            return self._comb_type.numeric_value + max(self._cards, key=lambda x: x.card_height).card_height

    def __repr__(self):
        return "Combination({}, {}, {})".format(repr(self.type), repr(self.height), repr(self._cards))

    def __lt__(self, other):
        # TODO Test!!
        """
        :param other: The Combination to compare to
        :return: True iff this Combination is considered strictly smaller than the other Combination.
        :raise TypeError, ValueError: When the Combinations can't be compared.
        IMPORTANT: Phoenix on left hand side is always smaller, but phoenix on right hand side is always bigger.
        So 'Phoenix < single card' is always True, but 'single card < Phoenix' is also always True.
        """

        cant_compare_ex = ValueError("Can't compare {} to {}.".format(self.__repr__(), other.__repr__()))

        # TODO, speed, change all ... in {...} to is ... or ... is ... or...

        if self.__class__ is not other.__class__:  # assures both are Combinations.
            raise TypeError("Can't compare {} to {}, must be the same class".format(self.__repr__(), other.__repr__()))

        elif self.type is CombinationType.DOG or other.type is CombinationType.DOG:
            raise TypeError("Can't compare {} to {}, Dog can't be compared to any other combination.".format(self.__repr__(), other.__repr__()))

        elif self.is_bomb() and other.is_bomb():
            # same type -> height decides; self is SQUAREBOMB other is STRAIGHTBOMB -> True; self is STRAIGHTBOMB other is SQUAREBOMB -> False
            return self.height < other.height if self.type is other.type else self.type is CombinationType.SQUAREBOMB

        elif self.is_bomb() and not other.is_bomb():
            return False

        elif not self.is_bomb() and other.is_bomb():
            return True

        elif self.type is CombinationType.SINGLE_MAHJONG:
            return other.type in {CombinationType.SINGLE_PHOENIX, CombinationType.SINGLE_CARD, CombinationType.DRAGON} or other.is_bomb() or raiser(cant_compare_ex)

        elif self.type is CombinationType.SINGLE_PHOENIX:
            return (False if other.type is CombinationType.SINGLE_MAHJONG else
                    True if other.type is CombinationType.SINGLE_CARD or other.type is CombinationType.DRAGON
                    else raiser(cant_compare_ex))

        elif self.type is CombinationType.SINGLE_CARD:
            return (self.height < other.height if other.type is CombinationType.SINGLE_CARD else
                    False if other.type is CombinationType.SINGLE_MAHJONG else
                    True if other.type is CombinationType.DRAGON or other.type is CombinationType.SINGLE_PHOENIX
                    else raiser(cant_compare_ex))

        elif self.type is CombinationType.DRAGON:
            return (False if other.type in {CombinationType.SINGLE_CARD, CombinationType.SINGLE_PHOENIX, CombinationType.SINGLE_MAHJONG}
                    else raiser(cant_compare_ex))

        elif self.type is CombinationType.PAIR or self.type is CombinationType.TRIO or self.type is CombinationType.FULLHOUSE:
            return self.height < other.height if other.type is self.type else raiser(cant_compare_ex)

        elif self.type is CombinationType.PAIR_STEPS or self.type is CombinationType.STRAIGHT:
            return self.height < other.height if other.type is self.type and len(self) == len(other) else raiser(cant_compare_ex)

    def __le__(self, other):
        return self.__lt__(other) or self.__eq__(other)

    def __ge__(self, other):
        return self.__gt__(other) or self.__eq__(other)

    def __gt__(self, other):
        return not self.__le__(other)

    def __len__(self):
        return len(self._cards)

    @staticmethod
    def is_dog(cards):
        return len(cards) == 1 and Card.DOG in cards

    @staticmethod
    def is_single_mahjong(cards):
        return len(cards) == 1 and Card.MAHJONG in cards

    @staticmethod
    def is_single_phoenix(cards):
        return len(cards) == 1 and Card.PHOENIX in cards

    @staticmethod
    def is_single_dragon(cards):
        return len(cards) == 1 and Card.DRAGON in cards

    @staticmethod
    def is_single(cards):
        return (len(cards) == 1
                and not Combination.is_dog(cards)
                and not Combination.is_single_mahjong(cards)
                and not Combination.is_single_phoenix(cards)
                and not Combination.is_single_dragon(cards))

    @staticmethod
    def is_pair(cards):
        return len(cards) == 2 and Combination.all_same_cardvalue(cards)

    @staticmethod
    def is_trio(cards):
        return len(cards) == 3 and Combination.all_same_cardvalue(cards)

    @staticmethod
    def is_sqarebomb(cards):
        return len(cards) == 4 and Combination.all_same_cardvalue(cards)

    @staticmethod
    def all_same_cardvalue(cards):
        """
        :param cards: Iterable; containing only Card instances
        :return: true if all cards have the same card_value.
        """
        it = iter(cards)
        reference_cardvalue = next(it).card_value
        return all([c.card_value == reference_cardvalue for c in it])

    @staticmethod
    def is_fullhouse(cards):
        if len(cards) != 5:
            return False
        sorted_cards = sorted(cards)
        return ((Combination.is_pair(sorted_cards[0:2]) and Combination.is_trio(sorted_cards[2:]))
                or (Combination.is_pair(sorted_cards[3:]) and Combination.is_trio(sorted_cards[0:3])))

    @staticmethod
    def is_pair_step(cards):
        if len(cards) < 4 or len(cards) % 2 == 1:  # must be an even number of cards, and at least 4 cards.
            return False
        sorted_cards = sorted(cards)
        k = 0
        while k < len(sorted_cards):
            if not Combination.is_pair(sorted_cards[k:k + 2]):
                return False
            k += 2
        return True

    @staticmethod
    def is_straight(cards):
        if len(cards) < 5 or Card.DOG in cards or Card.DRAGON in cards:
            return False
        # all different cardvalues:
        if len(set([c.card_value for c in cards])) != len(cards):
            return False
        # all card heights are consecutive #TODO speed, can be speed up, but probably not worth it.
        cardrange = range(min(cards, key=lambda e: e.height), max(cards, key=lambda e: e.height))
        return all([(c.height in cardrange) for c in cards])

    @staticmethod
    def is_straightbomb(cards):
        suit = next(iter(cards)).suit
        return Combination.is_straight and all([c.suit == suit for c in cards])


class Deck(Cards):
    def __init__(self, full=True, cards=list()):
        """
        full: if True, the argument cards is ignored and a full deck is created. Default is True
        cards: The cards initially in the Deck. Ignored when 'full=True'
        """
        if full:
            cards_to_add = [
                Card.PHOENIX, Card.DRAGON, Card.MAHJONG, Card.DOG,
                Card.TWO_JADE, Card.THREE_JADE, Card.FOUR_JADE, Card.FIVE_JADE, Card.SIX_JADE, Card.SEVEN_JADE,
                Card.EIGHT_JADE, Card.NINE_JADE, Card.TEN_JADE, Card.J_JADE, Card.Q_JADE, Card.K_JADE, Card.A_JADE,
                Card.TWO_HOUSE, Card.THREE_HOUSE, Card.FOUR_HOUSE, Card.FIVE_HOUSE, Card.SIX_HOUSE, Card.SEVEN_HOUSE,
                Card.EIGHT_HOUSE, Card.NINE_HOUSE, Card.TEN_HOUSE, Card.J_HOUSE, Card.Q_HOUSE, Card.K_HOUSE,
                Card.A_HOUSE,
                Card.TWO_SWORD, Card.THREE_SWORD, Card.FOUR_SWORD, Card.FIVE_SWORD, Card.SIX_SWORD, Card.SEVEN_SWORD,
                Card.EIGHT_SWORD, Card.NINE_SWORD, Card.TEN_SWORD, Card.J_SWORD, Card.Q_SWORD, Card.K_SWORD,
                Card.A_SWORD,
                Card.TWO_PAGODA, Card.THREE_PAGODA, Card.FOUR_PAGODA, Card.FIVE_PAGODA, Card.SIX_PAGODA,
                Card.SEVEN_PAGODA, Card.EIGHT_PAGODA, Card.NINE_PAGODA, Card.TEN_PAGODA, Card.J_PAGODA, Card.Q_PAGODA,
                Card.K_PAGODA, Card.A_PAGODA
            ]
        else:
            cards_to_add = list(cards)

        super().__init__(cards_to_add)

    def split(self, nbr_piles=4, random_=True):
        """
        :param nbr_piles: Splits the deck into 'nbr_piles' same sized piles (defualt is 4).
        The size of the deck must be divisible by nbr_piles.
        :param random_: If random is True, the cards will be distributed randomly over the piles.
        :return a list (of length 'nbr_piles') of lists of 'Card' instances.
        """
        if len(self._cards) % nbr_piles != 0:
            raise ValueError(
                    "The decks size ({}) must be divisible by 'nbr_piles' ({}).".format(len(self._cards), nbr_piles))
        pile_size = int(len(self._cards) / nbr_piles)
        cards_to_distribute = list(self._cards)
        if random_:
            rnd.shuffle(cards_to_distribute)
        pile_list = []
        for k in range(pile_size):
            pile_list.append(list(cards_to_distribute[k:k + pile_size]))
        return pile_list
