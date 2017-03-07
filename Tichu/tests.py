
from time import time

from game.cards.card import Card
from game.cards.combination import Combination
from game.cards.deck import Deck
from game.cards.partition import Partition


def powerset(cards_seq):
    """
    Returns all the possible combinations of this set. This is a generator.
    """
    if len(cards_seq) <= 1:
        yield cards_seq  # single combination
        yield []
    else:
        for item in powerset(cards_seq[1:]):
            # item is a list of cards.
            # cards_seq[0] is a single card.
            yield [cards_seq[0]] + item
            yield item


def powerset_test():
    start_t = time()

    deck = Deck(full=True)
    piles = deck.split(nbr_piles=4, random_=True)

    cards = piles[0]  # [Card.SEVEN_HOUSE, Card.SEVEN_JADE, Card.SEVEN_PAGODA, Card.K_HOUSE, Card.K_JADE]
    print("nbr cards", len(cards))
    print("cards", cards)

    ps = powerset(list(cards))

    combs = []

    for comb in ps:
        try:
            combs.append(Combination(comb))
        except ValueError as e:
            pass  # print("No comb:", comb)

    # put together again


    print('\n'.join([c.short_string for c in combs]))
    print("time: ", time()-start_t)


def is_combination(cards):
    # TODO handle phoenix
    #print("is comb: ", cards, end=" -> ")
    try:
        c = Combination(cards)
        #print("True")
        return True
    except ValueError as ve:
        #print("False")
        return False


def combine(cards):

    def merge_and_create_new_partition(combs, combs_to_merge):
        new_combs = list(combs)
        for comb in combs_to_merge:
            new_combs.remove(comb)
        new_combs.append(merge_combs(combs_to_merge))
        return FrozenPartition(new_combs)

    def merge_combs(combs_to_merge):
        l = []
        for comb in combs_to_merge:
            l.extend(comb.cards_list)
        return Combination(l)

    def iter_and_test(combs, type1, type2, ps, test_funct):
        for i in range(len(combs)):
            comb = combs[i]
            if comb.type is type1:
                for k in range(i+1, len(combs)):
                    comb2 = combs[k]
                    if comb2.type is type2 and test_funct(comb, comb2):
                        ps.add(merge_and_create_new_partition(combs, [comb, comb2]))

    def singles_to_straight(singles):

        sorted_singles = sorted(singles, key=lambda comb: comb.any_card.card_value)
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

        to_straight_rec(sorted_singles, list())

        return straights

    def combine_once(combs):
        #start_t = time()
        ps = set()
        same_card_val = lambda c1, c2: c1.any_card.card_value is c2.any_card.card_value
        # single + single -> pair
        iter_and_test(combs, CombinationType.SINGLE_CARD, CombinationType.SINGLE_CARD, ps,
                      lambda c1, c2: c1.height == c2.height)

        # pair + single -> triples
        iter_and_test(combs, CombinationType.PAIR, CombinationType.SINGLE_CARD, ps,
                      same_card_val)

        # triple + single -> squarebomb
        iter_and_test(combs, CombinationType.TRIO, CombinationType.SINGLE_CARD, ps,
                      same_card_val)

        # pair + pair -> squarebomb
        iter_and_test(combs, CombinationType.PAIR, CombinationType.PAIR, ps,
                      same_card_val)

        # pair + triple -> fullshouse
        iter_and_test(combs, CombinationType.PAIR, CombinationType.TRIO, ps,
                      lambda c1, c2: True)

        # pair + pair -> pairstep
        iter_and_test(combs, CombinationType.PAIR, CombinationType.PAIR, ps,
                      lambda c1, c2: abs(c1.any_card.card_height - c2.any_card.card_height) == 1)

        # pairstep + pair -> pairstep
        iter_and_test(combs, CombinationType.PAIR_STEPS, CombinationType.PAIR, ps,
                      lambda c1, c2: (c1.highest_card.card_height - c2.any_card.card_height == -1
                                      or c1.lowest_card.card_height - c2.any_card.card_height == 1))

        # 5 single -> straight
        single_combs = sorted([comb for comb in combs if comb.type is CombinationType.SINGLE_CARD],
                              key=lambda comb: comb.any_card.card_value)
        if len(single_combs) >= 5:
            straights = singles_to_straight(single_combs)  # list of list of combs
            for st in straights:
                ps.add(merge_and_create_new_partition(combs, st))

        # straight + single -> straight
        iter_and_test(combs, CombinationType.STRAIGHT, CombinationType.SINGLE_CARD, ps,
                      lambda c1, c2: (c1.highest_card.card_height - c2.any_card.card_height == -1
                                      or c1.lowest_card.card_height - c2.any_card.card_height == 1))

        # straightbomb + single -> straight
        iter_and_test(combs, CombinationType.STRAIGHTBOMB, CombinationType.SINGLE_CARD, ps,
                              lambda c1, c2: (c1.highest_card.card_height - c2.any_card.card_height == -1
                                              or c1.lowest_card.card_height - c2.any_card.card_height == 1))

        # print("time comb once: ", time() - start_t)
        return ps
    # end combine_once

    # remove DOG and Dragon
    no_special_cards = [c for c in cards if c not in {Card.DOG, Card.DRAGON, Card.PHOENIX}]

    # remove Phoenix & replace it once with all cards not in cards
    # TODO

    # store 'all single' partition
    final_partitions = set()

    # repeat combine_once until no new partitions are generated
    new_partitions = set()
    new_partitions.add(FrozenPartition([Combination([c]) for c in no_special_cards]))
    while len(new_partitions) > 0:
        pton = new_partitions.pop()
        if pton not in final_partitions:
            final_partitions.add(pton)
            res = combine_once(pton.combinations_list)
            print(len(res))
            new_partitions.update(res)

    # add DOG and Dragon to each partition (if present in cards)
    # TODO

    # return that shit
    return frozenset(final_partitions)



def partition_test():
    print("partition test")
    start_t = time()

    deck = Deck(full=True)
    piles = deck.split(nbr_piles=4, random_=True)

    cards = [Card.DOG, Card.MAHJONG, Card.TWO_HOUSE, Card.THREE_SWORD, Card.FOUR_HOUSE, Card.FOUR_SWORD,
             Card.FIVE_JADE, Card.SIX_HOUSE, Card.SIX_SWORD, Card.SEVEN_JADE, Card.SEVEN_SWORD, Card.SEVEN_HOUSE,
             Card.EIGHT_HOUSE, Card.EIGHT_JADE, Card.EIGHT_SWORD, Card.K_HOUSE,
             Card.DRAGON, Card.PHOENIX]

    small_cards = [Card.MAHJONG, Card.TWO_HOUSE, Card.THREE_SWORD, Card.FOUR_HOUSE, Card.FOUR_SWORD,
             Card.FIVE_JADE, Card.SIX_SWORD, Card.SEVEN_JADE]

    very_small_cards = [Card.THREE_SWORD, Card.FOUR_HOUSE, Card.FOUR_SWORD]

    used_cards = cards
    print("cards:", used_cards)

    # -----------------------------------------------------------------------------------------------------
    # remove DOG and Dragon
    no_special_cards = [c for c in used_cards if c not in {Card.DOG, Card.DRAGON, Card.PHOENIX}]

    # remove Phoenix & replace it once with all cards not in cards
    # TODO

    # store 'all single' partition
    final_partitions = set()
    final_partitions.add(Partition([Combination([c]) for c in no_special_cards]))
    new_partitions = set()
    done = {}

    # repeat combine_once until no new partitions are generated
    foundnew = True
    while foundnew:
        foundnew = False
        for pton in final_partitions:
            if pton not in done:
                res = pton.evolve()
                if len(res) > 0:
                    foundnew = True
                    new_partitions.update(res)
                done[pton] = res
        final_partitions.update(new_partitions)
        new_partitions = set()

    # add DOG and Dragon to each partition (if present in cards)
    # TODO

    # -----------------------------------------------------------------------------------------------------
    ps = final_partitions

    printdone = False
    if printdone:
        for k, v in done.items():
            print(k, ": ------------------------- ", len(v))
            for p in v:
                print("->", p)

    printps = False
    if printps:
        for p in sorted(list(ps), key=lambda x: len(x)):
            print("\nPartition:", hash(p))
            for comb in p:
                print("  ", str(comb.type), sorted([c._cards for c in comb]))

    print("time: ", time() - start_t)
    print("nbr cards", len(used_cards), "-> nbr partitions:", len(ps))
    return ps


def find_straight_tests():
    p = Partition([Combination([c]) for c in [Card.MAHJONG, Card.TWO_HOUSE, Card.THREE_SWORD, Card.FOUR_HOUSE,
                 Card.FIVE_JADE, Card.SIX_SWORD, Card.SEVEN_JADE]])
    straights = p.find_all_straights()
    for st in straights:
        print(st)

def evolve_test():
    p = Partition([
        Combination([Card.SEVEN_HOUSE]),
        Combination([Card.FOUR_HOUSE]),
        Combination([Card.MAHJONG, Card.TWO_HOUSE, Card.THREE_SWORD, Card.FOUR_HOUSE, Card.FIVE_HOUSE, Card.SIX_JADE])
    ])
    print("res: ", str(p.evolve()))


if __name__ == '__main__':
    partition_test()
