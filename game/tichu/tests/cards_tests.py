import unittest
from collections import namedtuple

from tichu.cards.cards import Card as C
from tichu.cards.cards import *
from tichu.utils import flatten

if __name__ == '__main__':
    unittest.main()

CombTestCase = namedtuple("CTC", ["combinations", "othercards"])
TestCaseTuple = namedtuple("TestCase", ["cards", "combs"])


def comb_tc_to_tctuple(ctc):
    """
    CombTestCase -> TestCaseTuple
    """
    allcards = {c for c in ctc.othercards}
    for comb in ctc.combinations:
        allcards.update(comb.cards)
    assert isinstance(allcards, set)
    tct = TestCaseTuple(combs={comb for comb in ctc.combinations}, cards=allcards)
    return tct




class AllCombinationsTest(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_all_bombs_no_args(self):
        pass # TODO

    def test_squarebomb_no_args(self):
        squarebombs = [
            # cards containing no squarebombs:
            CombTestCase(combinations={},
                         othercards={C.TEN_HOUSE, C.FIVE_HOUSE, C.TEN_JADE, C.TEN_PAGODA, C.A_HOUSE, C.J_JADE, C.A_JADE, C.A_PAGODA}),

            CombTestCase(combinations={},
                         othercards={C.TWO_HOUSE, C.MAHJONG, C.TWO_JADE, C.TWO_PAGODA, C.A_PAGODA, C.Q_SWORD, C.Q_JADE, C.NINE_SWORD, C.FOUR_HOUSE, C.FIVE_HOUSE, C.NINE_PAGODA}),

            CombTestCase(combinations={},
                         othercards={C.DOG, C.DRAGON, C.MAHJONG, C.PHOENIX}),

            # cards containing exactly 1 squarebomb:
            CombTestCase(combinations={SquareBomb(C.A_HOUSE, C.A_SWORD, C.A_JADE, C.A_PAGODA)},
                         othercards={}),

            CombTestCase(combinations={SquareBomb(C.Q_HOUSE, C.Q_SWORD, C.Q_JADE, C.Q_PAGODA)},
                         othercards={C.FOUR_HOUSE, C.FIVE_HOUSE, C.NINE_PAGODA}),

            CombTestCase(combinations={SquareBomb(C.TWO_HOUSE, C.TWO_SWORD, C.TWO_JADE, C.TWO_PAGODA)},
                         othercards={C.FOUR_JADE, C.FIVE_SWORD, C.K_PAGODA}),

            CombTestCase(combinations={SquareBomb(C.TWO_HOUSE, C.TWO_SWORD, C.TWO_JADE, C.TWO_PAGODA)},
                         othercards={C.DOG, C.DRAGON, C.MAHJONG, C.PHOENIX}),

            CombTestCase(combinations={SquareBomb(C.TWO_HOUSE, C.TWO_SWORD, C.TWO_JADE, C.TWO_PAGODA)},
                         othercards={}),

            CombTestCase(combinations={SquareBomb(C.TEN_HOUSE, C.TEN_SWORD, C.TEN_JADE, C.TEN_PAGODA)},
                         othercards={C.A_HOUSE, C.A_SWORD, C.A_JADE, C.PHOENIX, C.NINE_PAGODA}),

            # cards containing exactly 2 squarebombs:
            CombTestCase(combinations={SquareBomb(C.TEN_HOUSE, C.TEN_SWORD, C.TEN_JADE, C.TEN_PAGODA), SquareBomb(C.A_HOUSE, C.A_SWORD, C.A_JADE, C.A_PAGODA)},
                         othercards={C.DOG, C.DRAGON, C.MAHJONG, C.PHOENIX}),

            CombTestCase(combinations={SquareBomb(C.TWO_HOUSE, C.TWO_SWORD, C.TWO_JADE, C.TWO_PAGODA), SquareBomb(C.Q_HOUSE, C.Q_SWORD, C.Q_JADE, C.Q_PAGODA)},
                         othercards={C.FOUR_HOUSE, C.FIVE_HOUSE, C.NINE_PAGODA}),
        ]

        for crds, expected_bombs in (comb_tc_to_tctuple(ctc) for ctc in squarebombs):
            cards = ImmutableCards(crds)
            sqbombs = list(cards.squarebombs())
            self.assertEqual(len(sqbombs), len(set(sqbombs)))  # generate no duplicates
            self.assertEqual(len(sqbombs), len(expected_bombs))
            for bomb in sqbombs:
                with self.subTest(bomb=bomb):
                    self.assertTrue(bomb.issubset(cards))
                    self.assertTrue(bomb in expected_bombs, "bomb: {}, bombs: {}".format(bomb, expected_bombs))

    def test_straightbomb_no_args(self):
        straightbombs = [
            # cards containing no straightbombs:
            CombTestCase(othercards={C.TEN_HOUSE, C.FIVE_HOUSE, C.TEN_JADE, C.TEN_PAGODA, C.A_HOUSE, C.J_JADE, C.A_JADE, C.A_PAGODA, C.DOG, C.DRAGON, C.MAHJONG, C.PHOENIX}, combinations={}),
            CombTestCase(othercards={C.TWO_HOUSE, C.MAHJONG, C.TWO_JADE, C.TWO_PAGODA, C.A_PAGODA, C.Q_SWORD, C.Q_JADE, C.NINE_SWORD, C.FOUR_HOUSE, C.FIVE_HOUSE, C.NINE_PAGODA}, combinations={}),
            CombTestCase(othercards={C.DOG, C.DRAGON, C.MAHJONG, C.PHOENIX}, combinations={}),
            
            # cards containing exactly 1 straightbomb:
            CombTestCase(othercards={C.A_HOUSE, C.A_SWORD, C.A_JADE},
                         combinations={StraightBomb.from_cards(C.A_PAGODA, C.K_PAGODA, C.Q_PAGODA, C.J_PAGODA, C.TEN_PAGODA)}),

            CombTestCase(othercards={C.K_SWORD, C.A_JADE, C.A_PAGODA, C.PHOENIX},
                         combinations={StraightBomb.from_cards(C.Q_HOUSE, C.J_HOUSE, C.TEN_HOUSE, C.NINE_HOUSE, C.EIGHT_HOUSE)}),

            CombTestCase(othercards={C.K_SWORD, C.A_JADE, C.A_PAGODA, C.DOG, C.DRAGON, C.MAHJONG, C.PHOENIX},
                         combinations={StraightBomb.from_cards(C.Q_HOUSE, C.J_HOUSE, C.TEN_HOUSE, C.NINE_HOUSE, C.EIGHT_HOUSE)}),

            CombTestCase(othercards={C.Q_HOUSE, C.K_SWORD, C.A_JADE, C.A_PAGODA, C.DOG, C.DRAGON, C.MAHJONG, C.PHOENIX},
                         combinations={StraightBomb.from_cards(C.SIX_HOUSE, C.FIVE_HOUSE, C.FOUR_HOUSE, C.THREE_HOUSE, C.TWO_HOUSE)}),  # Mahjong can't be part of straightbomb, neither can phoenix
            
            # cards containing exactly 2 straightbombs:
            CombTestCase(othercards={C.Q_HOUSE, C.K_SWORD, C.A_JADE, C.A_PAGODA, C.DOG, C.DRAGON, C.MAHJONG, C.PHOENIX},
                         combinations={StraightBomb.from_cards(C.Q_HOUSE, C.J_HOUSE, C.TEN_HOUSE, C.NINE_HOUSE, C.EIGHT_HOUSE),
                                       StraightBomb.from_cards(C.TWO_HOUSE, C.THREE_HOUSE, C.FOUR_HOUSE, C.FIVE_HOUSE, C.SIX_HOUSE)}),

            CombTestCase(othercards={C.K_SWORD, C.A_JADE, C.A_PAGODA, C.DOG, C.DRAGON, C.MAHJONG, C.PHOENIX},
                         combinations={StraightBomb.from_cards(C.Q_HOUSE, C.J_HOUSE, C.TEN_HOUSE, C.NINE_HOUSE, C.EIGHT_HOUSE),
                                       StraightBomb.from_cards(C.J_JADE, C.TEN_JADE, C.NINE_JADE, C.EIGHT_JADE, C.SEVEN_JADE)}),

            CombTestCase(othercards={C.K_SWORD, C.A_JADE, C.A_PAGODA, C.TEN_JADE, C.NINE_JADE, C.EIGHT_JADE, C.SEVEN_JADE, C.DOG, C.DRAGON, C.MAHJONG, C.PHOENIX},
                         combinations={StraightBomb.from_cards(C.Q_HOUSE, C.J_HOUSE, C.TEN_HOUSE, C.NINE_HOUSE, C.EIGHT_HOUSE),
                                       StraightBomb.from_cards(C.SIX_HOUSE, C.FIVE_HOUSE, C.FOUR_HOUSE, C.THREE_HOUSE, C.TWO_HOUSE)}),

            # cards containing exactly 4 straightbombs:
            CombTestCase(othercards={C.DOG, C.DRAGON, C.MAHJONG, C.PHOENIX},  # one of length 6 -> makes 3 different bombs & another of len 5
                         combinations={StraightBomb.from_cards(C.Q_HOUSE, C.J_HOUSE, C.TEN_HOUSE, C.NINE_HOUSE, C.EIGHT_HOUSE),
                                       StraightBomb.from_cards(C.J_HOUSE, C.TEN_HOUSE, C.NINE_HOUSE, C.EIGHT_HOUSE, C.SEVEN_HOUSE),
                                       StraightBomb.from_cards(C.Q_HOUSE, C.J_HOUSE, C.TEN_HOUSE, C.NINE_HOUSE, C.EIGHT_HOUSE, C.SEVEN_HOUSE),
                                       StraightBomb.from_cards(C.J_JADE, C.TEN_JADE, C.NINE_JADE, C.EIGHT_JADE, C.SEVEN_JADE)}),
        ]
        for crds, expected_bombs in (comb_tc_to_tctuple(ctc) for ctc in straightbombs):
            cards = ImmutableCards(crds)
            strbombs = list(cards.straightbombs())
            self.assertEqual(len(strbombs), len(set(strbombs)))  # generate no duplicates
            self.assertEqual(len(strbombs), len(expected_bombs), "\nstrbombs      : {}, \nexpected_bombs: {}".format(sorted(strbombs), sorted(expected_bombs)))
            for bomb in strbombs:
                with self.subTest(bomb=bomb):
                    self.assertTrue(bomb.issubset(cards))
                    self.assertTrue(bomb in expected_bombs, "bomb: {} in bombs: {}".format(bomb, expected_bombs))

    def test_single_no_args(self):
        # TODO Fails because singles now does not return 2 cards with the same cardvalues
        singles_ctc = [
            CombTestCase(othercards={},
                         combinations={Single(c) for c in {c for c in C}}),  # test all cards
        ]

        for crds, expected_singles in (comb_tc_to_tctuple(ctc) for ctc in singles_ctc):
            cards = ImmutableCards(crds)
            singles = list(cards.singles())
            self.assertEqual(len(singles), len(set(singles)))  # generate no duplicates
            self.assertEqual(len(singles), len(expected_singles), "\nsingles      : {}, \nexpected_singles: {}".format(singles, expected_singles))
            for sing in singles:
                with self.subTest(single=sing):
                    self.assertTrue(sing.issubset(cards))
                    self.assertTrue(sing in expected_singles, "single: {} in expected_singles: {}".format(sing, expected_singles))
                    self.assertEqual(C.PHOENIX is sing.card, sing.is_phoenix())
                    self.assertEqual(C.PHOENIX in sing, sing.is_phoenix())
                    self.assertTrue(sing.card in sing)
                    self.assertTrue(sing.contains_cardval(sing.card.card_value))
                    self.assertEqual(sing.height, sing.card.card_height)
                    # test phoenix height change
                    for k in range(2, 15):
                        with self.subTest(k=k):
                            sing.set_phoenix_height(k)
                            if C.PHOENIX is sing.card:
                                self.assertEqual(sing.height, k)
                            else:
                                self.assertEqual(sing.height, sing.card.card_height, "sing: {}, k:{}".format(sing, k))
                    for k in [None, C.PHOENIX, C.TEN_HOUSE, sing]:
                        with self.subTest(k=k):
                            with self.assertRaises(TypeError):
                                sing.set_phoenix_height(k)
                    for k in [-1, 0, 1, 1.8, 1.2, 15, 15.1, 18, 100, -10]:
                        with self.subTest(i=k):
                            with self.assertRaises(ValueError):
                                sing.set_phoenix_height(k)

    def test_pair_no_args(self):
        # test normal pair creation, should not raise exception:
        all_pairs = {Pair(c1, c2) for c1 in {c for c in C} for c2 in {c for c in C} if c1 != c2 and c1.card_value is c2.card_value}

        make_pair_fun = lambda c1, c2: Pair(c1, c2)
        self.assertRaises(ValueError, make_pair_fun, C.TWO_JADE, C.TWO_JADE)  # two same cards
        self.assertRaises(ValueError, make_pair_fun, C.PHOENIX, C.DRAGON)  # phoenix with special card
        self.assertRaises(ValueError, make_pair_fun, C.TWO_JADE, C.FIVE_JADE)  # two not same valued cards
        self.assertRaises(ValueError, make_pair_fun, C.TWO_JADE, C.DRAGON)  # card with special card


        pairs_ctc = [
            CombTestCase(othercards={C.K_PAGODA, C.FIVE_HOUSE, C.J_HOUSE, C.Q_SWORD},
                         combinations={Pair(C.A_PAGODA, C.A_JADE)}),
            CombTestCase(othercards={},
                         combinations={Pair(C.PHOENIX, c1) for c1 in C if c1.suit is CardSuit.JADE}),  # Phoenix pairs
            CombTestCase(othercards={C.DOG, C.DRAGON, C.MAHJONG},
                         combinations={Pair(C.PHOENIX, c1) for c1 in C if c1.suit is CardSuit.JADE}),  # Phoenix pairs with special cards
            CombTestCase(othercards={c for c in C if c.suit is CardSuit.JADE},
                         combinations={}),  # no pairs when only one suit and Phoenix not present
            CombTestCase(othercards={C.A_JADE, C.Q_SWORD, C.J_HOUSE, C.TEN_HOUSE, C.NINE_HOUSE, C.EIGHT_HOUSE, C.SEVEN_PAGODA, C.SIX_SWORD, C.FIVE_JADE, C.FOUR_JADE, C.THREE_PAGODA, C.TWO_JADE, C.MAHJONG, C.DRAGON, C.DOG},
                         combinations={}),  # no pairs when no same valued and Phoenix not present
        ]

        for crds, expected_pairs in (comb_tc_to_tctuple(ctc) for ctc in pairs_ctc):
            with self.subTest(msg="\ncrds: {}, \nexpected_pairs: {}".format(crds, expected_pairs)):
                cards = ImmutableCards(crds)
                pairs = list(cards.pairs())
                self.assertEqual(len(pairs), len(set(pairs)))  # generate no duplicates
                self.assertEqual(len(pairs), len(expected_pairs), "\npairs: {}, \nexpected_pairs: {}".format(pairs, expected_pairs))
                for p in pairs:
                    with self.subTest(msg="pair: {} in expected_pairs: {}".format(p, expected_pairs)):
                        self.assertTrue(p.issubset(cards))
                        self.assertTrue(p in expected_pairs)
                        self.assertEqual(C.PHOENIX in p.cards, p.contains_phoenix())
                        self.assertTrue(len(p.cards) == 2)
                        self.assertEqual(p.height, max(p.cards).card_height)

    def test_trio_no_args(self):
        # test normal trio creation, should not raise exception:
        all_trios = {Trio(c1, c2, c3) for c1 in {c for c in C} for c2 in {c for c in C} for c3 in {c for c in C}
                     if((c1 is not c2) and (c2 is not c3) and (c3 is not c1) and c1.card_value is c2.card_value is c3.card_value)}

        make_trio_fun = lambda c1, c2, c3: Trio(c1, c2, c3)
        self.assertRaises(ValueError, make_trio_fun, C.TWO_JADE, C.TWO_JADE, C.TWO_SWORD)  # two same cards
        self.assertRaises(ValueError, make_trio_fun, C.PHOENIX, C.DRAGON, C.TWO_SWORD)  # phoenix with special card
        self.assertRaises(ValueError, make_trio_fun, C.PHOENIX, C.PHOENIX, C.TWO_SWORD)  # 2 phoenixes
        self.assertRaises(ValueError, make_trio_fun, C.TWO_JADE, C.FIVE_JADE, C.TWO_SWORD)  # two not same valued cards
        self.assertRaises(ValueError, make_trio_fun, C.TWO_JADE, C.DRAGON, C.TWO_SWORD)  # card with special card

        trios_ctc = [
            CombTestCase(othercards={C.K_PAGODA, C.FIVE_HOUSE, C.J_HOUSE, C.Q_SWORD},
                         combinations={Trio(C.A_PAGODA, C.A_JADE, C.A_SWORD)}),
            CombTestCase(othercards={},
                         combinations={Trio(C.PHOENIX, c1, c2) for c1 in C for c2 in C if c1.suit is CardSuit.JADE and c2.suit is CardSuit.HOUSE and c1.card_value is c2.card_value}),  # Phoenix trios
            CombTestCase(othercards={C.DOG, C.DRAGON, C.MAHJONG},
                         combinations={Trio(C.PHOENIX, c1, c2) for c1 in C for c2 in C if c1.suit is CardSuit.JADE and c2.suit is CardSuit.HOUSE and c1.card_value is c2.card_value}),  # Phoenix pairs with special cards
            CombTestCase(othercards={c for c in C if c.suit is CardSuit.JADE},
                         combinations={}),  # no pairs when only one suit and Phoenix not present
            CombTestCase(othercards={C.A_JADE, C.Q_SWORD, C.J_HOUSE, C.TEN_HOUSE, C.NINE_HOUSE, C.EIGHT_HOUSE, C.SEVEN_PAGODA, C.SIX_SWORD, C.FIVE_JADE, C.FOUR_JADE, C.THREE_PAGODA, C.TWO_JADE, C.MAHJONG, C.DRAGON, C.DOG},
                         combinations={}),  # no pairs when no same valued and Phoenix not present
        ]

        for crds, expected_trios in (comb_tc_to_tctuple(ctc) for ctc in trios_ctc):
            with self.subTest(msg="\ncrds: {}, \nexpected_trios: {}".format(crds, expected_trios)):
                cards = ImmutableCards(crds)
                trios = list(cards.trios())
                self.assertEqual(len(trios), len(set(trios)))  # generate no duplicates
                self.assertEqual(len(trios), len(expected_trios), "\ncards: {} \ntrios: {}, \nexpected_trios: {}".format(crds, trios, expected_trios))
                for trio in trios:
                    with self.subTest(msg="trio: {} in expected_trios: {}".format(trio, expected_trios)):
                        self.assertTrue(trio.issubset(cards))
                        self.assertTrue(trio in expected_trios, "trio: {} in expected_trios: {}".format(trio, expected_trios))
                        self.assertEqual(C.PHOENIX in trio.cards, trio.contains_phoenix())
                        self.assertTrue(len(trio.cards) == 3)
                        self.assertEqual(trio.height, max(trio.cards).card_height)

    def test_straight_no_args(self):

        make_straight_fun = lambda cards, ph: Straight(cards, phoenix_as=ph)
        self.assertRaises(ValueError, make_straight_fun, [C.TWO_JADE, C.TWO_JADE, C.THREE_SWORD, C.FOUR_JADE, C.FIVE_HOUSE, C.SIX_SWORD], None)  # two same cards
        self.assertRaises(ValueError, make_straight_fun, [C.PHOENIX, C.DRAGON, C.TWO_JADE, C.THREE_SWORD, C.FOUR_JADE, C.FIVE_HOUSE, C.SIX_SWORD], C.SEVEN_HOUSE)  # phoenix with special card
        self.assertRaises(AssertionError, make_straight_fun, [C.PHOENIX, C.PHOENIX, C.TWO_JADE, C.THREE_SWORD, C.FOUR_JADE, C.FIVE_HOUSE, C.SIX_SWORD], C.SEVEN_HOUSE)  # 2 phoenixes
        self.assertRaises(ValueError, make_straight_fun, [C.TWO_JADE, C.THREE_SWORD, C.A_JADE, C.FIVE_HOUSE, C.SIX_SWORD], None)  # not a straight
        self.assertRaises(ValueError, make_straight_fun, [C.TWO_JADE, C.DOG, C.FOUR_JADE, C.FIVE_HOUSE, C.SIX_SWORD], None)  # cards with special card
        self.assertRaises(ValueError, make_straight_fun, [C.TWO_JADE, C.THREE_SWORD, C.FOUR_JADE, C.FIVE_HOUSE], None)  # too short
        self.assertRaises(ValueError, make_straight_fun, [C.MAHJONG, C.TWO_JADE, C.THREE_SWORD, C.FIVE_HOUSE, C.SIX_SWORD], None)  # mahjong but not a straight

        straights_ctc = [
            CombTestCase(othercards={C.K_PAGODA, C.FIVE_HOUSE, C.J_HOUSE, C.Q_SWORD},
                         combinations={Straight([C.TWO_JADE, C.THREE_SWORD, C.FOUR_JADE, C.FIVE_HOUSE, C.SIX_SWORD])}),
            CombTestCase(othercards={},
                         combinations={Straight([C.MAHJONG, C.TWO_JADE, C.THREE_SWORD, C.FOUR_JADE, C.FIVE_HOUSE])}),  # mahjong
            CombTestCase(othercards={C.DOG, C.DRAGON},
                         combinations={Straight([C.MAHJONG, C.TWO_JADE, C.THREE_SWORD, C.FOUR_JADE, C.FIVE_HOUSE])}),
            CombTestCase(othercards={},
                         combinations={Straight([C.MAHJONG, C.TWO_JADE, C.THREE_SWORD, C.FOUR_JADE, C.FIVE_HOUSE]),
                                       Straight([C.EIGHT_HOUSE, C.NINE_HOUSE, C.TEN_PAGODA, C.J_HOUSE, C.Q_SWORD])}),  # two disjoint straights
            CombTestCase(othercards={C.DOG, C.DRAGON},
                         combinations={Straight([C.MAHJONG, C.TWO_JADE, C.THREE_SWORD, C.FOUR_JADE, C.FIVE_HOUSE]),
                                       Straight([C.EIGHT_HOUSE, C.NINE_HOUSE, C.TEN_PAGODA, C.J_HOUSE, C.Q_SWORD])}),  # two disjoint straights with 'noise'

            CombTestCase(othercards={C.A_JADE, C.Q_SWORD, C.J_HOUSE, C.NINE_HOUSE, C.DRAGON, C.DOG},
                         combinations={Straight([C.SEVEN_PAGODA, C.SIX_SWORD, C.FIVE_JADE, C.FOUR_JADE, C.THREE_PAGODA, C.TWO_JADE, C.MAHJONG]),  # 7
                                       Straight([C.SEVEN_PAGODA, C.SIX_SWORD, C.FIVE_JADE, C.FOUR_JADE, C.THREE_PAGODA, C.TWO_JADE]),             # 6
                                       Straight([C.SIX_SWORD, C.FIVE_JADE, C.FOUR_JADE, C.THREE_PAGODA, C.TWO_JADE, C.MAHJONG]),                  # 6
                                       Straight([C.FIVE_JADE, C.FOUR_JADE, C.THREE_PAGODA, C.TWO_JADE, C.MAHJONG]),                               # 5
                                       Straight([C.SEVEN_PAGODA, C.SIX_SWORD, C.FIVE_JADE, C.FOUR_JADE, C.THREE_PAGODA]),                         # 5
                                       Straight([C.SIX_SWORD, C.FIVE_JADE, C.FOUR_JADE, C.THREE_PAGODA, C.TWO_JADE]),                             # 5
                                      }),  # a length 7 straight and all shorter ones
            # Phoenix
            CombTestCase(othercards={},
                         combinations={Straight([C.MAHJONG, C.PHOENIX, C.THREE_SWORD, C.FOUR_JADE, C.FIVE_HOUSE], C.TWO_SWORD)}),  # simple phoenix (note that the phoenix is always replaced with Sword in the straights() method)

        ]

        for crds, expected_straights in (comb_tc_to_tctuple(ctc) for ctc in straights_ctc):
            with self.subTest(msg="\ncrds: {}, \nexpected_straights: {}".format(crds, expected_straights)):
                cards = ImmutableCards(crds)
                straights = list(cards.straights())
                self.assertEqual(len(straights), len(set(straights)))  # generate no duplicates
                self.assertEqual(len(straights), len(expected_straights), "\ncards: {} \nstraights: {}, \nexpected_straights: {}".format(crds, straights, expected_straights))
                for st in straights:
                    with self.subTest(msg="st: {} in expected_straights: {}".format(st, expected_straights)):
                        self.assertTrue(st.issubset(cards))
                        self.assertTrue(st in expected_straights, "st: {} in expected_straights: {}".format(st, expected_straights))
                        self.assertEqual(C.PHOENIX in st.cards, st.contains_phoenix())
                        self.assertTrue(len(st.cards) >= 5)
                        self.assertEqual(st.height, max(st.cards).card_height)

        # correct nbr of straights
        cards = [
            ImmutableCards([C.MAHJONG, C.TWO_JADE, C.THREE_SWORD, C.FOUR_JADE, C.FIVE_HOUSE, C.SIX_SWORD, C.SEVEN_HOUSE, C.EIGHT_HOUSE, C.NINE_HOUSE, C.TEN_PAGODA, C.J_HOUSE, C.Q_SWORD]),
            ImmutableCards([C.MAHJONG, C.TWO_JADE, C.THREE_SWORD, C.FOUR_JADE, C.FIVE_HOUSE, C.SIX_SWORD, C.SEVEN_HOUSE, C.EIGHT_HOUSE, C.NINE_HOUSE, C.TEN_PAGODA, C.J_HOUSE, C.Q_SWORD, C.K_PAGODA, C.A_SWORD]),
            ImmutableCards([C.TWO_JADE, C.THREE_SWORD, C.FOUR_JADE, C.FIVE_HOUSE,  C.SIX_SWORD, C.SEVEN_HOUSE, C.EIGHT_HOUSE]),
            ]

        for imm_c in cards:
            straights = list(imm_c.straights())
            expected_nbr = sum([len(imm_c)-k+1 for k in range(5, len(imm_c)+1)]) # eg. if there are 7 cards, we get 7-7+1 + 7-6+1 + 7-5+1 = 3+2+1 = 6 different straights
            self.assertEqual(len(straights), expected_nbr, "\ncards: {}\nstraights: {}".format(imm_c, straights))

        # phoenix & correct nbr of straights
        cards = [
            ImmutableCards([C.MAHJONG, C.TWO_JADE, C.THREE_SWORD, C.FOUR_JADE, C.FIVE_HOUSE, C.PHOENIX, C.SEVEN_HOUSE, C.EIGHT_HOUSE, C.NINE_HOUSE, C.TEN_PAGODA, C.J_HOUSE]),  # phoenix in the middle
            ImmutableCards([C.MAHJONG, C.TWO_JADE, C.THREE_SWORD, C.FOUR_JADE, C.FIVE_HOUSE, C.SIX_SWORD, C.SEVEN_HOUSE, C.EIGHT_HOUSE, C.NINE_HOUSE, C.TEN_PAGODA, C.J_HOUSE, C.Q_SWORD, C.K_PAGODA, C.A_SWORD, C.PHOENIX]),  # phoenix "superfluous"
            ImmutableCards([C.TWO_JADE, C.THREE_SWORD, C.FOUR_JADE, C.FIVE_HOUSE,  C.SIX_SWORD, C.SEVEN_HOUSE, C.EIGHT_HOUSE, C.PHOENIX]),  # phoenix useful only at the end
            ImmutableCards([C.PHOENIX, C.NINE_HOUSE, C.TEN_PAGODA, C.J_HOUSE, C.Q_SWORD, C.K_PAGODA, C.A_SWORD]),  # phoenix useful only at the beginning
            ImmutableCards([C.THREE_SWORD, C.FOUR_JADE, C.FIVE_HOUSE,  C.SIX_SWORD, C.SEVEN_HOUSE, C.EIGHT_HOUSE, C.PHOENIX]),  # phoenix useful at both ends end
            ]
        straights0 = set(cards[0].straights())
        straights1 = set(cards[1].straights())
        straights2 = set(cards[2].straights())
        straights3 = set(cards[3].straights())
        straights4 = set(cards[4].straights())
        expected_nbr0 = sum([11-k+1 for k in range(5, 12)]) + 4+5 +2  # sum([11-k+1 for k in range(5, 12)]) for phoenix in the middle (includes 2 without phoenix), 4+5 for phoenix replacing any card (not mahjong), 2 for phoenix as Q
        self.assertEqual(len(straights0), expected_nbr0, "found straights: \n{}".format("\n".join(str(st) for st in sorted(straights0, key=lambda s: len(s)))))
        expected_nbr1 = sum([14-k+1 for k in range(5, 15)]) + sum([(14-k+1)*k for k in range(5, 15)]) - (14-5+1)  # sum([14-k+1 for k in range(5, 15)]) without phoenix + sum([(14-k+1)*k for k in range(5, 15)]) phoenix replacing a card in each straight -(14-5+1) phoenix can't replace mahjong (there are 10 straights starting from 1 without phoenix)
        self.assertEqual(len(straights1), expected_nbr1, "found straights: \n{}".format("\n".join(str(st) for st in sorted(straights1, key=lambda s: len(s)))))
        expected_nbr2 = sum([7-k+1 for k in range(5, 8)]) + sum([(7-k+1)*k for k in range(5, 8)]) + 4  # sum([7-k+1 for k in range(5, 8)]) without phoenix + sum([(7-k+1)*k for k in range(5, 8)]) phoenix replacing a card in each straight + 4 phoenix as Q
        self.assertEqual(len(straights2), expected_nbr2, "found straights: \n{}".format("\n".join(str(st) for st in sorted(straights2, key=lambda s: len(s)))))
        expected_nbr3 = sum([6-k+1 for k in range(5, 7)]) + sum([(6-k+1)*k for k in range(5, 7)]) + 3  # sum([6-k+1 for k in range(5, 7)]) without phoenix + sum([(6-k+1)*k for k in range(5, 7)]) phoenix replacing a card in each straight + 3 phoenix as TWO
        self.assertEqual(len(straights3), expected_nbr3, "found straights: \n{}".format("\n".join(str(st) for st in sorted(straights3, key=lambda s: len(s)))))
        expected_nbr4 = sum([6-k+1 for k in range(5, 7)]) + sum([(6-k+1)*k for k in range(5, 7)]) + 3 + 3  # sum([6-k+1 for k in range(5, 7)]) without phoenix + sum([(6-k+1)*k for k in range(5, 7)]) phoenix replacing a card in each straight + 3 phoenix as TWO + 3 phoenix as NINE
        self.assertEqual(len(straights4), expected_nbr4, "found straights: \n{}".format("\n".join(str(st) for st in sorted(straights4, key=lambda s: len(s)))))

    def test_fullhouse_no_args(self):
        # test normal trio creation, should not raise exception:
        all_pairs = {Pair(c1, c2) for c1 in {c for c in C} for c2 in {c for c in C} if c1 != c2 and c1.card_value is c2.card_value}
        all_trios = {Trio(c1, c2, c3) for c1 in {c for c in C} for c2 in {c for c in C} for c3 in {c for c in C}
                     if((c1 is not c2) and (c2 is not c3) and (c3 is not c1) and c1.card_value is c2.card_value is c3.card_value)}
        all_fullhouses = {FullHouse(p, t) for p in all_pairs for t in all_trios
                          if(len(p.cards.union(t.cards)) == 5)}
        all_fullhouses_from_cards = {FullHouse.from_cards(fh.cards) for fh in all_fullhouses}
        self.assertSetEqual(all_fullhouses, all_fullhouses_from_cards)

        make_fullhouse_fun = lambda p, t: FullHouse(p, t)
        make_fullhouse_from_cards = lambda cards: FullHouse.from_cards(cards)
        self.assertRaises(ValueError, make_fullhouse_fun, Pair(C.TWO_JADE, C.TWO_HOUSE), Trio(C.TWO_SWORD, C.TWO_PAGODA, C.TWO_JADE))  # two same cards
        self.assertRaises(ValueError, make_fullhouse_fun, Pair(C.TWO_JADE, C.PHOENIX), Trio(C.PHOENIX, C.THREE_PAGODA, C.THREE_JADE))  # 2 phoenixes
        self.assertRaises(ValueError, make_fullhouse_fun, Pair(C.TWO_JADE, C.PHOENIX), Trio(C.PHOENIX, C.TWO_SWORD, C.TWO_PAGODA))  # 2 phoenixes
        self.assertRaises(ValueError, make_fullhouse_from_cards, [C.A_JADE, C.A_SWORD, C.A_HOUSE, C.K_JADE, C.K_SWORD, C.K_HOUSE])  # too many
        self.assertRaises(ValueError, make_fullhouse_from_cards, [C.A_JADE, C.A_SWORD, C.A_HOUSE, C.K_JADE])  # too few
        self.assertRaises(ValueError, make_fullhouse_from_cards, [C.A_JADE, C.A_SWORD, C.A_HOUSE, C.K_JADE, C.Q_SWORD])  # not fullhouse
        self.assertRaises(ValueError, make_fullhouse_from_cards, [C.A_JADE, C.J_SWORD, C.A_HOUSE, C.K_JADE, C.K_SWORD])  # not fullhouse
        # self.assertRaises(ValueError, make_fullhouse_from_cards, [C.PHOENIX, C.A_SWORD, C.A_HOUSE, C.K_JADE, C.PHOENIX])  # 2 phoenixes -> cant make from cards with phoenix
        # self.assertRaises(ValueError, make_fullhouse_from_cards, [C.PHOENIX, C.A_SWORD, C.A_HOUSE, C.K_JADE, C.Q_SWORD])  # phoenix but not fullhouse -> cant make from cards with phoenix

        fullhouses_ctc = [
            CombTestCase(othercards={C.TEN_PAGODA, C.FIVE_HOUSE, C.J_HOUSE, C.Q_SWORD},
                         combinations={FullHouse.from_cards([C.A_JADE, C.A_SWORD, C.A_HOUSE, C.K_JADE, C.K_SWORD])}),
            CombTestCase(othercards={},
                         combinations={FullHouse.from_cards([C.A_JADE, C.A_SWORD, C.A_HOUSE, C.K_JADE, C.K_SWORD]),
                                       FullHouse.from_cards([C.A_JADE, C.A_SWORD, C.A_HOUSE, C.TEN_JADE, C.TEN_HOUSE]),
                                       FullHouse.from_cards([C.A_JADE, C.A_SWORD, C.A_HOUSE, C.J_JADE, C.J_SWORD]),
                                       FullHouse.from_cards([C.TEN_JADE, C.TEN_SWORD, C.TEN_HOUSE, C.J_JADE, C.J_SWORD]),
                                       FullHouse.from_cards([C.TEN_JADE, C.TEN_SWORD, C.TEN_HOUSE, C.K_JADE, C.K_SWORD]),
                                       FullHouse.from_cards([C.TEN_JADE, C.TEN_SWORD, C.TEN_HOUSE, C.A_JADE, C.A_SWORD])}),

            CombTestCase(othercards={},
                         combinations={FullHouse(trio=Trio(C.PHOENIX, C.A_JADE, C.A_HOUSE), pair=Pair(C.K_JADE, C.K_SWORD)),
                                       FullHouse(trio=Trio(C.PHOENIX, C.K_JADE, C.K_SWORD), pair=Pair(C.A_JADE, C.A_HOUSE))}),  # 1 phoenix
            CombTestCase(othercards={C.A_JADE, C.A_SWORD, C.Q_SWORD, C.J_HOUSE, C.J_PAGODA,C.TEN_HOUSE, C.NINE_HOUSE, C.EIGHT_HOUSE, C.SEVEN_PAGODA, C.SIX_SWORD, C.FIVE_JADE, C.FOUR_JADE, C.FOUR_HOUSE, C.THREE_PAGODA, C.TWO_JADE, C.MAHJONG, C.DRAGON, C.DOG},
                         combinations={}),  # no fullhouse
            CombTestCase(othercards={C.A_JADE, C.A_SWORD, C.A_PAGODA, C.Q_SWORD, C.J_HOUSE, C.TEN_HOUSE, C.NINE_HOUSE, C.EIGHT_HOUSE, C.SEVEN_PAGODA, C.SIX_SWORD, C.FIVE_JADE, C.FOUR_JADE, C.THREE_PAGODA, C.TWO_JADE, C.MAHJONG, C.DRAGON, C.DOG},
                         combinations={}),  # no fullhouse
        ]

        for crds, expected_fullhouses in (comb_tc_to_tctuple(ctc) for ctc in fullhouses_ctc):
            with self.subTest(msg="\ncrds: {}, \nexpected_trios: {}".format(crds, expected_fullhouses)):
                cards = ImmutableCards(crds)
                fullhouses = list(cards.fullhouses())
                self.assertEqual(len(fullhouses), len(set(fullhouses)))  # generate no duplicates
                self.assertEqual(len(fullhouses), len(expected_fullhouses), "\ncards: {} \nfullhouses: {}, \nexpected_fullhouses: {}".format(crds, fullhouses, expected_fullhouses))
                for fh in fullhouses:
                    with self.subTest(msg="fh: {} in expected_fullhouses: {}".format(fh, expected_fullhouses)):
                        self.assertTrue(fh.issubset(cards))
                        self.assertEqual(C.PHOENIX in fh.cards, fh.contains_phoenix())
                        self.assertTrue(len(fh.cards) == 5)
                        self.assertEqual(fh.height, fh.trio.height)

    def test_pairstep_no_args(self):

        pairs = [None, None,
                 Pair(C.TWO_PAGODA, C.TWO_JADE),  # 2
                 Pair(C.THREE_PAGODA, C.THREE_JADE),
                 Pair(C.FOUR_PAGODA, C.FOUR_JADE),
                 Pair(C.FIVE_PAGODA, C.FIVE_JADE),
                 Pair(C.SIX_PAGODA, C.SIX_JADE),
                 Pair(C.SEVEN_PAGODA, C.SEVEN_JADE),
                 Pair(C.EIGHT_PAGODA, C.EIGHT_JADE),
                 Pair(C.NINE_PAGODA, C.NINE_JADE),
                 Pair(C.TEN_PAGODA, C.TEN_JADE),  # 10
                 Pair(C.J_PAGODA, C.J_JADE),  # 11
                 Pair(C.Q_PAGODA, C.Q_JADE),  # 12
                 Pair(C.K_PAGODA, C.K_JADE),  # 13
                 Pair(C.A_PAGODA, C.A_JADE),  # 14
                 ]
        make_ps_fun = lambda pairs: PairSteps(pairs)
        make_ps_from_cards = lambda cards: PairSteps.from_cards(cards)
        self.assertRaises(ValueError, make_ps_fun, [pairs[5], Pair(C.FIVE_PAGODA, C.FIVE_HOUSE)])  # two same cards and no pairstep
        self.assertRaises(ValueError, make_ps_fun, [pairs[5], Pair(C.PHOENIX, C.SIX_HOUSE), Pair(C.PHOENIX, C.SEVEN_HOUSE)])  # 2 phoenixes
        self.assertRaises(ValueError, make_ps_fun, [pairs[3], pairs[4], pairs[6]])  # not a ps, gap
        self.assertRaises(ValueError, make_ps_fun, [pairs[3], pairs[4], pairs[5], pairs[6], pairs[6]])  # not a ps, duplicated pairs
        self.assertRaises(TypeError, make_ps_fun, [pairs[8], Trio(C.FOUR_JADE, C.FOUR_HOUSE, C.FOUR_SWORD)])  # not pairs as argument
        self.assertRaises(ValueError, make_ps_fun, [pairs[3]])  # too short
        self.assertRaises(ValueError, make_ps_from_cards, [*pairs[3].cards, *pairs[4].cards, *pairs[6].cards])  # not ps, gap
        self.assertRaises(ValueError, make_ps_from_cards, [*pairs[3].cards, *pairs[4].cards, *pairs[5].cards, *pairs[5].cards])  # not ps, duplicated pairs
        self.assertRaises(ValueError, make_ps_from_cards, [*pairs[3].cards, *pairs[4].cards, *pairs[5].cards, C.SIX_SWORD])  # not ps, single card
        self.assertRaises(ValueError, make_ps_from_cards, [*pairs[3].cards, *pairs[4].cards, *pairs[5].cards, C.MAHJONG, C.MAHJONG])  # not ps, special card

        ps_ctc = [
            CombTestCase(othercards={C.K_PAGODA, C.FIVE_HOUSE, C.J_HOUSE, C.Q_SWORD},
                         combinations={PairSteps(pairs[7:9])}),  # len 2
            CombTestCase(othercards={},
                         combinations={PairSteps(pairs[10:13]), PairSteps(pairs[10:12]), PairSteps(pairs[11:13])}),  # len 3
            CombTestCase(othercards={C.DOG, C.DRAGON},
                         combinations={PairSteps(pairs[7:9]), PairSteps(pairs[4:6]), PairSteps(pairs[11:13])}),  # 3 disjoint of len 2
            CombTestCase(othercards={},
                         combinations={PairSteps([Pair(C.PHOENIX, C.TWO_JADE), pairs[3]]),
                                       PairSteps([Pair(C.PHOENIX, C.J_JADE), pairs[12]]),
                                       PairSteps([Pair(C.PHOENIX, C.Q_JADE), pairs[11]]),
                                       PairSteps(pairs[11:13])}),  # phoenix

            CombTestCase(othercards={C.DRAGON, C.DOG},
                         combinations={PairSteps(pairs[6:11]),
                                       PairSteps(pairs[6:10]),
                                       PairSteps(pairs[6:9]),
                                       PairSteps(pairs[6:8]),
                                       PairSteps(pairs[7:11]),
                                       PairSteps(pairs[7:10]),
                                       PairSteps(pairs[7:9]),
                                       PairSteps(pairs[8:11]),
                                       PairSteps(pairs[8:10]),
                                       PairSteps(pairs[9:11]),
                                       }),
        ]

        for crds, expected_ps in (comb_tc_to_tctuple(ctc) for ctc in ps_ctc):
            with self.subTest(msg="\ncrds: {}, \nexpected_ps: {}".format(crds, expected_ps)):
                cards = ImmutableCards(crds)
                pairsteps = list(cards.pairsteps())
                self.assertEqual(len(pairsteps), len(set(pairsteps)), "\ncards: {} \npairsteps: {}, \nexpected_ps: {}".format(crds, pairsteps, expected_ps))  # generate no duplicates
                self.assertEqual(len(pairsteps), len(expected_ps), "\ncards: {} \npairsteps: {}, \nexpected_ps: {}".format(crds, pairsteps, expected_ps))
                for ps in pairsteps:
                    with self.subTest(msg="ps: {} in expected_ps: {}".format(ps, expected_ps)):
                        self.assertTrue(ps.issubset(cards))
                        self.assertEqual(C.PHOENIX in ps.cards, ps.contains_phoenix())
                        self.assertTrue(len(ps.cards) >= 4 and len(ps.cards) %2 == 0)
                        self.assertEqual(ps.height, max(ps.cards).card_height)

        # correct nbr of ps
        cards = [
            ImmutableCards(list(flatten(pairs[2:10]))),
            ImmutableCards(list(flatten(pairs[2:4]))),
            ImmutableCards(list(flatten(pairs[2:]))),
        ]

        for imm_c in cards:
            pairsteps = list(imm_c.pairsteps())
            assert len(imm_c) % 2 == 0  # just to be sure
            nbr_pairs = len(imm_c) // 2
            expected_nbr = sum([nbr_pairs-k+1 for k in range(2, nbr_pairs+1)])  # eg. if there are 6 cards (3 pairs), 3 + 2 = 5 different ps
            self.assertEqual(len(pairsteps), expected_nbr, "\ncards: {}\npairsteps: {}".format(imm_c, pairsteps))

        cards_ph = [
            (ImmutableCards(list(flatten([pairs[3:7], C.PHOENIX, C.TWO_JADE]))), sum([5-k+1 for k in range(2, 5+1)]) + sum([sum([n-k+2 for k in range(2, n+1)]) for n in range(2, 4+1)]) ),  # +2 + 3 + 4 + 2 + 3 + 2
            (ImmutableCards(list(flatten([pairs[5:9], C.PHOENIX, C.NINE_JADE, pairs[10:12]]))), sum([7-k+1 for k in range(2, 7+1)]) + 2 + (4 + 3 + 2) + (3 + 2) + 2),  # + 2 + (4 + 3 + 2) + (3 + 2) + 2
        ]
        for imm_c, expected_nbr in cards_ph:
            pairsteps = list(imm_c.pairsteps())
            self.assertEqual(len(pairsteps), expected_nbr, "\ncards: {}\npairsteps: \n{}".format(imm_c, "\n".join([str(ps) for ps in sorted(pairsteps, key=lambda ps: len(ps))])))

    def test_all_combination_no_args(self):
        # only some small examples:
        # TODO
        pass

    def test_can_be_played_on(self):
        pass  # TODO


class ImmutableCardsTest(unittest.TestCase):
    pass

class MutableCardsTest(unittest.TestCase):
    # TODO make sure no precomputed value from immutable cards is kept
    pass
