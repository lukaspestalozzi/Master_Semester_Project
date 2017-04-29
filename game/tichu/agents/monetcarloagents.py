import logging
import time

from game.montecarlo.old_montecarlo import MctsState, DefaultMonteCarloTreeSearch
from .partialagents import *
from ..trick import Trick


class SimpleMonteCarloPerfectInformationAgent(SimplePartialAgent):

    def __init__(self, iterations: int=100):
        super().__init__()
        self._mcts = DefaultMonteCarloTreeSearch(search_iterations=iterations, nbr_rollouts=1)

    def play_combination(self, wish, round_history):
        nbr_passed = round_history.nbr_passed()
        assert nbr_passed in range(0, 4)
        action = self._start_montecarlo_search(self._create_mcts_state(round_history=round_history,
                                                                       wish=wish,
                                                                       trick_on_table=round_history.tricks[-1],
                                                                       nbr_passed=nbr_passed))
        return action

    def play_first(self, round_history, wish):
        nbr_passed = round_history.nbr_passed()
        assert nbr_passed == 0
        action = self._start_montecarlo_search(self._create_mcts_state(round_history=round_history,
                                                                       wish=wish,
                                                                       trick_on_table=Trick([]),
                                                                       nbr_passed=nbr_passed))
        return action

    def _create_mcts_state(self, round_history, wish, trick_on_table, nbr_passed):
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
