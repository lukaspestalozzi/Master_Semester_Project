from collections import defaultdict
from enum import Enum

from game.cards.card import Card
from game.cards.card import CardSuit
from game.cards.cards import ImmutableCards
from game.exceptions import LogicError
from game.utils import raiser


class CombinationType(Enum):
    DOG = 0  # Dog (must be played alone, can't be compared to any other card)
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

    def __str__(self):
        return self.name

    def __repr__(self):
        return "CombinationType({}({}))".format(self.name, self.value)


class Combination(ImmutableCards):

    def __init__(self, cards, phoenix_as=None):
        """
        :param cards: an iterable of Card instances.
        :param phoenix_as: Card or None; The card the PHOENIX should represent in the Combination.
        If the phoenix is not in the combination or the phoenix is played alone, this argument is ignored.
        Also, the phoenix can't take on a card already in the combination or any special card.
        """
        has_phoenix = Card.PHOENIX in cards
        if has_phoenix:
            if len(cards) == 1:   # A phoenix played alone is a valid combination. But the phoenix counts 1/2 higher than the last played combination.
                phoenix_as = Card.PHOENIX
            elif phoenix_as is None:
                raise ValueError("When The phoenix appears in the cards, then phoenix_as must be a Card.")
            elif not isinstance(phoenix_as, Card):
                raise ValueError("The phoenix_as must be a Card.")
            elif phoenix_as in cards:
                raise ValueError("The phoenix can't take on a card already in the combination.")
            elif phoenix_as.suit is CardSuit.SPECIAL:
                raise ValueError("The phoenix can't take on a special card.")

        super().__init__(cards)
        self._phoenix = phoenix_as if has_phoenix else None
        self._cards_with_phoenix_replaced = frozenset([c for c in self._cards if c is not Card.PHOENIX] + [self._phoenix]) if self._phoenix else self._cards
        self._comb_type = self._find_combination_type()
        if self._comb_type is None:
            raise ValueError("This is no valid combination {}.".format(str(cards)))
        self._comb_height = self._init_height()
        self._card_value_tuple = tuple(sorted([c.card_value for c in self._cards],
                                              key=lambda x: x.card_value))

    @property
    def type(self):
        return self._comb_type

    @property
    def height(self):
        return self._comb_height

    @property
    def short_string(self):
        # TODO precompute
        return "{} ({})".format(self.type, ', '.join(["{}_{}".format(c.card_value.name, c.suit.shortname) for c in self._cards]))

    @property
    def card_value_tuple(self):
        return self._card_value_tuple

    def is_bomb(self):
        return self.type is CombinationType.SQUAREBOMB or self.type is CombinationType.STRAIGHTBOMB

    def contains_phoenix(self):
        return bool(self._phoenix)

    def _find_combination_type(self):
        """
        :return the CombinationType of this combination. if the cards don't constitute a valid Combination returns None
        """
        nbr_cards = len(self._cards_with_phoenix_replaced)

        if nbr_cards == 0 or nbr_cards > 15:
            return None

        if nbr_cards == 1:
            if Card.DOG in self._cards:
                return CombinationType.DOG

            elif Card.MAHJONG in self._cards:
                return CombinationType.SINGLE_MAHJONG

            elif Card.PHOENIX in self._cards:
                return CombinationType.SINGLE_PHOENIX

            elif Card.DRAGON in self._cards:
                return CombinationType.DRAGON

            else:
                return CombinationType.SINGLE_CARD

        if nbr_cards == 2 and Combination.all_same_cardvalue(self._cards_with_phoenix_replaced):
            return CombinationType.PAIR

        if nbr_cards == 3 and Combination.all_same_cardvalue(self._cards_with_phoenix_replaced):
            return CombinationType.TRIO

        if nbr_cards >= 5:
            if Combination.is_straight(self._cards_with_phoenix_replaced):
                suit = next(iter(self._cards_with_phoenix_replaced)).suit
                for c in self._cards_with_phoenix_replaced:
                    if c.suit is not suit:
                        return CombinationType.STRAIGHT
                return CombinationType.STRAIGHTBOMB

        if nbr_cards == 5 and Combination.is_fullhouse(self._cards_with_phoenix_replaced):
            return CombinationType.FULLHOUSE

        if nbr_cards % 2 == 0:
            if Combination.is_pair_step(self._cards_with_phoenix_replaced):
                return CombinationType.PAIR_STEPS

        if nbr_cards == 4 and Combination.all_same_cardvalue(self._cards_with_phoenix_replaced):
            return CombinationType.SQUAREBOMB

        return None

    def _init_height(self):
        if self._comb_type is CombinationType.DOG:
            return 0
        if self._comb_type is CombinationType.FULLHOUSE:  # the triple counts.
            # TODO improvement, make nicer
            counts = defaultdict(lambda: 0)
            for c in self._cards:
                counts[c.card_value] += 1
            for cv in counts:
                if counts[cv] == 3:
                    return self._comb_type.numeric_value + cv.height
            raise LogicError("This seems not to be a FULLHOUSE: {}.".format(self._cards))

        if self._comb_type is CombinationType.STRAIGHT or self._comb_type is CombinationType.STRAIGHTBOMB:
            # a straight is strictly higher if it is longer.
            # combination value + length (-5 because it is at least 5 long) + height of lowest card
            assert len(self._cards) >= 5
            return self._comb_type.numeric_value + 20 * (len(self._cards) - 5) + min(self._cards, key=lambda x: x.card_height).card_height

        else:  # in all other cases, the highest card counts.
            return self._comb_type.numeric_value + max(self._cards, key=lambda x: x.card_height).card_height

    def __str__(self):
        # TODO speed, precompute this string
        cards_str = '; '.join([str(c) for c in self._cards])
        return "Comb({}, height:{}, phoenix: {}, cards:[{}])".format(str(self.type.name), str(self.height), str(self._phoenix), cards_str)

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
        d = defaultdict(lambda : 0)
        for c in cards:
            d[c.card_value] += 1
        return len(d) == 2 and 2 in d.values() and 3 in d.values()

    @staticmethod
    def is_pair_step(cards):
        if len(cards) < 4 or len(cards) % 2 == 1:  # must be an even number of cards, and at least 4 cards.
            return False
        sorted_cards = sorted(cards)
        k = 0
        min_height = min([c.card_height for c in cards])
        cardrange = range(min_height, min_height + len(cards)//2)
        while k < len(sorted_cards):
            if (sorted_cards[k].card_height not in cardrange
                    or not Combination.is_pair(sorted_cards[k:k + 2])):
                return False
            k += 2
        return True

    @staticmethod
    def is_straight(cards):
        if len(cards) < 5 or Card.DOG in cards or Card.DRAGON in cards or Card.PHOENIX in cards:
            return False
        # all different cardvalues:
        if len(set([c.card_value for c in cards])) != len(cards):
            return False

        # cards are consecutive
        cardheights = [c.card_height for c in cards]
        return max(cardheights) - min(cardheights) + 1 == len(cards)

    @staticmethod
    def is_straightbomb(cards):
        suit = next(iter(cards)).suit
        return Combination.is_straight(cards) and all([c.suit == suit for c in cards])



