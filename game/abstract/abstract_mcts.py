import abc

from .abstract_gamestate import GameState


class MCTSGameState(GameState, metaclass=abc.ABCMeta):
    """
    Gamestate for Monte Carlo Tree Search
    """

    @abc.abstractmethod
    def rollout(self, *args, **kwargs):
        """
        Does a rollout and returns the result
        :return: A dict containing the score for each player in the final state of the rollout (mapping player.id() -> score).
        """
