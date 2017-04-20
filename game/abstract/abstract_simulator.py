import abc

from .abstract_gamestate import GameState
from collections import Collection


class GameSimulator(metaclass=abc.ABCMeta):
    """
    Simulates a Game
    """

    @abc.abstractmethod
    def simulate(self, players: Collection, start_state: GameState):
        """
        :param players: 
        :param start_state: 
        :return: Simulates a game from the given state onwards.
        """