from game.cards import CardValue
from game.round import SwapCards, Card_To
from game.abstract_tichuplayer import TichuPlayer, PlayerAction
import random


class PassingTichuPlayer(TichuPlayer):
    """
    Ignores the agent.
    Always passes when possible. Or plays a random card when passing is not possible.
    Wishes a random CardValue and swaps the first 3 cards.
    Always announces a normal Tichu
    """



    def __init__(self, name, agent):
        super().__init__(name, agent)

    def play_combination(self, on_trick):
        return PlayerAction(self)

    def play_bomb_or_not(self, on_trick):
        return False

    def give_dragon_away(self, trick):
        return (self.position + 1) % 4

    def play_first(self):
        return next(iter(self.hand_cards))

    def swap_cards(self):
        it = iter(self.hand_cards)
        return SwapCards(self,
                         Card_To(next(it), (self.position + 1) % 4),
                         Card_To(next(it), (self.position + 2) % 4),
                         Card_To(next(it), (self.position + 3) % 4))

    def players_announced_tichu(self, announced):
        pass

    def announce_grand_tichu_or_not(self, announced_tichu, announced_grand_tichu):
        return False

    def announce_tichu_or_not(self, announced_tichu, announced_grand_tichu):
        return True

    def players_announced_grand_tichu(self, announced):
        pass

    def wish(self):
        return random.choice([cv for cv in CardValue])

