
import abc
from .abstract_player import Player


class Action(metaclass=abc.ABCMeta):
    """
    The interface for a general Game Action
    """

    @abc.abstractmethod
    def played_by(self) -> Player:
        """
        Use a 'Enviroment' Player to model actions played by the enviroment such as chance events.
        
        :return: The Player that played the action. 
        """