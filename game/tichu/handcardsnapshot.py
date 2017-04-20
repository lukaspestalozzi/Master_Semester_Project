import logging

from collections import namedtuple

from .cards import ImmutableCards, Cards
from game.utils import check_all_isinstance, indent


class HandCardSnapshot(namedtuple("HCS", ["handcards0", "handcards1", "handcards2", "handcards3"])):
    """
    Contains 4 ImmutableCards instances representing the handcards of the 4 players.
    """

    def __init__(self, handcards0, handcards1, handcards2, handcards3):
        check_all_isinstance([handcards0, handcards1, handcards2, handcards3], ImmutableCards)
        super().__init__()

    @classmethod
    def from_cards_lists(cls, cards0, cards1, cards2, cards3):
        return cls(ImmutableCards(cards0), ImmutableCards(cards1), ImmutableCards(cards2), ImmutableCards(cards3))

    def remove_cards(self, from_pos, cards):
        """

        :param from_pos:
        :param cards:
        :return: a new HandCardSnapshot instance with the cards removed from the given position
        """
        cards_at_pos = Cards(self[from_pos])
        cards_at_pos.remove_all(cards)
        new_cards_at_pos = cards_at_pos.to_immutable()
        new_l = list(self)
        new_l[from_pos] = new_cards_at_pos
        return HandCardSnapshot(*new_l)

    def copy(self, save=False):
        """
        Makes a copy of this instance
        :param save: (default False)
         - an integer (in range(4)) then the copy will only contain information as seen by the player at this position.
         - False, it is a complete copy.

        :return: a copy of this instance
        """
        if save is False:
            return HandCardSnapshot(self.handcards0, self.handcards1, self.handcards2, self.handcards3)
        elif save is not True and save in range(4):
            empty_hc = [ImmutableCards(list()) for _ in range(4)]
            empty_hc[save] = [self.handcards0, self.handcards1, self.handcards2, self.handcards3][save]
            return HandCardSnapshot(*empty_hc)
        else:
            raise ValueError("save must be one of [False, 0, 1, 2, 3] but was: " + str(save))

    def pretty_string(self, indent_: int = 0) -> str:
        ind = indent(indent_, s=" ")
        s = f"{ind}0:{self.handcards0.pretty_string()}\n{ind}1:{self.handcards1.pretty_string()}\n{ind}2:{self.handcards2.pretty_string()}\n{ind}3:{self.handcards3.pretty_string()}"
        return s

    def __str__(self):
        return self.pretty_string()
