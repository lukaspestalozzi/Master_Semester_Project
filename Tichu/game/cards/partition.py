from collections import abc

from game.cards.combination import Combination, CombinationType


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
        try:
            l = []
            for comb in combs:
                l.extend(comb.cards_list)
            return Partition(self._combs.difference(set(combs)).union({Combination(l)}))
        except Exception as e:
            raise ValueError("Cant merge those combs in this Partition, {}".format(e))
        """
        l = []
        for comb in combs:
            l.extend(comb.cards_list)
        return Partition(self._combs.difference(set(combs)).union({Combination(l)}))

    def find_all_straights(self):
        """

        :return: all possible Partitions created from merging 5 single combinations to a straight
        """
        straights = []
        def to_straight_rec(remaining, acc_straight):
            if len(acc_straight) == 5:
                straights.append(acc_straight)
                return None

            if len(remaining) == 0:
                return None
            cc = remaining[0]  # current combination
            tail = remaining[1:]
            ccheight = cc.any_card.card_height
            accheight = acc_straight[-1].any_card.card_height if len(acc_straight) > 0 else None
            # card may be added to straight
            if len(acc_straight) == 0 or ccheight == accheight + 1:
                to_straight_rec(tail, acc_straight + [cc])  # take cc
            # same height as last added card
            elif ccheight == accheight:
                to_straight_rec(tail, acc_straight[:-1] + [cc])  # remove last and take cc instead
            to_straight_rec(tail, acc_straight)  # don't take cc

        sorted_singles = sorted([comb for comb in self._combs if comb.type is CombinationType.SINGLE_CARD
                                 or comb.type is CombinationType.SINGLE_MAHJONG],
                              key=lambda cmb: cmb.lowest_card.card_value)

        if len(sorted_singles) < 5:
            return set()

        to_straight_rec(sorted_singles, list())
        partitions = set()
        for st in straights:
            partitions.add(self.merge(st))

        return partitions

    def evolve(self):
        """
        :return: A set of Partitions containing all Partitions that are created by combining two combinations in this partition.
        """

        # TODO only look at card values -> handle straightbomb

        def single_same_valued(val_single1, val_comb2, type2):
            return (val_single1 is val_comb2 and (type2 is CombinationType.SINGLE_CARD
                                               or type2 is CombinationType.PAIR
                                               or type2 is CombinationType.TRIO))

        def single_step(height_single, min_height2, max_height2):
            return height_single - 1 == max_height2 or height_single + 1 == min_height2

        new_partitions = set()
        for comb1 in self._combs:
            for comb2 in self._combs:
                # print("comb1:", comb1)
                # print("comb2:", comb2)
                if comb2 == comb1:
                    # print("-> same, continue")
                    continue
                t1 = comb1.type
                t2 = comb2.type
                any_card1 = comb1.any_card

                # single + single, pair, trio
                if t1 is CombinationType.SINGLE_CARD and single_same_valued(any_card1.card_value, comb2.any_card.card_value, t2):
                    # print("-> single + single, pair, trio")
                    new_partitions.add(self.merge([comb1, comb2]))

                # single + straight -> longer straight
                if ((t1 is CombinationType.SINGLE_CARD or t1 is CombinationType.SINGLE_MAHJONG) and (t2 is CombinationType.STRAIGHT or t2 is CombinationType.STRAIGHTBOMB)
                        and single_step(any_card1.card_height, comb2.lowest_card.card_height, comb2.highest_card.card_height)):
                    # print("-> single + straight -> longer straight")
                    new_partitions.add(self.merge([comb1, comb2]))

                if t1 is CombinationType.PAIR:
                    if t2 is t1 and (any_card1.card_value is comb2.any_card.card_value or abs(any_card1.card_height - comb2.any_card.card_height) == 1):
                        # Pair + Pair -> squarebomb or pairstep
                        # print("-> Pair + Pair -> squarebomb or pairstep")
                        new_partitions.add(self.merge([comb1, comb2]))

                    if t2 is CombinationType.TRIO:  # Pair + Trio -> Fullhouse
                        # print("-> Pair + Trio -> Fullhouse")
                        new_partitions.add(self.merge([comb1, comb2]))

                    if t2 is CombinationType.PAIR_STEPS and single_step(any_card1.card_height, comb2.lowest_card.card_height, comb2.highest_card.card_height):
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

