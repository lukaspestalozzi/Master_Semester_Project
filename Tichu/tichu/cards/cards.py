import random
import uuid
from collections import abc as collectionsabc
import abc
from collections import defaultdict

import itertools

import logging

from tichu.cards.card import Card, CardSuit, CardValue
from tichu.utils import assert_, try_ignore

__author__ = 'Lukas Pestalozzi'
__all__ = ['ImmutableCards', 'Cards', 'Combination',
           'Single', 'Pair', 'Trio', 'SquareBomb', 'Straight', 'StraightBomb', 'PairSteps', 'FullHouse']


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

        self._hash = hash(self._cards)
        self._repr = "(len: {}, cards: {})".format(len(self._cards), repr(self._cards))
        self._str = "({})".format(', '.join([str(c) for c in self._cards]))

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
        pts = sum([c.points for c in self._cards])
        logging.debug("counting points of cards: {} -> {}".format(self._cards, pts))
        return pts

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
        from tichu.cards.partition import Partition
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
        return itertools.chain(self.all_squarebombs(), self.all_straightbombs())

    def all_squarebombs(self):
        for l in self.value_dict().values():
            if len(l) == 4:
                yield SquareBomb(*l)

    def all_straightbombs(self):
        for st in self.all_straights(ignore_phoenix=True):
            sb = try_ignore(lambda: StraightBomb(st))
            if sb:
                yield sb

    def all_pairs(self, ignore_phoenix=False):
        # TODO speed, sort and then iterate? probably not worth it.
        if not ignore_phoenix and Card.PHOENIX in self._cards:
            for c in self._cards:
                if c.suit is not CardSuit.SPECIAL:
                    yield Pair(c, Card.PHOENIX)

        for c1 in self._cards:
            for c2 in self._cards:
                if c1 is not c2 and c1.card_value is c2.card_value:
                    yield Pair(c1, c2)

    def all_trios(self, ignore_phoenix=False):
        # TODO speed, but probably not worth it.
        if not ignore_phoenix and Card.PHOENIX in self._cards:
            for p in self.all_pairs(ignore_phoenix=True):
                yield Trio(Card.PHOENIX, *p.cards)

        for l in self.value_dict().values():
            if len(l) == 3:
                yield Trio(*l)
            elif len(l) == 4:
                yield Trio(*l[:3])  # 0, 1, 2
                yield Trio(*l[1:])  # 1, 2, 3
                yield Trio(*l[2:], *l[:1])  # 2, 3, 0
                yield Trio(*l[3:], *l[:2])  # 3, 0, 1

    def all_straights_gen(self, length=None, ignore_phoenix=False):
        assert_(length is None or length >= 5, msg="length must be None or >=5, but was: " + str(length))

        if len(self._cards) < (5 if length is None else length):
            # if not enough cards are available, return.
            return
        else:
            sorted_cards = sorted([c for c in self._cards
                                   if c is not Card.PHOENIX and c is not Card.DOG and c is not Card.DRAGON],
                                  key=lambda c: c.card_value)

            next_c = defaultdict(lambda: [])  # card val height -> list of cards
            for c in sorted_cards:
                next_c[c.card_height - 1].append(c)

            def gen_from(card, remlength, ph):
                if remlength <= 1:
                    yield [card]  # finish a straight with this card

                # a straight for all possible continuations
                for nc in next_c[card.card_height]:
                    for st in gen_from(nc, remlength - 1, ph=ph):
                        yield [card] + st

                # Phoenix:
                if ph is None and not ignore_phoenix:
                    if remlength <= 2 and card.card_value is not CardValue.A:
                        phoenix_as = ImmutableCards._card_val_to_sword_card[card.card_height + 1]
                        yield [card, (Card.PHOENIX, phoenix_as)]  # finish the straight with the Phoenix

                    # take phoenix instead of card
                    if card is not Card.MAHJONG:
                        for nc in next_c[card.card_height]:
                            for st in gen_from(nc, remlength - 1, ph=card):
                                yield [(Card.PHOENIX, card)] + st

                    # take phoenix to jump a value
                    phoenix_as = ImmutableCards._card_val_to_sword_card[card.card_height + 1]
                    for nc in next_c[card.card_height+1]:
                        for st in gen_from(nc, remlength - 2, ph=phoenix_as):
                            yield [card, (Card.PHOENIX, phoenix_as)] + st

            def gen_all_straights():
                for c in sorted_cards:
                    if c.card_value <= CardValue.TEN:
                        yield from gen_from(c, 5, ph=None)  # all straights starting with normal card
                        if c.card_value > CardValue.TWO and not ignore_phoenix:
                            # all straights starting with the Phoenix
                            phoenix = ImmutableCards._card_val_to_sword_card[c.card_height - 1]
                            for st in gen_from(c, 4, ph=phoenix):
                                yield [(Card.PHOENIX, phoenix)] + st

            for st in gen_all_straights():
                try:
                    (phoenix, phoenix_as) = next(elem for elem in st if isinstance(elem, tuple))
                    st.remove((phoenix, phoenix_as))  # TODO switch to dictionaries {card->card, phoenix->card ...}
                    st.append(phoenix)
                    yield Straight(st, phoenix_as=phoenix_as)
                except StopIteration:
                    yield Straight(st)

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
            elif c_height == last_height and acc_straight[-1] is not Card.PHOENIX:
                # remove last and take cc instead
                all_straights_rec(remaining[1:], acc_straight[:-1] + [cc], last_height=c_height, ph_in_acc=ph_in_acc)
                # don't take cc
                all_straights_rec(remaining[1:], acc_straight, last_height=last_height, ph_in_acc=ph_in_acc)

            all_straights_rec(remaining[1:], list(), None, ph_in_acc=None)  # start new straight

            # the phoenix is not yet used and can be used
            if phoenix and not ph_in_acc and cc.card_value is not CardValue.A:
                # take phoenix instead of any other card
                if len(acc_straight) > 0:
                    all_straights_rec(remaining, acc_straight + [Card.PHOENIX], last_height=last_height + 1,
                                      ph_in_acc=ImmutableCards._card_val_to_sword_card[last_height + 1])
                # start a straight with phoenix and current card
                if cc.card_value is not CardValue.TWO and cc is not Card.MAHJONG:
                    all_straights_rec(remaining[1:], [Card.PHOENIX, cc], c_height,
                                      ph_in_acc=ImmutableCards._card_val_to_sword_card[c_height-1])

        s_cards = sorted([c for c in self._cards
                          if c is not Card.PHOENIX
                          and c is not Card.DOG
                          and c is not Card.DRAGON],
                         key=lambda c: c.card_value)

        all_straights_rec(s_cards, list(), None, ph_in_acc=None)

        return straights

    def all_fullhouses(self, ignore_phoenix=False):
        for t in self.all_trios(ignore_phoenix=ignore_phoenix):
            for p in self.all_pairs(ignore_phoenix=ignore_phoenix):
                try:
                    yield FullHouse(pair=p, trio=t)
                except Exception:
                    pass

    def all_pairsteps(self, ignore_phoenix=False, length=None):
        assert_(length is None or length > 0)
        pairs_s = sorted(list(self.all_pairs(ignore_phoenix=ignore_phoenix)))
        # TODO speed, may be faster

        new_ps = set()
        # find all pairsteps of length 2
        for p1 in pairs_s:
            for p2 in pairs_s:
                if p1 != p2 and abs(p1.height - p2.height) == 1 and not(p1.contains_phoenix() and p2.contains_phoenix()):
                    new_ps.add(PairSteps([p1, p2]))

        psteps = set()
        # find all longer pairsteps
        while len(new_ps):
            ps = new_ps.pop()
            if ps not in psteps:
                for pair in pairs_s:
                    try:
                        res = ps.extend(pair)
                        new_ps.add(res)
                    except Exception:
                        pass
                psteps.add(ps)
        if length is not None:
            return {ps for ps in psteps if len(ps) == length}
        else:
            return psteps

    def all_combinations(self, played_on=None, ignore_phoenix=False, contains_value=None):
        """
        :return: a set of all possible combinations appearing in this cards instance
        """
        combs = set()
        if played_on is None:
            combs.update([Single(c) for c in self._cards])  # single cards
            combs.update(self.all_bombs())
            combs.update(self.all_pairs(ignore_phoenix=ignore_phoenix))
            combs.update(self.all_trios(ignore_phoenix=ignore_phoenix))
            combs.update(self.all_straights(ignore_phoenix=ignore_phoenix))
            combs.update(self.all_fullhouses(ignore_phoenix=ignore_phoenix))
            combs.update(self.all_pairsteps(ignore_phoenix=ignore_phoenix))
        if isinstance(played_on, Combination):
            if Card.DOG in played_on:
                assert len(played_on) == 1
                return set()  # it is not possible to play on the dog

            combs.update([b for b in self.all_bombs() if played_on < b])
            if Card.DRAGON in played_on:
                assert len(played_on) == 1
                return combs  # only bombs can beat the Dragon

            elif isinstance(played_on, Single) and Card.MAHJONG in played_on:
                assert len(played_on) == 1
                # all single cards except dog
                combs.update({Single(c) for c in self._cards if c is not Card.DOG})

            elif isinstance(played_on, Single) and Card.PHOENIX in played_on:
                assert len(played_on) == 1
                # all single cards except dog and Mahjong
                combs.update({Single(c) for c in self._cards if c is not Card.DOG and c is not Card.MAHJONG})

            elif isinstance(played_on, Single):
                # all single cards higher than the played_on.any_card
                combs.update({Single(c) for c in self._cards if played_on.height < c.card_height})

            elif isinstance(played_on, Pair):
                # all pairs higher than the played_on.any_card
                pairs = self.all_pairs()
                combs.update({pair for pair in pairs if played_on < pair})

            elif isinstance(played_on, Trio):
                # all trios higher than the played_on.any_card
                trios = self.all_trios()
                combs.update({trio for trio in trios if played_on < trio})

            elif isinstance(played_on, PairSteps):
                # all higher pairsteps
                pairsteps = self.all_pairsteps(length=len(played_on))
                combs.update({ps for ps in pairsteps if played_on < ps})

            elif isinstance(played_on, Straight):
                # all higher straights
                straights = self.all_straights(length=len(played_on))
                combs.update({st for st in straights if played_on < st})

        if contains_value:
            return {comb for comb in combs if contains_value in (c.card_value for c in comb)}
        else:
            return combs

    def random_cards(self, n=1):
        """
        :param n: int > 0
        :return: n random cards.
        """
        cds = list(self._cards)
        random.shuffle(cds)
        return cds[:n]

    def __str__(self):
        return self._str

    def __repr__(self):
        return "[{}]({})".format(type(self).__name__, self._repr)

    def __len__(self):
        return len(self._cards)

    def __iter__(self):
        return self._cards.__iter__()

    def __contains__(self, item):
        return self._cards.__contains__(item)

    def __add__(self, other):
        assert_(isinstance(other, ImmutableCards))
        return ImmutableCards(self._cards.union(other._cards))

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


class Cards(ImmutableCards):
    """
    A mutable set of Cards with some helpful functions.
    """

    def __init__(self, cards):
        super().__init__(cards)
        self._cards = set(self._cards)
        self.__hash__ = None  # diable hashing

    def add(self, card):
        """
        Adds the card to this Cards set
        :param card: the Card to add
        :return: Nothing
        """
        if isinstance(card, Card):
            self._cards.add(card)
            assert card in self._cards
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
        assert card not in self._cards

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

    def __str__(self):
        return "({})".format(', '.join([str(c) for c in self._cards]))

    def __repr__(self):
        return "(len: {}, cards: {})".format(len(self._cards), repr(self._cards))


class Combination(metaclass=abc.ABCMeta):

    def __init__(self, cards):
        assert_(len(cards) > 0)
        assert_(all((isinstance(card, Card) for card in cards)), msg="cards: "+str(cards))
        self._cards = ImmutableCards(cards)
        assert len(self._cards) == len(cards)

    @property
    def cards(self):
        return self._cards

    @abc.abstractproperty
    def height(self):
        raise NotImplementedError()

    @property
    def points(self):
        return sum(c.points for c in self._cards)

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
        return Card.PHOENIX in self._cards

    def issubset(self, other):
        for c in self._cards:
            if c not in other:
                return False
        return True

    def fulfills_wish(self, wish):
        return wish in (c.card_value for c in self._cards)

    def __iter__(self):
        return iter(self._cards)

    def __eq__(self, other):
        return self.__class__ is other.__class__ and self.cards == other.cards and self.height == other.height

    def __hash__(self):
        return hash(self._cards)

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

    def __str__(self):
        return "{}{}".format(self.__class__.__name__.upper(), str(self._cards))

    def __repr__(self):
        return self.__str__()


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
            assert_(card1.suit is not CardSuit.SPECIAL, msg="card1: {}, card2:{}".format(card1, card2))
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
        cards = set(pair.cards + trio.cards)
        assert_(len(cards) == 5, msg="pair: {}, trio: {}".format(pair, trio))
        super().__init__(cards)
        self._height = trio.height

    @property
    def height(self):
        return self._height

    @classmethod
    def from_cards(cls, cards):
        assert_(len(set(cards)) == 5)  # 5 different cards
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

        cards = set(itertools.chain(*[p.cards for p in pairs]))
        assert_(len(cards) == 2*len(pairs))  # no duplicated card (takes care of multiple phoenix use)
        super().__init__(cards)
        self._height = max(pairheights)
        self._lowest_pair_height = min(pairheights)
        self._pairs = pairs

    @property
    def height(self):
        return self._height

    @property
    def lowest_card_height(self):
        return self._lowest_pair_height

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

    def __lt__(self, other):
        if isinstance(other, Bomb):
            return True
        assert_(isinstance(other, PairSteps) and len(other) == len(self), self._cant_compare_error(other))
        return self.height < other.height


class Straight(Combination):

    def __init__(self, cards, phoenix_as=None):
        assert_(len(cards) >= 5)
        if Card.PHOENIX in cards:
            assert_(isinstance(phoenix_as, Card))
            assert_(phoenix_as not in cards)
            assert_(phoenix_as.suit is not CardSuit.SPECIAL, msg="But was "+str(phoenix_as))

        cards_phoenix_replaced = [c for c in cards if c is not Card.PHOENIX] + [phoenix_as] if phoenix_as else cards
        assert_(len({c.card_value for c in cards_phoenix_replaced}) == len(cards_phoenix_replaced),
                msg="cards: {} (phoenix_as: {})".format(cards_phoenix_replaced, phoenix_as))  # different card values
        cardheights = [c.card_height for c in cards_phoenix_replaced]
        assert_(max(cardheights) - min(cardheights) + 1 == len(cards_phoenix_replaced),
                msg="max: {} min: {} cards: {} (phoenix_as: {})".format(max(cardheights), min(cardheights), cards_phoenix_replaced, phoenix_as))  # cards are consecutive

        super().__init__(cards)
        self._height = max(cardheights)
        self._lowest_card = min(cards, key=lambda c: c.card_height)

    @property
    def height(self):
        return self._height

    @property
    def lowest_card(self):
        return self._lowest_card

    def __lt__(self, other):
        if isinstance(other, Bomb):
            return True
        assert_(isinstance(other, Straight) and len(other) == len(self), self._cant_compare_error(other))
        return self.height < other.height

    def __eq__(self, other):
        return super().__eq__(other) and self.lowest_card == other.lowest_card

    def __hash__(self):
        return hash((self._cards, self.height, self.lowest_card))

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
