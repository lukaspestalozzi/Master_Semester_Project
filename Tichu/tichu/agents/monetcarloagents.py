import random

import logging

import time

from tichu.agents.baseagent import BaseAgent
from tichu.cards.card import CardValue
from tichu.game.gameutils import PassAction, CombinationAction, SwapCardAction, Trick
from tichu.montecarlo import MctsState, MonteCarloTreeSearch


class MonteCarloPerfectInformationAgent(BaseAgent):

    def __init__(self):
        super().__init__()
        self._mcts = MonteCarloTreeSearch()

    def start_game(self):
        pass

    def give_dragon_away(self, hand_cards, trick, round_history):
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
        nbr_passed = round_history.nbr_passed()
        assert nbr_passed in range(0, 4)
        action = self._start_montecarlo_search(self._create_mcts_state(round_history=round_history,
                                                                       wish=wish,
                                                                       trick_on_table=round_history.tricks[-1],
                                                                       nbr_passed=nbr_passed))
        return action

    def play_bomb(self, hand_cards, round_history):
        return None  # TODO, for now only play bomb when it's your turn -> bomb will never be beaten by another bomb!!

    def play_first(self, hand_cards, round_history, wish):
        nbr_passed = round_history.nbr_passed()
        assert nbr_passed == 0
        action = self._start_montecarlo_search(self._create_mcts_state(round_history=round_history,
                                                                       wish=wish,
                                                                       trick_on_table=Trick([]),
                                                                       nbr_passed=nbr_passed))
        return action

    def _create_mcts_state(self, round_history, wish, trick_on_table, nbr_passed):
        """
        :param round_history:
        :param wish:
        :param trick_on_table:
        :param nbr_passed:
        :return:
        """
        return MctsState(current_pos=self.position,
                         hand_cards=round_history.last_handcards,
                         won_tricks=round_history.won_tricks,
                         trick_on_table=trick_on_table,
                         wish=wish,
                         ranking=tuple(round_history.ranking),
                         nbr_passed=nbr_passed,
                         announced_tichu=frozenset(round_history.announced_tichus),
                         announced_grand_tichu=frozenset(round_history.announced_grand_tichus),
                         action_leading_here=round_history.events[-1])

    def _start_montecarlo_search(self, start_state):
        start_t = time.time()
        if len(start_state.possible_actions()) == 1:
            logging.debug(f"player #{self.position} there is only one action to play.")
            action = next(iter(start_state.possible_actions()))
        else:
            logging.debug(f"player #{self.position} started mcts")
            action = self._mcts.search(start_state=start_state)

        logging.debug(f"player #{self.position} found action: {action} (time: {time.time()-start_t})")
        return action

    def swap_cards(self, hand_cards):
        sc = hand_cards.random_cards(3)
        scards = [
            SwapCardAction(player_from=self._position, card=sc[0], player_to=(self.position + 1) % 4),
            SwapCardAction(player_from=self._position, card=sc[1], player_to=(self.position + 2) % 4),
            SwapCardAction(player_from=self._position, card=sc[2], player_to=(self.position + 3) % 4)
        ]
        return scards

    def notify_about_announced_tichus(self, tichu, grand_tichu):
        pass

    def announce_tichu(self, announced_tichu, announced_grand_tichu, round_history):
        return False

    def announce_grand_tichu(self, announced_grand_tichu):
        return False
