
from time import time

from tichu.cards.card import Card
from tichu.cards.cards import ImmutableCards
from tichu.cards.deck import Deck
from tichu.cards.partition import Partition


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
    from tichu.cards.cards import Combination
    print("powerset test")
    start_t = time()

    cards, small_cards, very_small_cards = test_setup()
    used_cards = cards
    ps = powerset(list(used_cards))

    combs = []

    for comb in ps:
        try:
            combs.append(Combination(comb))
        except ValueError as e:
            pass  # print("No comb:", comb)

    # put together again

    print("nbr cards", len(used_cards), "-> nbr combiantions:", len(combs))
    print("time: ", time()-start_t)


def test_setup():
    print("setup test...")
    from tichu.cards.card import Card

    deck = Deck(full=True)
    piles = deck.split(nbr_piles=4, random_=True)

    cards = [Card.MAHJONG, Card.TWO_HOUSE, Card.THREE_SWORD, Card.FOUR_HOUSE, Card.FOUR_SWORD,
             Card.FIVE_JADE, Card.SIX_HOUSE, Card.SIX_SWORD, Card.SEVEN_JADE, Card.SEVEN_HOUSE,
             Card.EIGHT_SWORD, Card.K_HOUSE, Card.DRAGON, Card.PHOENIX]

    small_cards = [Card.MAHJONG, Card.TWO_HOUSE, Card.THREE_SWORD, Card.FOUR_HOUSE, Card.FOUR_SWORD,
                   Card.FIVE_JADE, Card.SIX_SWORD, Card.SEVEN_JADE]

    very_small_cards = [Card.THREE_SWORD, Card.FOUR_HOUSE, Card.FOUR_SWORD]

    return cards, small_cards, very_small_cards, piles


def partition_test():
    print("partition test")
    from tichu.cards.card import Card
    from tichu.cards.cards import Combination
    start_t = time()

    cards, small_cards, very_small_cards, piles = test_setup()

    used_cards = cards
    print("cards:", used_cards)

    # -----------------------------------------------------------------------------------------------------
    # remove DOG and Dragon
    no_special_cards = [c for c in used_cards if c not in {Card.DOG, Card.DRAGON, Card.PHOENIX}]

    # remove Phoenix & replace it once with all cards not in cards
    # TODO

    # store 'all single' partition
    final_partitions = set()
    open_partitions = set()
    open_partitions.add(Partition([Combination([c]) for c in no_special_cards]))

    done = {}

    # repeat combine_once until no new partitions are generated
    while len(open_partitions) > 0:  # for pton in final_partitions:
        pton = open_partitions.pop()
        if pton not in done:
            res = pton.evolve()
            if len(res) > 0:
                open_partitions.update(res)
            done[pton] = res
        final_partitions.update(open_partitions)
    open_partitions = set()

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
                print("  ", str(comb.type), sorted([c for c in comb]))

    print("time: ", time() - start_t)
    print("nbr cards", len(used_cards), "-> nbr partitions:", len(ps))
    return ps


def find_straight_tests():
    from tichu.cards.cards import ImmutableCards
    cards, small_cards, very_small_cards, piles = test_setup()
    used_cards = piles[0]
    start_t = time()
    straights = ImmutableCards(used_cards).all_straights(ignore_phoenix=False)
    print("time: ", time() - start_t)

    print("used_cards: ", sorted(used_cards))

    printps = False
    if printps:
        for st in sorted(straights, key=lambda s: (len(s), s.lowest_card)):
            print(sorted(st))
    print("found nbr straights: ", len(straights))


def evolve_test():
    from tichu.cards.card import Card
    from tichu.cards.cards import Combination
    p = Partition([
        Combination([Card.SEVEN_HOUSE]),
        Combination([Card.FOUR_HOUSE]),
        Combination([Card.MAHJONG, Card.TWO_HOUSE, Card.THREE_SWORD, Card.FOUR_HOUSE, Card.FIVE_HOUSE, Card.SIX_JADE])
    ])
    print("res: ", str(p.evolve()))


def all_combinations_test():
    cards = ImmutableCards([Card.MAHJONG, Card.TWO_HOUSE, Card.THREE_SWORD, Card.FOUR_HOUSE, Card.FOUR_SWORD,
             Card.FIVE_JADE, Card.SIX_HOUSE, Card.SIX_SWORD, Card.SEVEN_JADE, Card.SEVEN_HOUSE,
             Card.EIGHT_SWORD, Card.K_HOUSE, Card.DRAGON, Card.PHOENIX])

    small_cards = ImmutableCards([Card.MAHJONG, Card.TWO_HOUSE, Card.THREE_SWORD, Card.FOUR_HOUSE, Card.FOUR_SWORD,
                   Card.FIVE_JADE, Card.SIX_SWORD, Card.SEVEN_JADE])

    very_small_cards = ImmutableCards([Card.THREE_SWORD, Card.FOUR_HOUSE, Card.FOUR_SWORD])

    start_t = time()

    used_cards = small_cards
    all_combs = used_cards.all_combinations()
    print("time: ", time() - start_t)
    if True:
        print("cards: ")
        for c in sorted(used_cards):
            print("  ", c)

        print("possible combinations:")
        for comb in all_combs:
            print("->", sorted(comb))


def straight_gen_test():
    many_cards = ImmutableCards([Card.MAHJONG, Card.TWO_HOUSE, Card.THREE_SWORD, Card.FOUR_HOUSE, Card.FOUR_SWORD,
                            Card.FIVE_JADE, Card.SIX_HOUSE, Card.SIX_SWORD, Card.SEVEN_JADE, Card.SEVEN_HOUSE,
                            Card.EIGHT_SWORD, Card.K_HOUSE, Card.DRAGON, Card.PHOENIX])

    small_cards = ImmutableCards([Card.MAHJONG, Card.TWO_HOUSE, Card.THREE_SWORD, Card.FOUR_HOUSE, Card.FOUR_SWORD,
                                  Card.FIVE_JADE, Card.SIX_SWORD, Card.SEVEN_JADE])

    very_small_cards = ImmutableCards([Card.THREE_SWORD, Card.FOUR_HOUSE, Card.FOUR_SWORD])

    start_t = time()

    used_cards = small_cards

    straights = tuple(used_cards.all_straights_gen())

    print("time: ", time() - start_t)

    if True:
        print("cards: ")
        for c in sorted(used_cards):
            print("  ", c)

        print("straights:")
        for st in straights:
            print(", ".join([str(c) for c in sorted(st)]))

        print("nbr straights:", len(straights))
        print("nbr different straights:", len(set(straights)))


if __name__ == '__main__':
    straight_gen_test()
