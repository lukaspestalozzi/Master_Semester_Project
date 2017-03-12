from collections import abc as collectionsabc
import abc
from collections import defaultdict
from enum import Enum

import itertools

from tichu.cards.card import Card, CardSuit
from tichu.cards.partition import Partition
from tichu.exceptions import LogicError
from tichu.utils import raiser, assert_, try_ignore

__author__ = 'Lukas Pestalozzi'


class ImmutableCards(collectionsabc.Collection):
    _card_val_to_sword_card = {
        2: Card.TWO_SWORD,
        3: Card.THREE_SWORD,
        4: Card.FOUR_SWORD,
        5: Card.FIVE_SWORD,
        6: Card.SIX_SWORD,
        7: Card.SEVEN_SWORD,
        8: Card.EIGHT_SWORD,
        9: Card.NINE_SWORD,
        10: Card.TEN_SWORD,
        11: Card.J_SWORD,
        12: Card.Q_SWORD,
        13: Card.K_SWORD,
        14: Card.A_SWORD,
    }

    def __init__(self, cards):
        """
        :param cards: An iterable containing Card instances or another Card instance.
        """
        if isinstance(cards, ImmutableCards):
            self._cards = frozenset(cards.cards_list)
        elif all([isinstance(c, Card) for c in cards]):
            self._cards = frozenset(cards)
        else:
            raise TypeError("Only instances of 'Card' can be put into 'Cards'.")

        assert len(self._cards) == len(cards)  # make sure no card is 'lost' due to duplicated cards in 'cards'
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

    def copy(self):
        """

        :return: copy of this ImmutableCards instance
        """
        return ImmutableCards(self._cards)

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
        # TODO test
        # remove PHOENIX
        no_phoenix_cards = [c for c in self._cards if c is not Card.PHOENIX]

        # replace Phoenix once with all cards not in cards
        # TODO handle phoenix

        # store 'all single' partition
        final_partitions = set()
        open_partitions = set()
        open_partitions.add(Partition([Combination([c]) for c in no_phoenix_cards]))

        done = {}

        # repeat "evolve" until no new partitions are generated
        while len(open_partitions) > 0:  # for pton in final_partitions:
            pton = open_partitions.pop()
            if pton not in done:
                res = pton.evolve()
                if len(res) > 0:
                    open_partitions.update(res)
                done[pton] = res
            final_partitions.add(pton)  # TODO question, can be put in if clause?

        return final_partitions

    def value_dict(self):
        """
        :return: a dict mapping the card_values appearing in self._cards to the list of corresponding cards.
        """
        # TODO precompute, -> must be overridden by mutable subclasses
        val_dict = defaultdict(lambda: [])
        for c in self._cards:
            val_dict[c.card_value].append(c)
        return val_dict

    # TODO cache the results -> (only in immutable cards)

    def all_bombs(self):
        return self.all_squarebombs().union(self.all_straightbombs())

    def all_squarebombs(self):
        squares = set()
        for l in self.value_dict():
            if len(l) == 4:
                squares.add(SquareBomb(l))
        return squares

    def all_straightbombs(self):
        s_bombs = set()
        for st in self.all_straights(ignore_phoenix=True):
            sb = try_ignore(lambda: StraightBomb(st))
            s_bombs.add(sb) if sb else None  # one line :)
        return s_bombs

    def all_pairs(self, ignore_phoenix=False):
        # TODO speed, sort and then iterate? probably not worth it.
        pairs = set()
        if not ignore_phoenix and Card.PHOENIX in self._cards:
            for c in self._cards:
                pairs.add(Pair(c, Card.PHOENIX))

        for c1 in self._cards:
            for c2 in self._cards:
                if c1 is c2:
                    continue
                elif c1.card_value is c2.card_value:
                    pairs.add(Pair(c1, c2))

        return pairs

    def all_trios(self, ignore_phoenix=False):
        # TODO speed, but probably not worth it.
        trios = set()
        if not ignore_phoenix and Card.PHOENIX in self._cards:
            for p in self.all_pairs(ignore_phoenix=True):
                trios.add(Trio(Card.PHOENIX, *p.cards))

        for l in self.value_dict():
            if len(l) == 3:
                trios.add(Combination(l))
            elif len(l) == 4:
                trios.add(Trio(*l[:3]))  # 0, 1, 2
                trios.add(Trio(*l[1:]))  # 1, 2, 3
                trios.add(Trio(*l[2:], *l[:1]))  # 2, 3, 0
                trios.add(Trio(*l[3:], *l[:2]))  # 3, 0, 1

        return trios

    def all_straights(self, length=None, ignore_phoenix=False):
        """

        :param length: Integer (defualt None), If not None, returns only straights of the given length (must be >=5)
        :param ignore_phoenix:
        :return:
        """
        assert_(length is None or length >= 5, ValueError("length must be None or >=5, but was: " + str(length)))

        if len(self._cards) < (5 if length is None else length):  # if not enough cards are available, return empty set
            return set()

        phoenix = not ignore_phoenix and Card.PHOENIX in self._cards
        straights = set()

        def all_straights_rec(remaining, acc_straight, last_height, ph_in_acc=None):
            if length is None and len(acc_straight) >= 5:
                straights.add(Straight(acc_straight, phoenix_as=ph_in_acc))
            elif length is not None and len(acc_straight) == length:
                straights.add(Straight(acc_straight, phoenix_as=ph_in_acc))
                return None  # no longer straights are searched

            if len(remaining) == 0:
                return None

            cc = remaining[0]
            c_height = cc.card_height  # current card height

            # card may be added to straight
            if len(acc_straight) == 0 or c_height == last_height + 1:
                all_straights_rec(remaining[1:], acc_straight + [cc], c_height, ph_in_acc=ph_in_acc)  # take cc

            # same height as last added card
            elif c_height == last_height:
                all_straights_rec(remaining[1:], acc_straight[:-1] + [cc], c_height,
                                  ph_in_acc=ph_in_acc)  # remove last and take cc instead
                all_straights_rec(remaining[1:], acc_straight, last_height, ph_in_acc=ph_in_acc)  # don't take cc

            all_straights_rec(remaining[1:], list(), None, ph_in_acc=None)  # start new straight

            if phoenix and not ph_in_acc and len(
                    acc_straight) > 0 and last_height < 14:  # the phoenix is not yet used and can be used
                # take phoenix instead of any other card
                all_straights_rec(remaining, acc_straight + [Card.PHOENIX], last_height + 1,
                                  ph_in_acc=ImmutableCards._card_val_to_sword_card[last_height + 1])

        s_cards = sorted([c for c in self._cards
                          if c is not Card.PHOENIX
                          and c is not Card.DOG
                          and c is not Card.DRAGON],
                         key=lambda c: c.card_value)

        all_straights_rec(s_cards, list(), None, ph_in_acc=None)

        # append phoenix at the beginning of each straight
        # TODO integrate into recursion (ie, with each new card > 2 start new straight with [phoenix, card]
        phoenix_prepended = set()
        if phoenix:
            for st in straights:
                l_card = st.lowest_card
                if Card.PHOENIX not in st and l_card.card_height > 2:
                    phoenix_prepended.add(Straight([Card.PHOENIX] + st.cards_list,
                                                      phoenix_as=ImmutableCards._card_val_to_sword_card[
                                                          l_card.card_height - 1]))
            straights.update(phoenix_prepended)

        return straights

    def all_fullhouses(self, ignore_phoenix=False):
        pairs = self.all_pairs(ignore_phoenix=ignore_phoenix)
        trios = self.all_trios(ignore_phoenix=ignore_phoenix)
        fullhouses = set()
        for t in trios:
            for p in pairs:
                if not (t.contains_phoenix() and p.contains_phoenix()):  # only one phoenix is allowed
                    fullhouses.add(FullHouse(pair=p, trio=t))
        return fullhouses

    def all_pairsteps(self, ignore_phoenix=False):
        pairs_s = sorted(list(self.all_pairs(ignore_phoenix=ignore_phoenix)))
        # TODO speed, may be faster
        psteps = set()
        new_ps = set()
        # find all pairsteps of length 2
        for p1 in pairs_s:
            for p2 in pairs_s:
                if p1 != p2 and abs(p1.value_height - p2.value_height) == 1:
                    new_ps.add(PairSteps((p1, p2)))

        # find all longer pairsteps
        while len(new_ps):
            ps = new_ps.pop()
            if ps not in psteps:
                for pair in pairs_s:
                    if ps.can_add(pair):
                        new_ps.add(ps.extend(pair))
                psteps.add(ps)

        return psteps

    def all_combinations(self, played_on=None, ignore_phoenix=False):
        """
        :return: a set of all possible combinations appearing in this cards instance
        """
        combs = set()
        if played_on is None:
            combs.update([Combination([c]) for c in self._cards])  # single cards
            combs.update(self.all_bombs())
            combs.update(self.all_pairs(ignore_phoenix=ignore_phoenix))
            combs.update(self.all_trios(ignore_phoenix=ignore_phoenix))
            combs.update(self.all_straights(ignore_phoenix=ignore_phoenix))
            combs.update(self.all_fullhouses(ignore_phoenix=ignore_phoenix))
            combs.update(self.all_pairsteps(ignore_phoenix=ignore_phoenix))
        elif isinstance(played_on, Combination):
            combs.update([b for b in self.all_bombs() if played_on < b])
            if isinstance(played_on, Single):
                combs.update([c for c in self._cards if played_on < c])
            elif isinstance(played_on, Pair):
                combs.update([c for c in self.all_pairs() if played_on < c])
            elif isinstance(played_on, PairSteps):
                combs.update([c for c in self.all_pairsteps() if played_on < c])
            elif isinstance(played_on, Trio):
                combs.update([c for c in self.all_trios() if played_on < c])
            elif isinstance(played_on, Straight):
                combs.update([c for c in self.all_straights(length=len(played_on)) if played_on < c])
            elif isinstance(played_on, FullHouse):
                combs.update([c for c in self.all_fullhouses() if played_on < c])

        return combs

    def __str__(self):
        return type(self).__name__ + self._str

    def __repr__(self):
        return type(self).__name__ + self._repr

    def __len__(self):
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

    def copy(self):
        """
        :return: copy of this Cards instance
        """
        return Cards(self._cards)


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


class Combination_old(object):

    def __init__(self, cards, phoenix_as=None):
        """
        :param cards: an iterable of Card instances.
        :param phoenix_as: Card or None; The card the PHOENIX should represent in the Combination.
        If the phoenix is not in the combination or the phoenix is played alone, this argument is ignored.
        Also, the phoenix can't take on a card already in the combination or any special card.
        """
        has_phoenix = Card.PHOENIX in cards
        if has_phoenix:
            if len(
                    cards) == 1:  # A phoenix played alone is a valid combination. But the phoenix counts 1/2 higher than the last played combination.
                phoenix_as = Card.PHOENIX
            elif phoenix_as is None:
                raise ValueError("When The phoenix appears in the cards, then phoenix_as must be a Card.")
            elif not isinstance(phoenix_as, Card):
                raise ValueError("The phoenix_as must be a Card.")
            elif phoenix_as in cards:
                raise ValueError(
                    "The phoenix can't take on a card already in the combination. \ncards:{} \nphoenix: {}".format(
                        cards, phoenix_as))
            elif phoenix_as.suit is CardSuit.SPECIAL:
                raise ValueError("The phoenix can't take on a special card.")

        super().__init__(cards)
        self._phoenix = phoenix_as if has_phoenix else None
        self._cards_with_phoenix_replaced = frozenset(
            [c for c in self._cards if c is not Card.PHOENIX] + [self._phoenix]) if self._phoenix else self._cards
        self._comb_type = self._find_combination_type()
        if self._comb_type is None:
            raise ValueError("This is no valid combination {}.".format(str(sorted(cards))))
        self._comb_height = self._init_height()
        self._card_value_tuple = tuple(sorted([c.card_value for c in self._cards]))

    @property
    def type(self):
        return self._comb_type

    @property
    def height(self):
        return self._comb_height

    @property
    def short_string(self):
        # TODO precompute
        return "{} ({})".format(self.type,
                                ', '.join(["{}_{}".format(c.card_value.name, c.suit.shortname) for c in self._cards]))

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
            return self._comb_type.numeric_value + 20 * (len(self._cards) - 5) + min(self._cards, key=lambda
                x: x.card_height).card_height

        else:  # in all other cases, the highest card counts.
            return self._comb_type.numeric_value + max(self._cards, key=lambda x: x.card_height).card_height

    def __str__(self):
        # TODO speed, precompute this string
        cards_str = '; '.join([str(c) for c in self._cards])
        return "Comb({}, height:{}, phoenix: {}, cards:[{}])".format(str(self.type.name), str(self.height),
                                                                     str(self._phoenix), cards_str)

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
            raise TypeError(
                "Can't compare {} to {}, Dog can't be compared to any other combination.".format(self.__repr__(),
                                                                                                 other.__repr__()))

        elif self.is_bomb() and other.is_bomb():
            # same type -> height decides; self is SQUAREBOMB other is STRAIGHTBOMB -> True; self is STRAIGHTBOMB other is SQUAREBOMB -> False
            return self.height < other.height if self.type is other.type else self.type is CombinationType.SQUAREBOMB

        elif self.is_bomb() and not other.is_bomb():
            return False

        elif not self.is_bomb() and other.is_bomb():
            return True

        elif self.type is CombinationType.SINGLE_MAHJONG:
            return other.type in {CombinationType.SINGLE_PHOENIX, CombinationType.SINGLE_CARD,
                                  CombinationType.DRAGON} or other.is_bomb() or raiser(cant_compare_ex)

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
            return (False if other.type in {CombinationType.SINGLE_CARD, CombinationType.SINGLE_PHOENIX,
                                            CombinationType.SINGLE_MAHJONG}
                    else raiser(cant_compare_ex))

        elif self.type is CombinationType.PAIR or self.type is CombinationType.TRIO or self.type is CombinationType.FULLHOUSE:
            return self.height < other.height if other.type is self.type else raiser(cant_compare_ex)

        elif self.type is CombinationType.PAIR_STEPS or self.type is CombinationType.STRAIGHT:
            return self.height < other.height if other.type is self.type and len(self) == len(other) else raiser(
                cant_compare_ex)

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
        d = defaultdict(lambda: 0)
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
        cardrange = range(min_height, min_height + len(cards) // 2)
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


class Combination(metaclass=abc.ABCMeta):

    def __init__(self, cards):
        assert_(all((isinstance(card, Card) for card in cards)))
        self._cards = tuple(cards)

    @property
    def cards(self):
        return self._cards

    @abc.abstractproperty
    def height(self):
        raise NotImplementedError()

    @staticmethod
    def make(cards):
        """
        makes a combiantion out of the given cards
        :param cards: the cards
        :return: the Combination
        :raise ValueError: if cards don't make a valid combination
        """
        nbr_cards = len(cards)
        err = None
        try:
            assert_(0 < nbr_cards <= 15)
            if nbr_cards == 1:
                return Single(*cards)

            if nbr_cards == 2:
                return Pair(*cards)

            if nbr_cards == 3:
                return Trio(*cards)

            if nbr_cards == 4:
                return SquareBomb(*cards)

            if nbr_cards % 2 == 0:
                ss = try_ignore(lambda: PairSteps.from_cards(cards))
                if ss:
                    return ss

            if nbr_cards == 5:
                fh = try_ignore(lambda: FullHouse.from_cards(cards))
                if fh:
                    return fh

            if nbr_cards >= 5:
                st = try_ignore(lambda: Straight(cards))
                sb = try_ignore(lambda: StraightBomb(st))
                if sb:
                    return sb
                if st:
                    return st

        except Exception as e:
            err = e
        raise ValueError("Is no combination: {}\ncards: {}".format(err, str(cards)))

    def _cant_compare_error(self, other, raise_=False):
        e = ValueError("Can't compare {} to {}.".format(self.__repr__(), other.__repr__()))
        if raise_:
            raise e
        return e

    def contains_phoenix(self):
        return self.__contains__(Card.PHOENIX)

    def __iter__(self):
        return iter(self._cards)

    def __eq__(self, other):
        return self.__class__ is other.__class__ and self.cards == other.cards

    def __len__(self):
        return len(self._cards)

    def __contains__(self, other):
        return self._cards.__contains__(other)

    def __ne__(self, other):
        return not self.__eq__(other)

    def __le__(self, other):
        return self.__lt__(other) or self.__eq__(other)

    def __ge__(self, other):
        return self.__gt__(other) or self.__eq__(other)

    def __gt__(self, other):
        return not self.__le__(other)

    def __lt__(self, other):
        assert_(isinstance(other, (type(self), Bomb)), self._cant_compare_error(other))
        return self.height < other.height


class Single(Combination):

    def __init__(self, card):
        super().__init__((card, ))
        self._card = card

    @property
    def card(self):
        return self._card

    @property
    def height(self):
        return self._card.card_height

    def __lt__(self, other):
        """
        IMPORTANT: Phoenix on left hand side is always smaller, but phoenix on right hand side is always bigger.
        So 'Phoenix < single card' is always True, but 'single card < Phoenix' is also always True.
        """
        if isinstance(other, Bomb):
            return True
        assert_(isinstance(other, Single), self._cant_compare_error(other))
        assert_(self.card is not Card.DOG and other.card is not Card.DOG)  # dog can't be compared
        if self.card is Card.DRAGON:
            return False  # dragon is the highest single card
        if self._card is Card.PHOENIX or other.card is Card.PHOENIX or other.card is Card.DRAGON or self.card is Card.MAHJONG:
            # Phoenix on left is smaller, phoenix on right is bigger, dragon is always biggest, mahjong is always smallest
            return True
        return self.height < other.height

    def __contains__(self, item):
        return self._card is item


class Pair(Combination):

    def __init__(self, card1, card2):
        assert_(card1 is not card2)  # different cards
        super().__init__((card1, card2))

        if Card.PHOENIX in self._cards:
            if card1 is Card.PHOENIX:
                card1, card2 = card2, card1  # make sure card1 is not Phoenix
            assert_(card1.suit is not CardSuit.SPECIAL)
        else:
            assert_(card1.card_value is card2.card_value)  # same value

        self._height = card1.card_height
        self._card_value = card1.card_value

    @property
    def height(self):
        return self._height


class Trio(Combination):

    def __init__(self, card1, card2, card3):
        assert_(card1 is not card2 and card1 is not card3 and card2 is not card3)  # 3 different cards
        super().__init__((card1, card2, card3))

        if Card.PHOENIX in self._cards:
            if card1 is Card.PHOENIX:
                card1, card2 = card2, card1  # make sure card1 is not Phoenix
            assert_(card1.suit is not CardSuit.SPECIAL)
        else:
            assert_(card1.card_value is card2.card_value is card3.card_value)  # same values

        self._height = card1.card_height
        self._card_value = card1.card_value

    @property
    def height(self):
        return self._height


class FullHouse(Combination):

    def __init__(self, pair, trio):
        assert_(isinstance(pair, Pair))
        assert_(isinstance(trio, Trio))
        assert_(not(pair.contains_phoenix() and trio.contains_phoenix()))  # phoenix can only be used once
        super().__init__(pair.cards + trio.cards)
        self._height = trio.height

    @property
    def height(self):
        return self._height

    @classmethod
    def from_cards(cls, cards):
        assert_(len(cards) == 5)
        pair = None
        trio = None
        for cs in ImmutableCards(cards).value_dict().values():
            if len(cs) == 2:
                pair = Pair(*cs)
            if len(cs) == 3:
                trio = Trio(*cs)
            assert_(len(cs) == 0)
        return cls(pair, trio)


class PairSteps(Combination):

    def __init__(self, pairs):
        assert_(len(pairs) >= 2)
        assert_(all((isinstance(p, Pair) for p in pairs)))
        pairheights = {p.height for p in pairs}
        assert_(len(pairheights) == len(pairs))  # all pairs have different height
        assert_(max(pairheights) - min(pairheights) + 1 == len(pairs))  # pairs are consecutive
        assert_(sum([p.contains_phoenix() for p in pairs]) <= 1)  # phoenix can only be used once

        super().__init__(itertools.chain((p.cards for p in pairs)))
        self._height = max(pairheights)
        self._lowest_pair_height = min(pairheights)
        self._pairs = pairs

    @property
    def height(self):
        return self._height

    @classmethod
    def from_cards(cls, cards):
        assert_(len(cards) >= 4 and len(cards) % 2 == 0)
        pairs = []
        for cs in ImmutableCards(cards).value_dict().values():
            if len(cs) == 2:
                pairs.append(Pair(*cs))
            assert_(len(cs) == 0)
        return cls(pairs)

    def extend(self, pair):
        return PairSteps(self._pairs + [pair])

    def can_add(self, pair):
        return (isinstance(pair, Pair)
                and not(pair.contains_phoenix() and self.contains_phoenix())
                and (pair.height + 1 == self._lowest_pair_height or pair.height - 1 == self._height))

    def __lt__(self, other):
        assert_(len(other) == len(self), self._cant_compare_error(other))
        return super().__lt__(other)


class Straight(Combination):

    def __init__(self, cards, phoenix_as=None):
        assert_(len(cards) >= 5)
        if Card.PHOENIX in cards:
            assert_(isinstance(phoenix_as, Card))
            assert_(phoenix_as not in cards)
            assert_(phoenix_as.suit is not CardSuit.SPECIAL)

        cards_phoenix_replaced = [c for c in cards if c is not Card.PHOENIX] + [phoenix_as]
        assert_(len([c.card_value for c in cards_phoenix_replaced]) == len(cards_phoenix_replaced))  # different card values
        cardheights = [c.card_height for c in cards_phoenix_replaced]
        assert_(max(cardheights) - min(cardheights) + 1 == len(cards_phoenix_replaced))  # cards are consecutive

        super().__init__(cards)
        self._height = max(cardheights)

    @property
    def height(self):
        return self._height

    def __lt__(self, other):
        assert_(len(other) == len(self), self._cant_compare_error(other))
        return super().__lt__(other)


class Bomb(Combination):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class SquareBomb(Bomb):

    def __init__(self, card1, card2, card3, card4):
        super().__init__((card1, card2, card3, card4))
        assert_(len(set(self.cards)) == 4)  # all cards are different
        # all cards have same card_value (takes also care of the phoenix)
        assert_(len({c.card_value for c in self.cards}) == 1)
        self._height = card1.card_height + 500  # 500 to make sure it is higher than any other non bomb combination

    @property
    def height(self):
        return self._height

    @classmethod
    def from_cards(cls, cards):
        return cls(*cards)

    def __lt__(self, other):
        if isinstance(other, StraightBomb):
            return True
        else:
            return self.height < other.height


class StraightBomb(Bomb):

    def __init__(self, straight):
        assert_(isinstance(straight, Straight))
        assert_(len({c.suit for c in straight}) == 1)  # only one suit (takes also care of the phoenix)
        super().__init__(straight.cards)
        self._height = straight.height + 1000  # 1000 to make sure it is higher than any other non straightbomb

    @property
    def height(self):
        return self._height

    @classmethod
    def from_cards(cls, cards):
        return cls(Straight(cards))

    def __lt__(self, other):
        if isinstance(other, StraightBomb):
            if len(self) < len(other):
                return True
            elif len(self) == len(other):
                return self.height < other.height
        return False
