import logging
import random

from game.cards import CardValue, Combination, Card
from game.player.abstract_tichuplayer import TichuPlayer, PlayerAction
from game.round import SwapCards, Card_To


class PassingTichuPlayer(TichuPlayer):
    """
    Ignores the agent.
    Always passes when possible. Or plays a random card when passing is not possible.
    Wishes a random CardValue and swaps the first 3 cards.
    Always announces a normal Tichu
    """

    def __init__(self, name, agent):
        super().__init__(name, agent)

    def play_combination(self, on_trick, wish):  # TODO agent, give possible moves as argument
        action = PlayerAction(self)
        if wish and wish in [c.card_value for c in self.hand_cards]:
            cards = [c for c in self.hand_cards if c.card_value is wish]
            action = PlayerAction(self, combination=Combination(cards[0:1]), pass_=False)
        logging.info("{} plays: {}".format(self.name, action))
        return action

    def play_bomb_or_not(self, on_trick):
        return False

    def give_dragon_away(self, trick):
        pl_pos = (self.position + 1) % 4
        logging.info("{} gives dragon to: {}".format(self.name, pl_pos))
        return pl_pos

    def play_first(self):
        card = next(iter(self.hand_cards))
        action = PlayerAction(self, combination=Combination(cards=[card], phoenix_as=Card.PHOENIX))
        logging.info("{} plays: {}".format(self.name, action))
        return action

    def swap_cards(self):
        it = iter(self.hand_cards)
        scards = SwapCards(self,
                         Card_To(next(it), (self.position + 1) % 4),
                         Card_To(next(it), (self.position + 2) % 4),
                         Card_To(next(it), (self.position + 3) % 4))
        logging.info("{} swapps cards: {}".format(self.name, scards))
        return scards

    def players_announced_tichu(self, announced):
        pass

    def announce_grand_tichu_or_not(self, announced_tichu, announced_grand_tichu):
        return False

    def announce_tichu_or_not(self, announced_tichu, announced_grand_tichu):
        tichu = True
        if tichu:
            logging.info("{} announces Tichu: {}".format(self.name, tichu))
        return tichu

    def players_announced_grand_tichu(self, announced):
        pass

    def wish(self):
        wish = random.choice([cv for cv in CardValue])
        logging.info("{} wishes card: {}".format(self.name, wish))
        return wish

