import random
import uuid
import warnings
from collections import abc as collectionsabc
import abc
from collections import defaultdict

import itertools

import logging

from tichu.cards.card import Card, CardSuit, CardValue
from tichu.utils import assert_, try_ignore

__author__ = 'Lukas Pestalozzi'


class ImmutableCards(collectionsabc.Collection):
    # TODO change all "isinstance(x, ImmutableClass)" to "self.__class__ == x.__class__"

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

    def value_dict(self, include_special=True):
        """
        :type include_special: bool: if False, the special cards are not in the dict
        :return: a dict mapping the card_values appearing in self._cards to the list of corresponding cards.
        """
        # TODO precompute, -> must be overridden by mutable subclasses
        val_dict = defaultdict(lambda: [])
        for c in self._cards:
            if include_special or c.suit is not CardSuit.SPECIAL:
                val_dict[c.card_value].append(c)
        return val_dict

    # TODO cache the results -> (only in immutable cards)

    def all_bombs(self, contains_value=None):
        return itertools.chain(self.all_squarebombs(contains_value=contains_value),
                               self.all_straightbombs(contains_value=contains_value))

    def all_squarebombs(self, contains_value=None):
        must_contain_val = isinstance(contains_value, CardValue)
        for l in self.value_dict().values():
            if len(l) == 4:
                b = SquareBomb(*l)
                if not must_contain_val or (must_contain_val and b.contains_cardval(contains_value)):
                    yield b

    def all_straightbombs(self, contains_value=None):
        # TODO speed, maybe precompute suitdict
        must_contain_val = isinstance(contains_value, CardValue)
        # group by card suit
        suitdict = defaultdict(lambda: [])
        for c in self._cards:
            suitdict[c.suit].append(c)
        # look only at cards of same suit
        for suit, cards in suitdict.items():
            if len(cards) >= 5:  # must be at least 5 to be a straight
                cards_s = sorted(cards)
                curr_straight = []
                last_h = -10  # some number < -1
                for card in cards_s:
                    if card.card_height == last_h + 1:
                        # continue straight
                        curr_straight.append(card)
                        if len(curr_straight) >= 5:  # there is a straightbomb
                            stbomb = StraightBomb.from_cards(list(curr_straight))
                            if not must_contain_val or (must_contain_val and stbomb.contains_cardval(contains_value)):
                                yield stbomb
                    else:
                        # start new straight
                        curr_straight = [card]
                    last_h = card.card_height

    def all_singles(self, contains_value=None):
        sgls = (Single(c) for c in self._cards)
        if isinstance(contains_value, CardValue):
            return (s for s in sgls if s.contains_cardval(contains_value))
        else:
            return sgls

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

    def all_different_pairs(self, ignore_phoenix=False, contains_value=None):
        valdict = self.value_dict(include_special=False)

        # if contains_value is specified, filter all other values out
        if isinstance(contains_value, CardValue):
            valdict = {k: v for k, v in valdict.items() if k is contains_value}

        # phoenix
        if not ignore_phoenix and Card.PHOENIX in self._cards:
            for l in valdict.values():
                assert len(l) > 0
                yield Pair(l[0], Card.PHOENIX)

        # normal pairs
        for l in valdict.values():
            if len(l) >= 2:
                # 2 or more same valued cards -> take 2 of them
                yield Pair(l[0], l[1])
            if len(l) == 4:
                # 4 same valued cards -> make 2 different pairs (l[0] and l[1] already yielded)
                yield Pair(l[2], l[3])

    def all_trios(self, ignore_phoenix=False):
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

    def all_different_trios(self, ignore_phoenix=False, contains_value=None):
        valdict = self.value_dict()
        # if contains_value is specified, filter all other values out
        if isinstance(contains_value, CardValue):
            valdict = {valdict[k] for k in valdict if k is contains_value}

        # phoenix
        if not ignore_phoenix and Card.PHOENIX in self._cards:
            for l in valdict.values():
                if len(l) >= 3:
                    yield Trio(l[0], l[1], Card.PHOENIX)

        # normal pairs
        for l in valdict.values():
            if len(l) >= 3:
                # 3 or more same valued cards -> take 2 of them
                yield Trio(l[0], l[1], l[2])

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
                    for nc in next_c[card.card_height + 1]:
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

    def all_different_straights(self, length=None, ignore_phoenix=False, contains_value=None):
        assert_(length is None or length >= 5, msg="length must be None or >=5, but was: " + str(length))

        can_use_phoenix = not ignore_phoenix and Card.PHOENIX in self._cards

        if len(self._cards) < (5 if length is None else length):
            # if not enough cards are available -> return.
            return
        elif isinstance(contains_value, CardValue) and contains_value not in (c.card_value for c in self._cards):
            # does not contain the 'contains_value' card -> return
            return
        else:
            sorted_cards = sorted([c for c in self._cards
                                   if c is not Card.PHOENIX and c is not Card.DOG and c is not Card.DRAGON],
                                  key=lambda c: c.card_value)

            next_c = defaultdict(lambda: [])  # card val height -> list of cards with height 1 higher
            for c in sorted_cards:
                next_c[c.card_height - 1].append(c)

            def gen_from(card, remlength, ph):
                if remlength <= 1:
                    yield [card]  # finish a straight with this card

                # a straight for one possible continuation
                next_cards = next_c[card.card_height]
                if len(next_cards) > 0:
                    for st in gen_from(next_cards[0], remlength - 1, ph=ph):
                        yield [card] + st

                # Phoenix:
                if ph is None and can_use_phoenix:
                    if remlength <= 2 and card.card_value is not CardValue.A:
                        phoenix_as = ImmutableCards._card_val_to_sword_card[card.card_height + 1]
                        yield [card, (Card.PHOENIX, phoenix_as)]  # finish the straight with the Phoenix

                    # take phoenix instead of card
                    if card is not Card.MAHJONG:
                        if len(next_cards) > 0:
                            for st in gen_from(next_cards[0], remlength - 1, ph=card):
                                yield [(Card.PHOENIX, card)] + st

                    # take phoenix to jump a value
                    if card.card_value < CardValue.K:  # can not jump the As
                        after_next_cards = next_c[card.card_height + 1]
                        if len(after_next_cards) > 0:
                            phoenix_as = ImmutableCards._card_val_to_sword_card[card.card_height + 1]
                            for st in gen_from(after_next_cards[0], remlength - 2, ph=phoenix_as):
                                yield [card, (Card.PHOENIX, phoenix_as)] + st

            def gen_all_straights():
                """ Take all possible starting cards and generate straights from them """
                max_card_val = CardValue.TEN  # there is no possible straight starting from J (must have length 5)
                if isinstance(contains_value, CardValue):
                    max_card_val = min(max_card_val, contains_value)  # straight starting from a higher value than contains_val, can not contain that val

                for c in sorted_cards:
                    if c.card_value <= max_card_val:
                        yield from gen_from(c, 5, ph=None)  # all straights starting with normal card
                        if can_use_phoenix and c.card_value > CardValue.TWO:
                            # all straights starting with the Phoenix
                            phoenix = ImmutableCards._card_val_to_sword_card[c.card_height - 1]
                            for st in gen_from(c, 4, ph=phoenix):
                                yield [(Card.PHOENIX, phoenix)] + st

            # make the Straights
            for st in gen_all_straights():
                # TODO speed, make more efficient
                try: # raises Stop Iteration when phoenix is not in the straight
                    (phoenix, phoenix_as) = next(elem for elem in st if isinstance(elem, tuple))
                    st.remove((phoenix, phoenix_as))  # TODO switch to dictionaries {card->card, phoenix->card ...}
                    st.append(phoenix)
                    yield Straight(st, phoenix_as=phoenix_as)
                except StopIteration:
                    yield Straight(st)
    """
    def all_straights(self, length=None, ignore_phoenix=False):

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
    """

    def all_fullhouses(self, ignore_phoenix=False):
        trios = list(self.all_trios(ignore_phoenix=ignore_phoenix))
        pairs = list(self.all_pairs(ignore_phoenix=ignore_phoenix))
        for t in trios:
            for p in pairs:
                try:
                    fh = FullHouse(pair=p, trio=t)
                    yield fh
                except Exception:
                    pass

    def all_different_fullhouses(self, ignore_phoenix=False, contains_value=None):

        trios = list(self.all_different_trios(ignore_phoenix=ignore_phoenix))
        pairs = list(self.all_different_pairs(ignore_phoenix=ignore_phoenix))
        if isinstance(contains_value, CardValue):
            for t in trios:
                t_contains = t.contains_cardval(contains_value)
                for p in pairs:
                    if t_contains or p.contains_cardval(contains_value):
                        try:
                            fh = FullHouse(pair=p, trio=t)
                            yield fh
                        except Exception:
                            pass
        else:
            for t in trios:
                for p in pairs:
                    try:
                        fh = FullHouse(pair=p, trio=t)
                        yield fh
                    except Exception:
                        pass

    def all_pairsteps(self, ignore_phoenix=False, length=None):
        assert_(length is None or length > 0)
        pairs_s = sorted(self.all_pairs(ignore_phoenix=ignore_phoenix))

        if len(pairs_s) < 2:
            return

        def ps_len2():
            # find all pairsteps of length 2
            for p1 in pairs_s:
                for p2 in pairs_s:
                    try:
                        yield PairSteps([p1, p2])
                    except Exception:
                        pass

        def ps_len_le_than(l):
            if l <= 2:
                yield from ps_len2()
            else:
                for ps in ps_len_le_than(l - 1):
                    for p in pairs_s:
                        try:
                            yield ps.extend(p)
                        except Exception:
                            pass

        if length is not None:
            yield from (ps for ps in ps_len_le_than(length) if len(ps) == length)
        else:
            yield from ps_len_le_than(len(pairs_s))

    def all_different_pairsteps(self, ignore_phoenix=False, length=None, contains_value=None):
        assert_(length is None or length > 0)
        pairs_s = sorted(self.all_different_pairs(ignore_phoenix=ignore_phoenix))

        if len(pairs_s) < 2:
            return

        def ps_len2():
            # find all pairsteps of length 2
            for p1 in pairs_s:
                for p2 in pairs_s:
                    try:
                        yield PairSteps([p1, p2])
                    except Exception:
                        pass

        ps_length2 = list(ps_len2())

        def ps_len_le_than(l):
            if l <= 2:
                yield from ps_length2
            else:
                for ps in ps_len_le_than(l - 1):
                    for p in pairs_s:
                        try:
                            yield ps.extend(p)
                        except Exception:
                            pass

        gen = (ps for ps in ps_len_le_than(length) if len(ps) == length) if length is not None else ps_len_le_than(len(pairs_s))
        if isinstance(contains_value, CardValue):
            yield from (ps for ps in gen if ps.contains_cardval(contains_value))
        else:
            yield from gen

    def all_combinations(self, played_on=None, ignore_phoenix=False, contains_value=None):
        assert_(contains_value is None or isinstance(contains_value, CardValue))

        if played_on is None:
            yield from itertools.chain(
                    self.all_singles(contains_value=contains_value),
                    self.all_bombs(contains_value=contains_value),
                    self.all_different_pairs(ignore_phoenix=ignore_phoenix, contains_value=contains_value),
                    self.all_different_trios(ignore_phoenix=ignore_phoenix, contains_value=contains_value),
                    self.all_different_straights(ignore_phoenix=ignore_phoenix, contains_value=contains_value),
                    self.all_different_fullhouses(ignore_phoenix=ignore_phoenix, contains_value=contains_value),
                    self.all_different_pairsteps(ignore_phoenix=ignore_phoenix, contains_value=contains_value)
                )
        elif isinstance(played_on, Combination):
            if Card.DOG in played_on:
                assert len(played_on) == 1
                return   # it is not possible to play on the dog

            if isinstance(played_on, Bomb):
                yield from (b for b in self.all_bombs(contains_value=contains_value) if b.can_be_played_on(played_on))  # only higher bombs
            else:
                yield from self.all_bombs(contains_value=contains_value)  # all bombs

            if Card.DRAGON in played_on:
                assert len(played_on) == 1
                return  # only bombs can beat the Dragon

            elif isinstance(played_on, Single):
                # all single cards higher than the played_on
                yield from (single for single in self.all_singles(contains_value=contains_value) if single.can_be_played_on(played_on))

            elif isinstance(played_on, Pair):
                # all pairs higher than the played_on.any_card
                yield from (pair for pair in self.all_different_pairs(contains_value=contains_value) if pair.can_be_played_on(played_on))

            elif isinstance(played_on, Trio):
                # all trios higher than the played_on.any_card
                yield from (trio for trio in self.all_different_trios(contains_value=contains_value) if trio.can_be_played_on(played_on))

            elif isinstance(played_on, PairSteps):
                # all higher pairsteps
                yield from (ps for ps in self.all_different_pairsteps(length=len(played_on), contains_value=contains_value) if ps.can_be_played_on(played_on))

            elif isinstance(played_on, Straight):
                # all higher straights
                yield from (st for st in self.all_different_straights(length=len(played_on), contains_value=contains_value) if st.can_be_played_on(played_on))
        else:
            raise ValueError("Wrong arguments! (played_on was {})".format(played_on))

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

    def contains_cardval(self, cardval):
        return cardval in (c.card_value for c in self._cards)

    def can_be_played_on(self, other_comb):
        try:
            return other_comb < self
        except Exception:
            return False

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
        return "{}({})".format(self.__class__.__name__.upper(), ",".join(str(c) for c in sorted(self._cards)))

    def __repr__(self):
        return self.__str__()


class Single(Combination):

    def __init__(self, card):
        super().__init__((card, ))
        self._card = card
        self._height = self._card.card_height

    @property
    def card(self):
        return self._card

    @property
    def height(self):
        return self._height

    def set_phoenix_height(self, newheight):
        """
        Set the height of tis single to the given height ONLY IF the Phoenix is the card of this single.
        Otherwise the call is ignored and a warning is printed.
        :param newheight:
        :return: the height of the single after this call
        """
        if self._card is Card.PHOENIX:
            self._height = newheight
        else:
            warnings.warn("Tried to set the height of a non-phoenix single. The height was not set.")
        return self.height

    def is_phoenix(self):
        return self._card is Card.PHOENIX

    def contains_cardval(self, cardval):
        return cardval is self._card.card_value

    def __lt__(self, other):
        if isinstance(other, Bomb):
            return True
        assert_(isinstance(other, Single), self._cant_compare_error(other))
        assert_(self.card is not Card.DOG and other.card is not Card.DOG)  # dog can't be compared
        if self.card is Card.DRAGON:
            return False  # dragon is the highest single card
        if other.is_phoenix() and other.height == Card.PHOENIX.card_height:
            return True  # if the phoenix is on the right hand side of '<' and its value has not been changed, return True

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
