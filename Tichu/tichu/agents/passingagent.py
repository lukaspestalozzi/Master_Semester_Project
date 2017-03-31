import random

import logging

from tichu.agents.baseagent import BaseAgent
from tichu.cards.card import CardValue
from tichu.cards.cards import Single


class PassingAgent(BaseAgent):

    def __init__(self):
        super().__init__()

    def start_game(self):
        pass

    def give_dragon_away(self, hand_cards, round_history):
        pl_pos = (self.position + 1) % 4
        return pl_pos

    def wish(self, hand_cards, round_history):
        wish = random.choice([cv for cv in CardValue
                              if cv is not CardValue.DOG
                              and cv is not CardValue.DRAGON
                              and cv is not CardValue.MAHJONG
                              and cv is not CardValue.PHOENIX])
        return wish

    def play_combination(self, wish, hand_cards, round_history):
        if wish and wish in (c.card_value for c in hand_cards):
            try:
                comb = next((c for c in hand_cards.all_combinations(round_history.last_combination) if c.contains_cardval(wish)))
                return comb
            except StopIteration:
                pass
        return None

    def play_bomb(self, hand_cards, round_history):
        return False

    def play_first(self, hand_cards, round_history, wish):
        card = next(iter(hand_cards))
        if wish:
            try:
                card = next((c for c in hand_cards if c.card_value is wish))
            except StopIteration:
                pass

        comb = Single(card)
        logging.debug("hand cards: {}".format(hand_cards))
        logging.debug("Agent plays first: " + str(comb))

        return comb

    def swap_cards(self, hand_cards):
        it = iter(hand_cards)
        scards = [
                   Card_To(next(it), (self.position + 1) % 4),
                   Card_To(next(it), (self.position + 2) % 4),
                   Card_To(next(it), (self.position + 3) % 4)
                ]
        return scards

    def notify_about_announced_tichus(self, tichu, grand_tichu):
        pass

    def announce_tichu(self, announced_tichu, announced_grand_tichu, round_history):
        return False

    def announce_grand_tichu(self, announced_grand_tichu):
        return False


