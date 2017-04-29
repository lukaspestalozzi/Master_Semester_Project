import logging
import time

from game.montecarlo.montecarlo import InformationSetMCTS
from game.tichu import SimplePartialAgent
from game.tichu.new_.tichu_states import TichuInfoSet
from game.tichu.trick import Trick


class ISMctsUCBAgent(SimplePartialAgent):

    def __init__(self, iterations: int=100, cheat: bool=False):
        super().__init__()
        self._ismcts = None
        self.cheat = cheat
        self.iterations = iterations

    def start_game(self):
        self._ismcts = InformationSetMCTS()

    def play_combination(self, wish, round_history):
        action = self._start_search(self._create_infoset(round_history=round_history,
                                                         wish=wish,
                                                         trick_on_table=round_history.tricks[-1]))
        return action

    def play_first(self, round_history, wish):
        action = self._start_search(self._create_infoset(round_history=round_history,
                                                         wish=wish,
                                                         trick_on_table=Trick()))
        return action

    def _create_infoset(self, round_history, wish, trick_on_table):
        return TichuInfoSet(observer_id=self.position,
                            player_id=self.position,
                            hand_cards=round_history.last_handcards,
                            won_tricks=round_history.won_tricks,
                            trick_on_table=trick_on_table,
                            wish=wish,
                            ranking=tuple(round_history.ranking),
                            announced_tichu=frozenset(round_history.announced_tichus),
                            announced_grand_tichu=frozenset(round_history.announced_grand_tichus))

    def _start_search(self, start_infoset):
        start_t = time.time()
        if len(start_infoset.possible_actions()) == 1:
            logging.debug(f"player {self.position} there is only one action to play.")
            action = next(iter(start_infoset.possible_actions()))
        else:
            action = self._ismcts.search(start_infoset, observer_id=self.position, iterations=self.iterations, cheat=self.cheat)

        logging.debug(f"player {self.position} found action: {action} (time: {time.time()-start_t})")
        return action
