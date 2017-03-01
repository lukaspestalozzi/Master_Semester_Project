from enum import Enum
import random as rnd


__author__ = 'Lukas Pestalozzi'

class ComparableEnum(Enum):
    """
    Enum that allows comparing instances with >, >=, <=, <
    """
    # functions to compare the enum
    def _raise_cant_compare(self, other):
        raise TypeError("operation not supported between instances of {} and {}.".format(self.__class__, other.__class__))

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

    def points(self):
        if self.value == 5:
            return 5
        elif self.value in [10, 13]:
            return 10
        elif self.value == 15:
            return 25
        elif self.value == 1.5:
            return -25
        else:
            return 0

    def __repr__(self):
        return "{}({})".format(self.name, self.value)


class CardSuit(Enum):
    SWORD = ('Black')
    PAGODA = ('Red')
    HOUSE = ('Blue')
    JADE = ('Green')
    SPECIAL = ('Yellow')
    UNKNOWN = ('Unknown')

    def __init__(self, color):
        self._value_ = self._name_
        self._color = color

    @property
    def color(self):
        return self._color

    def __repr__(self):
        return "Suit {}({})".format(self.name, self._color)

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
        self._val = cardvalue
        self._color = cardsuit.color
        self._value_ = self._val # TODO rename value to cardvalue or similar

    @property
    def suit(self):
        return self._suit

    @property
    def color(self):
        return self._color

    def points(self):
        return self._val.points()

    def __eq__(self, other):
        return self.__class__ is other.__class__ and self._val == other._val and self._suit == other._suit

    def __ne__(self, other):
        return self.__class__ is other.__class__ and (self._val != other._val or self._suit != other._suit)

    def __repr__(self):
        return "Card({}, {})".format(repr(self._val), repr(self._suit))

class Cards():
    """
    An immutable list (tuple) of Cards with some helpful functions.

    The operation '-' (subtraction) can be understood as a 'remove all' function. So (0, 1, 2, 3) - (2, 3, 4) = (0, 1)
    """

    def __init__(self, cards):
        if all([isinstance(c, Card) for c in cards]):
            self._cards = tuple(cards)
        else:
            raise ValueError("Only instances of 'Card' can be put into 'Cards'.")

    def count_points(self):
        """
        Returns the Tichu points in this set of cards.
        """
        return sum([c.points() for c in self._cards])

    def __add__(self, other):
        """
        Returns a new Cards instance containing both card lists appended to each other.
        """
        if other.__class__ is self.__class__:
            return Cards(self._cards + other._cards)
        else:
            raise TypeError("Can't add (+) a Type {} to {}".format(other.__class__, self.__class__))

    def __sub__(self, other):
        # IMPROVE make more efficient
        """
        Returns a new Cards instance with all elements in other removed from this instance.
        """
        if other.__class__ is self.__class__:
            new_l = []
            for oe in other._cards:
                if oe not in self._cards:
                    new_l.append(oe)
            return Cards(new_l)
        else:
            raise TypeError("Can't subtract (-) a Type {} from {}".format(other.__class__, self.__class__))

    def __repr__(self):
        return "Cards[{}]".format(', '.join([c for c in self._cards]))

    def __str__(self):
        return self.__repr__()

    def __eq__(self, other):
        if self.__class__ is other.__class__:
            return self._cards == other._cards
        raise TypeError("Can't compare a {} to {}".format(self.__class__, other.__class__))

    def __hash__(self):
        return hash(self._cards)

    def __len__(self):
        return len(self._cards)

    def __length_hint__(self):
        return len(self._cards)

    def __getitem__(self, key):
        return self._cards.__getitem__(key)

    def __iter__(self):
        return self._cards.__iter__()

    def __reversed__(self):
        return Cards(reversed(list(self._cards)))

    def __contains__(self, item):
        return self._cards.__contains__(item)


class CombinationType(ComparableEnum):
    PASS = 0 # no card
    SINGLE = 1 # single card
    PAIR = 2 # two cards with same value
    TRIO = 3 # three cards with same value
    FULLHOUSE = 5 # a Pair and a Trio
    PAIR_STEPS = 6 # 2 or more consecutive Pairs
    STRAIGHT = 7 # 5 or more consecutive cards
    SQUAREBOMB = 8 # four cards with same value
    STRAIGHTBOMB = 9 # 5 or more consecutive cards with the same suit

class Combination(Cards):
    # TODO handle PHOENIX
    # TODO define combination value (hight of combination)
    # TODO make combinations comparable.
    bomb_types = frozenset([CombinationType.SQUAREBOMB, CombinationType.STRAIGHTBOMB])

    def __init__(self, cards):
        self._comb_type = Combination.is_combination(cards)
        if self._comb_type is not None:
            super().__init__(cards)
            self._comb_value = self._init_value()
        else:
            raise ValueError("{} is no valid combination.".format(str(cards)))

    @property
    def type(self):
        return self._comb_type

    @property
    def value(self):
        return self._comb_type

    def _init_value(self):
        if self._comb_type is CombinationType.PASS:
            return 0
        elif self._comb_type is CombinationType.FULLHOUSE: # the tripple counts.
            counts = defaultdict(lambda: 0)
            for c in self._cards:
                counts[c] += 1
            for k in counts:
                if counts[k] == 3:
                    return 1000*self._comb_type.value + k.value.value
            raise LogicError("This seems not to be a FULLHOUSE")

        elif self._comb_type is CombinationType.STRAIGHT or self._comb_type is CombinationType.STRAIGHTBOMB:
            # a straight is strictly higher if it is longer.
            return 1000*self._comb_type.value + 100*(len(self._cards)-4) + max(self._cards).value.value

        else: # in all other cases, the highest card counts.
            return 1000*self._comb_type.value + max(self._cards).value.value

    def __repr__(self):
        return "Combination({}, {}, {})".format(repr(self._comb_type), repr(self._comb_value), repr(self._cards))


    def __lt__(self, other):
        if all([
            self.__class__ is other.__class__, # must be same class
            self.type is other.type or self.type is in self.bomb_types or other.type is in self.bomb_types, # must be same type or one must be a bomb
            (self.type is not CombinationType.STRAIGHT and self.type is not CombinationType.PAIR_STEPS) or len(self._cards) == len(other._cards) # if a straight or pairsteps, then the number of cards must be the same
        ]):
            return self.value < other.value
        else:
            raise ValueError("Can't compare {} to {}".format(self.__repr__(), other.__repr__()))

    def __le__(self, other):
        return self.__lt__(other) or self.__eq__(other)

    def __ge__(self, other):
        return self.__gt__(other) or self.__eq__(other)

    def __gt__(self, other):
        return not self.__le__(other)

    @staticmethod
    def is_single(cards):
        return len(cards) == 1 and Card.DOG not in cards

    @staticmethod
    def is_pair(cards):
        return len(cards) == 2 and cards[0].value == cards[1].value

    @staticmethod
    def is_trio(cards):
        return len(cards) == 3 and cards[0].value == cards[1].value == cards[2].value

    @staticmethod
    def is_fullhouse(cards):
        if len(cards) != 5:
            return False
        sorted_cards = sorted(cards)
        return (is_pair(cards[0:2]) and is_trio(cards[2:])) or (is_pair(cards[3:]) and is_trio(cards[0:3]))

    @staticmethod
    def is_sqarebomb(cards):
        return len(cards) == 4 and cards[0].value == cards[1].value == cards[2].value == cards[3].value

    @staticmethod
    def is_pair_step(cards):
        if len(cards) < 4 or len(cards) % 2 == 1:
            return False
        sorted_cards = sorted(cards)
        k = 0
        while k < len(sorted_cards):
            if not Combination.is_pair(sorted_cards[k:k+2]):
                return False
            k += 2
        return True

    @staticmethod
    def is_straight(cards):
        if len(cards) < 5 or Card.DOG in cards or Card.DRAGON in cards:
            return False
        sorted_cards = sorted(cards)
        prev_val = sorted_cards[0].value.value
        for k in range(1, len(cards)):
            if prev_val + 1 != sorted_cards[k].value.value:
                return False
        return True

    @staticmethod
    def is_straightbomb(cards):
        suit = cards[0].suit
        return Combination.is_straight and all([c.suit == suit for c in cards])

    @staticmethod
    def is_combination(cards):
        # TODO improvement: test only possible combinations depending on len(cards)
        """
        cards: must be a Cards instance or a list containing only Card instances
        Returns None if the cards don't constitute a valid Combination
        Otherwise, returns the CombinationType.
        """
        if len(cards) == 0:
            return PASS

        elif Card.DOG in cards and len(cards) > 1: # dog must be alone
            return None

        elif Combination.is_single(cards):
            return CombinationType.SINGLE

        elif Combination.is_pair(cards):
            return CombinationType.PAIR

        elif Combination.is_trio(cards):
            return CombinationType.TRIO

        elif Combination.is_sqarebomb(cards):
            return CombinationType.SQUAREBOMB

        elif Combination.is_fullhouse(cards):
            return CombinationType.FULLHOUSE

        elif Combination.is_pair_step(cards):
            return CombinationType.PAIR_STEPS

        elif Combination.is_straightbomb(cards): # Important: bomb test before straight test.
            return CombinationType.STRAIGHTBOMB

        elif Combination.is_straight(cards):
            return CombinationType.STRAIGHT

        return None

class Trick(tuple):
    """ Immutable List of Cards instances """
    # TODO IMPORTANT!

    def is_empty(self):
        #TODO implement

    def add(self, combination): # QUESTION maybe add player that played it too
        #TODO implement

    def is_dragon_trick(self):
        # TODO

class Deck(Cards):

    def __init__(self, full=True, cards=[]):
        """
        full: if True, the argument cards is ignored and a full deck is created. Default is True
        cards: The cards initially in the Deck. Ignored when 'full=True'
        """
        if full:
            cards_to_add = [
                Card.DRAGON, Card.PHOENIX, Card.MAHJONG, Card.DOG,
                Card.TWO_JADE, Card.THREE_JADE, Card.FOUR_JADE, Card.FIVE_JADE, Card.SIX_JADE, Card.SEVEN_JADE, Card.EIGHT_JADE, Card.NINE_JADE, Card.TEN_JADE, Card.J_JADE, Card.Q_JADE, Card.K_JADE, Card.A_JADE,
                Card.TWO_HOUSE, Card.THREE_HOUSE, Card.FOUR_HOUSE, Card.FIVE_HOUSE, Card.SIX_HOUSE, Card.SEVEN_HOUSE, Card.EIGHT_HOUSE, Card.NINE_HOUSE, Card.TEN_HOUSE, Card.J_HOUSE, Card.Q_HOUSE, Card.K_HOUSE, Card.A_HOUSE,
                Card.TWO_SWORD, Card.THREE_SWORD, Card.FOUR_SWORD, Card.FIVE_SWORD, Card.SIX_SWORD, Card.SEVEN_SWORD, Card.EIGHT_SWORD, Card.NINE_SWORD, Card.TEN_SWORD, Card.J_SWORD, Card.Q_SWORD, Card.K_SWORD, Card.A_SWORD,
                Card.TWO_PAGODA, Card.THREE_PAGODA, Card.FOUR_PAGODA, Card.FIVE_PAGODA, Card.SIX_PAGODA, Card.SEVEN_PAGODA, Card.EIGHT_PAGODA, Card.NINE_PAGODA, Card.TEN_PAGODA, Card.J_PAGODA, Card.Q_PAGODA, Card.K_PAGODA, Card.A_PAGODA
            ]
        else:
            cards_to_add = list(cards)

        super().__init__(cards_to_add)

    def split(self, nbr_piles=4, random=True):
        """
        nbr_piles: Splits the deck into 'nbr_piles' same sized piles (defualt is 4).
        The size of the deck must be divisible by nbr_piles.
        random: If random is True, the cards will be distributed randomly over the piles.
        Returns a list of 'Cards' of length 'nbr_piles'.
        """
        if len(self._cards) % nbr_piles != 0:
            raise ValueError("The decks size ({}) must be divisible by 'nbr_piles' ({}).".format(len(self._cards), nbr_piles))
        pile_size = int(len(self._cards) / nbr_piles)
        cards_to_distribute = self._cards if not random else rnd.shuffle(list(self._cards))
        pile_list = []
        for k in range(pile_size):
            pile_list.append(Cards(list(cards_to_distribute[k:k+pile_size])))
        return pile_list
