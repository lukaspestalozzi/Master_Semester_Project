from enum import Enum

__author__ = 'Lukas Pestalozzi'
__all__ = ['CardValue', 'CardSuit', 'Card']


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
            return self.value >= other.value
        self._raise_cant_compare(other)

    def __gt__(self, other):
        if self.__class__ is other.__class__:
            return self.value > other.value
        self._raise_cant_compare(other)

    def __le__(self, other):
        if self.__class__ is other.__class__:
            return self.value <= other.value
        self._raise_cant_compare(other)

    def __lt__(self, other):
        if self.__class__ is other.__class__:
            return self.value < other.value
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
        if self.value == 5:
            self._points = 5
        elif self.value in [10, 13]:
            self._points = 10
        elif self.value == 15:
            self._points = 25
        elif self.value == 1.5:
            self._points = -25
        else:
            self._points = 0

        self._repr = "CardValue({} {})".format(self.name, self.value)
        self._str = (self.name if self.value > 10 or self.value in {15, 1.5, 1, 0}
                     else str(self.value))

    @property
    def height(self):
        return self.value

    @property
    def points(self):
        return self._points

    def __repr__(self):
        return self._str

    def __str__(self):
        return self._str


class CardSuit(ComparableEnum):
    SWORD = u'\u2660'
    PAGODA = u'\u2665'
    HOUSE = u'\u2666'
    JADE = u'\u2663'
    SPECIAL = u'\u1f0cf'

    def __init__(self, unicode):
        self._value_ = self._name_
        self._unicode = unicode
        self._shortname = self._name_[:2]
        self._repr = "Suit({})".format(self.name)

    @property
    def unicode(self):
        return self._unicode

    @property
    def shortname(self):
        return self._shortname

    def __unicode__(self):
        return self._unicode

    def  pretty_string(self):
        return self._unicode

    def __repr__(self):
        return self._repr

    def __str__(self):
        return self.unicode


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

        # precompute strings and hashe
        self._hash = hash((cardvalue, cardsuit))
        self._str = ("{}{}".format(str(self._cardvalue), self._suit.pretty_string()) if self._suit is not CardSuit.SPECIAL
                     else "{}".format(str(self._cardvalue)))
        self._repr = "Card({}, {})".format(repr(self._cardvalue), repr(self._suit))

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
    def points(self):
        return self._cardvalue.points

    def __eq__(self, other):  # TODO question, raise error when classes not the same?
        return self.__class__ is other.__class__ and self.card_value == other.card_value and self._suit == other.suit

    def __ne__(self, other):
        return not self.__eq__(other)

    def __repr__(self):
        return self._str

    def __str__(self):
        return self._str

    def __hash__(self):
        return self._hash
