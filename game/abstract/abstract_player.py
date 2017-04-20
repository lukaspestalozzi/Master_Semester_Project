import abc

from .abstract_action import Action
from .abstract_gamestate import GameState


class Player(metaclass=abc.ABCMeta):
    """
    The interface for a general player
    """

    @abc.abstractmethod
    @property
    def id(self) -> int:
        """
        For example the position on the playing table.
        
        :return: A unique identifier for this player
        """

    @abc.abstractmethod
    def reset(self):
        """
        Reset the internal state to the beginning of a game
        
        :return: self
        """

    @abc.abstractmethod
    def make_move(self, game_state: GameState) -> Action:
        """
        
        :param game_state: 
        :return: The Action the player wishes to make in this state
        """

    @abc.abstractmethod
    def notify(self, *args, **kwargs):
        """
        Can be called when the player has to be notified about something. For example other players moves.
        
        :param args: 
        :param kwargs: 
        :return: self
        """
        return self


