from collections import abc

from tichu.cards.cards import Single, Trio, Pair, Straight, StraightBomb, PairSteps, ImmutableCards
from tichu.cards.cards import Combination

__author__ = 'Lukas Pestalozzi'
__all__ = ['Partition']


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

    def contains_card(self, card):
        for comb in self._combs:
            if card in comb:
                return True
        return False

    def merge(self, combs):
        """
        :param combs: The combs must occure in this Partition and must constitute a valid combination when merged
        :return: Returns a Partition with the two combs merged.
        """
        l = []
        for comb in combs:
            l.extend(comb.cards_list)
        return Partition(self._combs.difference(set(combs)).union({Combination.make(l)}))

    def find_all_straights(self):
        """
        :return: all possible Partitions created from merging single combinations to a straight
        """

        single_cards = ImmutableCards([comb.card for comb in self._combs if isinstance(comb, Single)])
        if len(single_cards) < 5:
            return set()

        straights = single_cards.all_straights()
        partitions = set()
        for st in straights:
            stcombs = [Straight(*s) for s in st]
            partitions.add(self.merge(stcombs))

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
                if comb2 == comb1 or comb1.is_dog() or comb1.is_dragon() or comb2.is_dog() or comb2.is_dragon():
                    # print("-> same, continue")
                    continue

                # single + single, pair, trio
                if isinstance(comb1, Single) and isinstance(comb2, (Single, Pair, Trio)) and comb1.height == comb2.height:
                    # print("-> single + single, pair, trio")
                    new_partitions.add(self.merge([comb1, comb2]))

                # single + straight -> longer straight
                if isinstance(comb1, Single) and isinstance(comb2, (Straight, StraightBomb)) and comb2.can_add(comb1):
                    # print("-> single + straight -> longer straight")
                    new_partitions.add(self.merge([comb1, comb2]))

                if isinstance(comb1, Pair):
                    if isinstance(comb2, Pair) and abs(comb1.height - comb2.height) <= 1:
                        # Pair + Pair -> squarebomb (diff is 0) or pairstep (diff is 1)
                        # print("-> Pair + Pair -> squarebomb or pairstep")
                        new_partitions.add(self.merge([comb1, comb2]))

                    if isinstance(comb2, Trio):  # Pair + Trio -> Fullhouse
                        # print("-> Pair + Trio -> Fullhouse")
                        new_partitions.add(self.merge([comb1, comb2]))

                    if isinstance(comb2, PairSteps) and comb2.can_add(comb1):
                        # Pair + Pairsteps -> pairstep
                        # print("-> Pair + Pairsteps -> pairstep")
                        new_partitions.add(self.merge([comb1, comb2]))

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

