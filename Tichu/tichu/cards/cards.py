import random
import warnings
from collections import abc as collectionsabc
import abc
from collections import defaultdict

import itertools

from tichu.cards.card import Card, CardSuit, CardValue
from tichu.utils import check_param, check_isinstance, check_all_isinstance, check_true, ignored

__author__ = 'Lukas Pestalozzi'


class ImmutableCards(collectionsabc.Collection):
    # TODO change all "isinstance(x, ImmutableClass)" to "self.__class__ == x.__class__"

    __slots__ = ("_cards", "_hash", "_repr", "_str")
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
            raise TypeError("Only instances of 'Card' can be put into 'Cards'. But was {}".format(cards))

        self._hash = hash(self._cards)
        self._repr = "(len: {}, cards: {})".format(len(self._cards), repr(self._cards))
        self._str = "({})".format(', '.join([str(c) for c in sorted(self._cards)]))

    @property
    def cards_list(self):
        return list(self._cards)

    @property
    def cards(self):
        return frozenset(self._cards)

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

    def union(self, other):
        """

        :param other:
        :return: frozenset of the union of both cards sets
        """
        return frozenset(self.cards.union(other.cards))

    def count_points(self):
        """
        :return the Tichu points in this set of cards.
        """
        pts = sum([c.points for c in self._cards])
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
        open_partitions.add(Partition([Single(c) for c in no_phoenix_cards]))

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
        return itertools.chain(self.squarebombs(contains_value=contains_value),
                               self.straightbombs(contains_value=contains_value))

    def squarebombs(self, contains_value=None):
        must_contain_val = isinstance(contains_value, CardValue)
        for l in self.value_dict().values():
            if len(l) == 4:
                b = SquareBomb(*l)
                if not must_contain_val or (must_contain_val and b.contains_cardval(contains_value)):
                    yield b

    def straightbombs(self, contains_value=None):
        # group by card suit
        suitdict = defaultdict(lambda: [])
        for c in self._cards:
            suitdict[c.suit].append(c)

        # look only at cards of same suit
        for suit, cards in suitdict.items():
            if len(cards) >= 5:  # must be at least 5 to be a straight (also excludes special cards)
                yield from (StraightBomb(st) for st in ImmutableCards(cards).straights(contains_value=contains_value))

    def singles(self, contains_value=None):
        sgls = (Single(c) for c in self._cards)
        if isinstance(contains_value, CardValue):
            return (s for s in sgls if s.contains_cardval(contains_value))
        else:
            return sgls

    def pairs(self, ignore_phoenix=False, contains_value=None):
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

    def trios(self, ignore_phoenix=False, contains_value=None):
        valdict = self.value_dict()
        # if contains_value is specified, filter all other values out
        if isinstance(contains_value, CardValue):
            valdict = {k: v for k, v in valdict.items() if k is contains_value}

        # phoenix
        if not ignore_phoenix and Card.PHOENIX in self._cards:
            for l in valdict.values():
                if len(l) >= 2:
                    yield Trio(l[0], l[1], Card.PHOENIX)

        # normal pairs
        for l in valdict.values():
            if len(l) >= 3:
                # 3 or more same valued cards -> take 2 of them
                yield Trio(l[0], l[1], l[2])

    def straights_old(self, length=None, ignore_phoenix=False, contains_value=None):
        check_param(length is None or length >= 5, length)
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
                must_contain_val = isinstance(contains_value, CardValue)
                max_card_val = CardValue.TEN  # there is no possible straight starting from J (must have length 5)
                if must_contain_val:
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
            must_contain_val = isinstance(contains_value, CardValue)
            for st in gen_all_straights():
                # TODO speed, make more efficient
                straight = None
                try: # raises Stop Iteration when phoenix is not in the straight
                    (phoenix, phoenix_as) = next(elem for elem in st if isinstance(elem, tuple))
                    st.remove((phoenix, phoenix_as))  # TODO switch to dictionaries {card->card, phoenix->card ...}
                    st.append(phoenix)
                    straight = Straight(st, phoenix_as=phoenix_as)
                except StopIteration:
                    straight = Straight(st)
                if not must_contain_val or (must_contain_val and straight.contains_cardval(contains_value)):
                    yield straight

    def straights(self, length=None, ignore_phoenix=False, contains_value=None):
        check_param(length is None or length >= 5, length)
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

            next_card = defaultdict(lambda: [])  # card val height -> list of cards with height 1 higher
            for c in sorted_cards:
                next_card[c.card_height - 1].append(c)

            def gen_from(card, remlength, ph):
                if remlength <= 1:
                    yield {card:card}  # finish a straight with this card

                # a straight for one possible continuation
                next_cards = next_card[card.card_height]
                if len(next_cards) > 0:
                    for st in gen_from(next_cards[0], remlength - 1, ph=ph):
                        yield {card:card, **st}

                # Phoenix:
                if ph is None and can_use_phoenix:
                    # finish the straight with the Phoenix:
                    if remlength <= 2 and card.card_value is not CardValue.A:
                        phoenix_as = ImmutableCards._card_val_to_sword_card[card.card_height + 1]
                        yield {card:card, Card.PHOENIX: phoenix_as}

                    # take phoenix instead of card
                    if card is not Card.MAHJONG:
                        if len(next_cards) > 0:
                            for st in gen_from(next_cards[0], remlength - 1, ph=card):
                                yield {Card.PHOENIX: card, **st}

                    # take phoenix to jump a value
                    if card.card_value < CardValue.K and len(next_card[card.card_height]) == 0:  # can not jump the As, and only jump if there is no next card
                        after_next_cards = next_card[card.card_height + 1]
                        if len(after_next_cards) > 0:  # there is a card to 'land'
                            phoenix_as = ImmutableCards._card_val_to_sword_card[card.card_height + 1]
                            for st in gen_from(after_next_cards[0], remlength - 2, ph=phoenix_as):
                                yield {card:card, Card.PHOENIX: phoenix_as, **st}

            def gen_all_straights():
                """ Take all possible starting cards and generate straights from them """
                must_contain_val = isinstance(contains_value, CardValue)
                max_card_val = CardValue.TEN  # there is no possible straight starting from J (must have length 5)
                if must_contain_val:
                    max_card_val = min(max_card_val, contains_value)  # straight starting from a higher value than contains_val, can not contain that val

                for c in sorted_cards:
                    if c.card_value <= max_card_val:
                        yield from gen_from(c, 5, ph=None)  # all straights starting with normal card
                        # all straights starting with the Phoenix:
                        if can_use_phoenix and c.card_value > CardValue.TWO:
                            phoenix = ImmutableCards._card_val_to_sword_card[c.card_height - 1]
                            for st in gen_from(c, 4, ph=phoenix):
                                yield {Card.PHOENIX:phoenix, **st}

            # make and yield the Straights:
            gen = (Straight(set(st.keys()), phoenix_as=st[Card.PHOENIX] if Card.PHOENIX in st else None) for st in gen_all_straights())
            if isinstance(contains_value, CardValue):
                yield from (st for st in gen if st.contains_cardval(contains_value))
            else:
                yield from gen

    def fullhouses(self, ignore_phoenix=False, contains_value=None):

        trios = list(self.trios(ignore_phoenix=ignore_phoenix))
        pairs = list(self.pairs(ignore_phoenix=ignore_phoenix))
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

    def pairsteps(self, ignore_phoenix=False, length=None, contains_value=None):
        check_param(length is None or length > 0, length)
        sorted_pairs = sorted(self.pairs(ignore_phoenix=ignore_phoenix))
        next_pair_no_ph = defaultdict(lambda: [])
        next_pair_with_ph = defaultdict(lambda: [])
        for p in sorted_pairs:
            if p.contains_phoenix():
                next_pair_with_ph[p.height-1].append(p)
            else:
                next_pair_no_ph[p.height - 1].append(p)

        def gen_from(pair, remlength, ph_used):
            if remlength <= 1:
                yield [pair]

            # continue without phoenix:
            try:
                for ps in gen_from(next_pair_no_ph[pair.height][0], remlength - 1, ph_used=ph_used):
                    yield [pair] + ps
            except (StopIteration, IndexError):
                pass

            # continue with phoenix:
            if not ph_used:
                try:
                    for ps in gen_from(next_pair_with_ph[pair.height][0], remlength - 1, ph_used=True):
                        yield [pair] + ps
                except (StopIteration, IndexError):
                    pass

        def gen_all_pairsteps():
            """ Take all possible starting pairs and generate pairsteps from them """
            max_height = CardValue.A.value  # there is no possible pairstep starting from As (must have length 2)
            if isinstance(contains_value, CardValue):
                max_height = min(max_height, contains_value.value)  # straight starting from a higher value than contains_val, can not contain that val

            for pair in sorted_pairs:
                if pair.height <= max_height:
                    yield from gen_from(pair, 2, ph_used=pair.contains_phoenix())  # all steps starting with the pair

        # make and yield the pairsteps:
        gen = (PairSteps(pairs) for pairs in gen_all_pairsteps())
        if isinstance(contains_value, CardValue):
            yield from (ps for ps in gen if ps.contains_cardval(contains_value))
        else:
            yield from gen

    def pairsteps_old(self, ignore_phoenix=False, length=None, contains_value=None):
        check_param(length is None or length > 0, length)
        pairs_s = sorted(self.pairs(ignore_phoenix=ignore_phoenix))

        if len(pairs_s) < 2:
            return

        def ps_len2():
            # find all pairsteps of length 2
            for i1, p1 in enumerate(pairs_s):
                for i2 in range(i1+1, len(pairs_s)):
                    p2 = pairs_s[i2]
                    try:
                        yield PairSteps([p1, p2])
                    except Exception:
                        pass

        ps_length2 = list(ps_len2())
        print("ps2:", ps_length2)

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
        check_param(contains_value is None or isinstance(contains_value, CardValue), contains_value)

        if played_on is None:
            yield from itertools.chain(
                    self.singles(contains_value=contains_value),
                    self.all_bombs(contains_value=contains_value),
                    self.pairs(ignore_phoenix=ignore_phoenix, contains_value=contains_value),
                    self.trios(ignore_phoenix=ignore_phoenix, contains_value=contains_value),
                    self.straights(ignore_phoenix=ignore_phoenix, contains_value=contains_value),
                    self.fullhouses(ignore_phoenix=ignore_phoenix, contains_value=contains_value),
                    self.pairsteps(ignore_phoenix=ignore_phoenix, contains_value=contains_value)
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
                yield from (single for single in self.singles(contains_value=contains_value) if single.can_be_played_on(played_on))

            elif isinstance(played_on, Pair):
                # all pairs higher than the played_on.any_card
                yield from (pair for pair in self.pairs(contains_value=contains_value) if pair.can_be_played_on(played_on))

            elif isinstance(played_on, Trio):
                # all trios higher than the played_on.any_card
                yield from (trio for trio in self.trios(contains_value=contains_value) if trio.can_be_played_on(played_on))

            elif isinstance(played_on, PairSteps):
                # all higher pairsteps
                yield from (ps for ps in self.pairsteps(length=len(played_on), contains_value=contains_value) if ps.can_be_played_on(played_on))

            elif isinstance(played_on, Straight):
                # all higher straights
                yield from (st for st in self.straights(length=len(played_on), contains_value=contains_value) if st.can_be_played_on(played_on))
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

    def pretty_string(self):
        # TODO
        return self._str

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
        check_isinstance(other, ImmutableCards)
        return ImmutableCards(self._cards.union(other._cards))

    def __hash__(self):
        return self._hash

    def __eq__(self, other):
        if self.__class__ is other.__class__ and len(self._cards) == len(other._cards):
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

    def __init__(self, cards=list()):
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
        :return self
        """
        for card in other:
            self.add(card)
        return self

    def remove(self, card):
        """
        Removes the card to this Cards set
        :param card: the Card to remove
        :return: Nothing
        """
        assert card in self._cards, "card: {}; remove from cards: {}".format(card, self._cards)
        self._cards.remove(card)
        assert card not in self._cards

    def remove_all(self, other):
        """
        Removes all elements in 'other' from this Cards set.
        :param other: Iterable containing only Card instances.
        :return: self
        """
        for card in other:
            self.remove(card)
        return self

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
        return "({})".format(', '.join([str(c) for c in sorted(self._cards)]))

    def __repr__(self):
        return "(len: {}, cards: {})".format(len(self._cards), repr(self._cards))


class Combination(metaclass=abc.ABCMeta):

    def __init__(self, cards):
        check_param(len(cards) > 0, cards)
        check_all_isinstance(cards, Card)
        self._cards = ImmutableCards(cards)
        check_true(len(self._cards) == len(cards))

    @property
    def cards(self):
        return self._cards

    @abc.abstractproperty
    def height(self):
        raise NotImplementedError()

    @property
    def points(self):
        return sum(c.points for c in self._cards)
    """
    @staticmethod
    def make(cards):
        makes a combiantion out of the given cards
        :param cards: the cards
        :return: the Combination
        :raise ValueError: if cards don't make a valid combination
        nbr_cards = len(cards)
        err = None
        try:
            check_param(0 < nbr_cards <= 15, nbr_cards)
            if nbr_cards == 1:
                return Single(*cards)

            if nbr_cards == 2:
                return Pair(*cards)

            if nbr_cards == 3:
                return Trio(*cards)

            if nbr_cards == 4:
                return SquareBomb(*cards)

            if nbr_cards % 2 == 0:
                ps = try_ignore(lambda: PairSteps.from_cards(cards))
                if ps:
                    return ps

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
    """  # make
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
        check_isinstance(other, (type(self), Bomb), msg="Can't compare")
        return self.height < other.height

    def __str__(self):
        return "{}({})".format(self.__class__.__name__.upper(), ",".join(str(c) for c in sorted(self._cards)))

    def __repr__(self):
        return self.__str__()


class Single(Combination):

    __slots__ = ("_card", "_height")

    def __init__(self, card):
        super().__init__([card])
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
        check_isinstance(newheight, (int, float))
        check_param(newheight == Card.PHOENIX.card_height or 2 <= newheight < 15, param=newheight)  # newheight must be between 2 and 14 (TWO and As)
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
        check_isinstance(other, Single)
        check_true(self.card is not Card.DOG and other.card is not Card.DOG, ex=TypeError, msg="Can't compare")  # dog can't be compared
        if self.card is Card.DRAGON:
            return False  # dragon is the highest single card
        if other.is_phoenix() and other.height == Card.PHOENIX.card_height:
            return True  # if the phoenix is on the right hand side of '<' and its value has not been changed, return True

        return self.height < other.height

    def __contains__(self, item):
        return self._card is item


class Pair(Combination):

    __slots__ = ("_card_value", "_height")

    def __init__(self, card1, card2):
        check_param(card1 is not card2, param=(card1, card2))  # different cards
        super().__init__((card1, card2))

        if Card.PHOENIX in self._cards:
            if card1 is Card.PHOENIX:
                card1, card2 = card2, card1  # make sure card1 is not Phoenix
            check_param(card1.suit is not CardSuit.SPECIAL, card1)
        else:
            check_param(card1.card_value is card2.card_value, (card1, card2))  # same value

        self._height = card1.card_height
        self._card_value = card1.card_value

    @property
    def height(self):
        return self._height


class Trio(Combination):

    __slots__ = ("_card_value", "_height")

    def __init__(self, card1, card2, card3):
        check_param(card1 is not card2 and card1 is not card3 and card2 is not card3, param=(card1, card2, card3))  # 3 different cards
        super().__init__((card1, card2, card3))

        if Card.PHOENIX in self._cards:
            if card1 is Card.PHOENIX:
                card1, card2 = card2, card1  # make sure card1 is not Phoenix
            check_param(card1.suit is not CardSuit.SPECIAL)
        else:
            check_param(card1.card_value is card2.card_value is card3.card_value)  # same values

        self._height = card1.card_height
        self._card_value = card1.card_value

    @property
    def height(self):
        return self._height


class FullHouse(Combination):

    __slots__ = ("_pair", "_trio", "_height")

    def __init__(self, pair, trio):
        check_isinstance(pair, Pair)
        check_param(trio, Trio)
        check_param(not(pair.contains_phoenix() and trio.contains_phoenix()))  # phoenix can only be used once
        cards = set(pair.cards + trio.cards)
        check_param(len(cards) == 5, param=(pair, trio))
        super().__init__(cards)
        self._height = trio.height
        self._pair = pair
        self._trio = trio

    @property
    def height(self):
        return self._height

    @property
    def trio(self):
        return self._trio

    @property
    def pair(self):
        return self._pair

    @classmethod
    def from_cards(cls, cards):
        check_param(len(set(cards)) == 5)  # 5 different cards
        check_param(Card.PHOENIX not in cards, "can't make from cards when Phoenix is present")
        pair = None
        trio = None
        for cs in ImmutableCards(cards).value_dict().values():
            if len(cs) == 2:
                pair = Pair(*cs)
            elif len(cs) == 3:
                trio = Trio(*cs)
            else:
                check_true(len(cs) == 0, ex=ValueError, msg="there is no fullhouse in the cards (cards: {})".format(cards))  # if this fails, then there is no fullhouse in the cards
        return cls(pair, trio)

    def __eq__(self, other):
        return self.__class__ == other.__class__ and self.trio == other.trio and self.pair == other.pair

    def __hash__(self):
        return hash((self._trio, self._pair))

    def __str__(self):
        return "{}(<{}><{}>)".format(self.__class__.__name__.upper(), ",".join(str(c) for c in self._trio), ",".join(str(c) for c in self._pair))


class PairSteps(Combination):

    __slots__ = ("_lowest_pair_height", "_height", "_pairs")

    def __init__(self, pairs):
        check_param(len(pairs) >= 2)
        check_all_isinstance(pairs, Pair)

        pairheights = {p.height for p in pairs}
        check_param(len(pairheights) == len(pairs))  # all pairs have different height
        check_param(max(pairheights) - min(pairheights) + 1 == len(pairs))  # pairs are consecutive

        cards = set(itertools.chain(*[p.cards for p in pairs]))
        check_param(len(cards) == 2*len(pairs), param=pairs)  # no duplicated card (takes care of multiple phoenix use)
        super().__init__(cards)
        self._height = max(pairheights)
        self._lowest_pair_height = min(pairheights)
        self._pairs = pairs

    @property
    def height(self):
        return self._height

    @property
    def pairs(self):
        return self._pairs

    @property
    def lowest_card_height(self):
        return self._lowest_pair_height

    @classmethod
    def from_cards(cls, cards):
        check_param(len(cards) >= 4 and len(cards) % 2 == 0)
        check_param(Card.PHOENIX not in cards, "can't make pairstep from cards when Phoenix is present")
        pairs = []
        for cs in ImmutableCards(cards).value_dict().values():
            if len(cs) == 2:
                pairs.append(Pair(*cs))
            check_true(len(cs) == 0, ex=ValueError, msg="Not a pairstep")
        return cls(pairs)

    def extend(self, pair):
        return PairSteps(self._pairs + [pair])

    def __str__(self):
        return "{}({})".format(self.__class__.__name__.upper(), ", ".join("{c[0]}{c[1]}".format(c=sorted(p.cards)) for p in self._pairs))

    def __lt__(self, other):
        if isinstance(other, Bomb):
            return True
        check_isinstance(other, PairSteps)
        check_true(len(other) == len(self), ex=TypeError, msg="Can't compare")
        return self.height < other.height


class Straight(Combination):

    __slots__ = ("_height", "_ph_as")

    def __init__(self, cards, phoenix_as=None):
        check_param(len(cards) >= 5)
        if Card.PHOENIX in cards:
            check_isinstance(phoenix_as, Card)
            check_param(phoenix_as not in cards, param=(phoenix_as, cards))
            check_param(phoenix_as.suit is not CardSuit.SPECIAL, param=phoenix_as)

        cards_phoenix_replaced = [c for c in cards if c is not Card.PHOENIX] + [phoenix_as] if phoenix_as else cards
        check_param(len({c.card_value for c in cards_phoenix_replaced}) == len(cards_phoenix_replaced))  # different card values
        cardheights = [c.card_height for c in cards_phoenix_replaced]
        check_param(max(cardheights) - min(cardheights) + 1 == len(cards_phoenix_replaced))  # cards are consecutive

        super().__init__(cards)
        self._height = max(cardheights)
        self._ph_as = phoenix_as

    @property
    def height(self):
        return self._height

    @property
    def phoenix_as(self):
        return self._ph_as

    def __lt__(self, other):
        if isinstance(other, Bomb):
            return True
        check_isinstance(other, Straight)
        check_true(len(other) == len(self), ex=TypeError, msg="Can't compare")
        return self.height < other.height

    def __eq__(self, other):
        if self.contains_phoenix():
            return super().__eq__(other) and self.phoenix_as.card_value is other.phoenix_as.card_value
        else:
            return super().__eq__(other)

    def __str__(self):
        if self.contains_phoenix():
            return "{}({})".format(self.__class__.__name__.upper(), ",".join("PH:"+str(self.phoenix_as) if c is Card.PHOENIX else str(c) for c in sorted(self._cards)))
        else:
            return super().__str__()

    def __hash__(self):
        if self.contains_phoenix():
            return hash((self._cards, self.height, self.phoenix_as.card_value))
        else:
            return hash((self._cards, self.height))


class Bomb(Combination):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class SquareBomb(Bomb):

    __slots__ = ("_height", )

    def __init__(self, card1, card2, card3, card4):
        super().__init__((card1, card2, card3, card4))
        check_param(len(set(self.cards)) == 4)  # all cards are different
        # all cards have same card_value (takes also care of the phoenix)
        check_param(len({c.card_value for c in self.cards}) == 1)
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

    __slots__ = ("_height", )

    def __init__(self, straight):
        check_isinstance(straight, Straight)
        check_true(len({c.suit for c in straight}) == 1)  # only one suit (takes also care of the phoenix)
        super().__init__(straight.cards)
        self._height = straight.height + 1000  # 1000 to make sure it is higher than any other non straightbomb

    @property
    def height(self):
        return self._height

    @classmethod
    def from_cards(cls, *cards):
        return cls(Straight(cards))

    def __lt__(self, other):
        if isinstance(other, StraightBomb):
            if len(self) < len(other):
                return True
            elif len(self) == len(other):
                return self.height < other.height
        return False
