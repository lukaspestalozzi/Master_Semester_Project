import abc

from collections import Collection


class GameManager(metaclass=abc.ABCMeta):
    """
    Manages a Game and enforces the Rules
    """

    @property
    @abc.abstractmethod
    def verbosity(self):
        """
        
        :return: The verbosity 
        """

    @verbosity.setter
    @abc.abstractmethod
    def verbosity(self, v):
        """
        Setter for the verbosity property
        """

    @abc.abstractmethod
    def start_game(self, players: Collection) -> object:
        """
        Runs an entire Game
        :param players: The Players participating in the game
        :return: The History of the played Game
        """
