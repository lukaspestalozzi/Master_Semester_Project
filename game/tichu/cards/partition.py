from collections import abc

from .card import Card
from .cards import Single, Trio, Pair, Straight, StraightBomb, PairSteps, ImmutableCards, SquareBomb, FullHouse, Combination
from game.utils import check_isinstance, ignored

__author__ = 'Lukas Pestalozzi'


class Partition(abc.Collection):

    def __init__(self, combinations):
        """
        Immutable Partition.
        Basically a set of Combinations
        :param combinations: iterable of combinations, or a single combination. (May be empty)
        """
        if isinstance(combinations, Combination):
            combinations = [combinations]
        if not all([isinstance(comb, Combination) for comb in combinations]):
            raise ValueError("combinations must be instances of Combination.")
        self._combs = frozenset(combinations)
        self._str = "Partition(nbr combs: {}, nbr cards: {}\n\t{})".format(len(self._combs), sum([len(c) for c in self._combs]), '\n\t'.join([str(comb) for comb in self._combs]))
        self._repr = "Partition({})".format(repr(self._combs))
        self._hash = hash(self._combs)

    @property
    def combinations(self):
        return self._combs

    @property
    def combinations_list(self):
        return list(self._combs)

    def to_json(self):
        return {
            "combinations": [comb.to_json() for comb in self._combs]
        }

    def contains_card(self, card):
        for comb in self._combs:
            if card in comb:
                return True
        return False

    def merge(self, combs, target_comb):
        """

        :param combs: the combinations that merged
        :param target_comb: the combination resulting from the merge
        :return: Returns a Partition with combs removed and the target added
        """
        check_isinstance(target_comb, Combination)
        return Partition(self._combs.difference(set(combs)).union({target_comb}))

    def find_all_straights(self):
        """
        :return: all possible Partitions created from merging single combinations to a straight
        """

        single_cards = ImmutableCards([comb.card for comb in self._combs if isinstance(comb, Single)])
        if len(single_cards) < 5:
            return set()

        straights = single_cards.straights()
        partitions = set()
        for st in straights:
            singles = [Single(c) for c in st]
            partitions.add(self.merge(singles, st))

        return partitions

    def evolve(self):
        """
        :return: A set of Partitions containing all Partitions that are created by combining two combinations in this partition.
        """

        # TODO only look at card values -> handle straightbomb
        # TODO handle phoenix

        new_partitions = set()
        for comb1 in self._combs:
            for comb2 in self._combs:
                # print("comb1:", comb1)
                # print("comb2:", comb2)
                if comb2 == comb1 or Card.DOG in comb1 or Card.DRAGON in comb1 or Card.DOG in comb2 or Card.DRAGON in comb2:
                    # print("-> same, continue")
                    continue

                # single + single, pair, trio
                if isinstance(comb1, Single) and isinstance(comb2, (Single, Pair, Trio)) and comb1.height == comb2.height:
                    # print("-> single + single, pair, trio")
                    if isinstance(comb2, Single):
                        new_partitions.add(self.merge({comb1, comb2}, Pair(comb1.card, comb2.card)))
                    elif isinstance(comb2, Pair):
                        new_partitions.add(self.merge({comb1, comb2}, Trio(*comb1.cards.union(comb2.cards))))
                    elif isinstance(comb2, Trio):
                        new_partitions.add(self.merge({comb1, comb2}, SquareBomb(*comb1.cards.union(comb2.cards))))

                # single + straight -> longer straight
                if isinstance(comb1, Single) and isinstance(comb2, (Straight, StraightBomb)):
                    # print("-> single + straight -> longer straight")
                    with ignored(ValueError):
                        st = Straight(comb1.cards.union(comb2.cards))
                        new_partitions.add(self.merge({comb1, comb2}, st))
                        new_partitions.add(self.merge({comb1, comb2}, st))

                if isinstance(comb1, Pair):
                    if isinstance(comb2, Pair) and abs(comb1.height - comb2.height) <= 1:
                        # Pair + Pair -> squarebomb (diff is 0) or pairstep (diff is 1)
                        # print("-> Pair + Pair -> squarebomb or pairstep")
                        with ignored(ValueError):
                            new_partitions.add(self.merge({comb1, comb2}, SquareBomb(*comb1.cards.union(comb2.cards))))
                        with ignored(ValueError):
                            new_partitions.add(self.merge({comb1, comb2}, PairSteps({comb1, comb2})))

                    if isinstance(comb2, Trio):  # Pair + Trio -> Fullhouse
                        # print("-> Pair + Trio -> Fullhouse")
                        new_partitions.add(self.merge({comb1, comb2}, FullHouse(pair=comb1, trio=comb2)))

                    if isinstance(comb2, PairSteps) and comb2:
                        # Pair + Pairsteps -> pairstep
                        # print("-> Pair + Pairsteps -> pairstep")
                        with ignored(ValueError):
                            new_partitions.add(self.merge({comb1, comb2}, PairSteps({comb1}.union(comb2.pairs))))

            # rof
        # rof
        all_straights = self.find_all_straights()
        new_partitions.update(all_straights)
        # print("-> all_straights", all_straights)
        return new_partitions

    def __len__(self):
        return len(self._combs)

    def __contains__(self, item):
        return self._combs.__contains__(item)

    def __iter__(self):
        return self._combs.__iter__()

    def __str__(self):
        return self._str

    def __repr__(self):
        return self._repr

    def __hash__(self):
        return self._hash

    def __eq__(self, other):
        if self.__class__ is other.__class__ and len(self) == len(other) and hash(self) == hash(other):
            for comb in self._combs:
                if comb not in other:
                    return False
            return True
        else:
            return False

