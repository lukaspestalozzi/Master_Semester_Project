from game.cards.card import Card
from game.cards.cards import ImmutableCards

import random as rnd


class Deck(ImmutableCards):
    def __init__(self, full=True, cards=list()):
        """
        full: if True, the argument cards is ignored and a full deck is created. Default is True
        cards: The cards initially in the Deck. Ignored when 'full=True'
        """
        if full:
            cards_to_add = [
                Card.PHOENIX, Card.DRAGON, Card.MAHJONG, Card.DOG,
                Card.TWO_JADE, Card.THREE_JADE, Card.FOUR_JADE, Card.FIVE_JADE, Card.SIX_JADE, Card.SEVEN_JADE,
                Card.EIGHT_JADE, Card.NINE_JADE, Card.TEN_JADE, Card.J_JADE, Card.Q_JADE, Card.K_JADE, Card.A_JADE,
                Card.TWO_HOUSE, Card.THREE_HOUSE, Card.FOUR_HOUSE, Card.FIVE_HOUSE, Card.SIX_HOUSE, Card.SEVEN_HOUSE,
                Card.EIGHT_HOUSE, Card.NINE_HOUSE, Card.TEN_HOUSE, Card.J_HOUSE, Card.Q_HOUSE, Card.K_HOUSE,
                Card.A_HOUSE,
                Card.TWO_SWORD, Card.THREE_SWORD, Card.FOUR_SWORD, Card.FIVE_SWORD, Card.SIX_SWORD, Card.SEVEN_SWORD,
                Card.EIGHT_SWORD, Card.NINE_SWORD, Card.TEN_SWORD, Card.J_SWORD, Card.Q_SWORD, Card.K_SWORD,
                Card.A_SWORD,
                Card.TWO_PAGODA, Card.THREE_PAGODA, Card.FOUR_PAGODA, Card.FIVE_PAGODA, Card.SIX_PAGODA,
                Card.SEVEN_PAGODA, Card.EIGHT_PAGODA, Card.NINE_PAGODA, Card.TEN_PAGODA, Card.J_PAGODA, Card.Q_PAGODA,
                Card.K_PAGODA, Card.A_PAGODA
            ]
        else:
            cards_to_add = list(cards)

        super().__init__(cards_to_add)
        self._cards = frozenset(self._cards)
        assert len(self._cards) == len(cards_to_add)

    def split(self, nbr_piles=4, random_=True):
        """
        :param nbr_piles: Splits the deck into 'nbr_piles' same sized piles (defualt is 4).
        The size of the deck must be divisible by nbr_piles.
        :param random_: If random is True, the cards will be distributed randomly over the piles.
        :return a list (of length 'nbr_piles') of lists of 'Card' instances.
        """
        if len(self._cards) % nbr_piles != 0:
            raise ValueError("The decks size ({}) must be divisible by 'nbr_piles' ({}).".format(len(self._cards), nbr_piles))
        pile_size = int(len(self._cards) / nbr_piles)
        cards_to_distribute = sorted(list(self._cards))
        if random_:
            rnd.shuffle(cards_to_distribute)
        pile_list = []
        for k in range(nbr_piles):
            from_ = k*pile_size
            to = k*pile_size + pile_size
            pile_list.append(list(cards_to_distribute[from_: to]))
        return pile_list
