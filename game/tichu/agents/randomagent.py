

import random

import logging
from collections import defaultdict

from .baseagent import DefaultAgent
from ..cards import CardValue
from ..tichu_actions import PassAction, CombinationAction, SwapCardAction


class RandomAgent(DefaultAgent):
    """
    Plays if possible a Random Move

    - wish: random value
    - play_first: a random action (that fulfills the wish if there is one).
    - play_combination: a random action (that fulfills the wish if there is one). Only passes if no other action is possible
    - play_bomb: if there is one, plays one
    - swap_cards: 3 random cards
    - announce_tichu:  with probability 0.3
    - announce_grand_tichu: with probability 0.1
    """

    def wish(self, round_history):
        wish = random.choice([cv for cv in CardValue
                              if cv is not CardValue.DOG
                              and cv is not CardValue.DRAGON
                              and cv is not CardValue.MAHJONG
                              and cv is not CardValue.PHOENIX])
        return wish

    def play_combination(self, wish, round_history):
        possible_combs = list(self.hand_cards.all_combinations(round_history.last_combination))
        comb = random.choice(possible_combs) if len(possible_combs) > 0 else None

        # try to fulfill wish:
        w = self._play_wish(possible_combs, wish)
        if w is not None:
            comb = w

        assert comb is None or len(possible_combs) > 0, "If there is a combination to play, don't pass"
        return PassAction(self._position) if comb is None else CombinationAction(self._position, combination=comb)

    def play_bomb(self, round_history):
        possible_bombs = [b for b in self.hand_cards.all_bombs() if round_history.last_combination < b]
        ret = random.choice(possible_bombs) if len(possible_bombs) > 0 else False
        return ret

    def play_first(self, round_history, wish):
        possible_combs = list(self.hand_cards.all_combinations())
        assert len(possible_combs) != 0

        # try to fulfill wish:
        comb = None
        w = self._play_wish(possible_combs, wish)
        if w is not None:
            comb = w
        else:
            # group by length
            l_dict = defaultdict(lambda: [])
            for comb in possible_combs:
                l_dict[len(comb)].append(comb)
            # choose a length
            l = random.choice(list(l_dict.keys()))
            # choose a combination of that length
            assert len(l_dict[l]) > 0
            comb = random.choice(l_dict[l])

        assert comb is not None
        return CombinationAction(self._position, combination=comb)

    def _play_wish(self, possible_combs, wish):
        """
        :param possible_combs:
        :param wish:
        :return: A combination fulfilling the wish if possible, None if not possible
        """
        # verify wish
        if wish and wish in (c.card_value for c in self.hand_cards):
            pcombs = (comb for comb in possible_combs if comb.contains_cardval(wish))
            try:
                return next(pcombs)  # Take the first combination fulfilling the wish
            except StopIteration:
                return None  # can't fulfill the wish (pcombs is empty), return any combination
        return None

    def swap_cards(self):
        sc = self.hand_cards.random_cards(3)
        scards = [
                    SwapCardAction(player_from=self._position, card=sc[0], player_to=(self.position + 1) % 4),
                    SwapCardAction(player_from=self._position, card=sc[1], player_to=(self.position + 2) % 4),
                    SwapCardAction(player_from=self._position, card=sc[2], player_to=(self.position + 3) % 4)
                ]
        return scards

    def announce_tichu(self, announced_tichu, announced_grand_tichu):
        return random.random() > 0.7

    def announce_grand_tichu(self, announced_grand_tichu):
        return random.random() > 0.9


