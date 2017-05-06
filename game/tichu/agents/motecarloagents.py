import abc
import logging
import time

from game.montecarlo.old_montecarlo import MctsState, DefaultMonteCarloTreeSearch
from game.montecarlo.montecarlo import InformationSetMCTS, EpicISMCTS, ISMctsLGR, ISMctsEpigLGR, \
    InformationSetMCTS_old_evaluation
from game.tichu.agents.baseagent import SearchAgent
from game.tichu.agents.partialagents import SimplePartialAgent
from game.tichu.new_.tichu_states import TichuState
from game.tichu.tichu_actions import TichuAction


class MonteCarloAgent(SearchAgent, SimplePartialAgent, metaclass=abc.ABCMeta):

    def __init__(self, iterations: int = 100, cheat: bool = False):
        super().__init__()
        self._mcts = None
        self.cheat = cheat
        self.iterations = iterations

    def start_game(self):
        self._mcts = self.init_montecarlo_search()

    def info(self):
        return "{s.name}[iterations: {s.iterations}, cheat: {s.cheat}]".format(s=self)

    def search(self, start_state):
        return self._mcts.search(root_state=start_state,
                                 observer_id=self.position,
                                 iterations=self.iterations,
                                 cheat=self.cheat)

    @abc.abstractmethod
    def init_montecarlo_search(self):
        """
        
        :return: The instance of the search class to be used.
        """
        pass


class SimpleMonteCarloPerfectInformationAgent(SearchAgent, SimplePartialAgent):
    """
    Old MCTSUCB1Agent
    
    SimpleMonteCarloPerfectInformationAgent is deprecated, use 'MCTSUCB1Agent' (with cheat=True) instead
    """

    def __init__(self, iterations: int=100):
        super().__init__(name="SimpleMonteCarloPerfectInformationAgent")
        self._mcts = DefaultMonteCarloTreeSearch(search_iterations=iterations, nbr_rollouts=1)
        import warnings
        warnings.warn("SimpleMonteCarloPerfectInformationAgent is seprecated, use 'MCTSUCB1Agent' (with cheat=True) instead", DeprecationWarning,
                      stacklevel=2)

    def _create_tichu_state(self, round_history, wish, trick_on_table):
        return MctsState(current_pos=self.position,
                         hand_cards=round_history.last_handcards,
                         won_tricks=round_history.won_tricks,
                         trick_on_table=trick_on_table,
                         wish=wish,
                         ranking=tuple(round_history.ranking),
                         nbr_passed=round_history.nbr_passed(),
                         announced_tichu=frozenset(round_history.announced_tichus),
                         announced_grand_tichu=frozenset(round_history.announced_grand_tichus),
                         action_leading_here=round_history.events[-1])

    def search(self, start_state):
        return self._mcts.search(start_state=start_state)


class ISMctsUCB1Agent(MonteCarloAgent):
    """
    **Type:** Information Set MCTS

    **Selection:** UCB1

    **Simulation:** Uniform Random

    **Best Action:** Most Visited
    """

    def init_montecarlo_search(self):
        return InformationSetMCTS()


class ISMctsUCB1Agent_old_evalAgent(MonteCarloAgent):
    """
    Same as ISMctsUCB1Agent but uses the absolute points as the reward of states.
    """

    def init_montecarlo_search(self):
        return InformationSetMCTS_old_evaluation()


class ISMctsEpicAgent(MonteCarloAgent):
    """
    **Type:** Episodic MCTS

    **Selection:** Epic

    **Simulation:** Epic

    **Best Action:** Most Visited
    """

    def init_montecarlo_search(self):
        return EpicISMCTS()


class ISMctsLGRAgent(MonteCarloAgent):
    """
    **Type:** Information Set MCTS
    
    **Selection:** UCB1
    
    **Simulation:** LastGoodResponse (Moves of winning player gets stored and chosen in next rollout if applicable)
    
    **Best Action:** Most Visited
    """

    def __init__(self, iterations: int = 100, cheat: bool = False, forgetting: bool=True):
        super().__init__(iterations=iterations, cheat=cheat)
        self.forgetting = forgetting

    def info(self):
        return "{s.name}[iterations: {s.iterations}, cheat: {s.cheat}, forgetting: {s.forgetting}]".format(s=self)

    def init_montecarlo_search(self):
        return ISMctsLGR(forgetting=self.forgetting)


class ISMctsEpicLGRAgent(ISMctsLGRAgent):
    """
    **Type:** Information Set MCTS
    
    **Selection:** Epic
    
    **Simulation:** LastGoodResponse (Moves of winning player gets stored and chosen in next rollout if applicable)
    
    **Best Action:** Most Visited
    """

    def init_montecarlo_search(self):
        return ISMctsEpigLGR(forgetting=self.forgetting)

