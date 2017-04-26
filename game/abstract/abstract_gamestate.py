import abc
from collections import Collection, Generator

from .abstract_action import Action


class GameState(metaclass=abc.ABCMeta):
    """
    The interface of a general GameState
    """

    def __init__(self):
        self._reward_vector = None

    @abc.abstractmethod
    def is_terminal(self) -> bool:
        """
        
        :rtype: bool
        :return: True iff this state is terminal, False otherwise
        """

    @abc.abstractmethod
    def possible_actions(self) -> Collection:
        """
        :rtype: Collection
        :return: A collection containing all possible actions in this state
        """

    def possible_actions_gen(self) -> Generator:
        """
        The same as <GameState.possible_actions()> but returning a generator instead of the whole collection of actions.
        
        The default implementation is: 'yield from self.possible_actions()'
        
        :rtype: Generator
        :return: A Generator yielding all possible actions in this state
        """
        yield from self.possible_actions()

    @abc.abstractmethod
    def current_player_id(self) -> int:
        """
        :return: The player_id whose turn it is in this state
        """

    @abc.abstractmethod
    def next_state(self, action: Action):
        """
        :param action: 
        :return: The Game state when playing the given action in this state.
        """

    @abc.abstractmethod
    def evaluate(self) -> tuple:
        """
        The behaviour of this function is undefined when the state is not terminal.
        
        :return: A tuple containing the score for each player in this state (index player.id() -> score).
        """

    def reward_vector(self) -> tuple:
        """
        Note: The behaviour of this function is undefined when the state is not terminal.
        Note: caches the result of self.evaluate().
        :return: The reward vector of this state.
        """
        if self._reward_vector is None:
            self._reward_vector = self.evaluate()
        return tuple(self._reward_vector)

    @abc.abstractmethod
    def unique_id(self) -> str:
        """
        A string that has following property: 
        
        - A.unique_id() == B.unique_id() implies A == B
        - A.unique_id() != B.unique_id() implies A != B
        
        :return: A unique string for this instance 
        """


class GameInfoSet(GameState, metaclass=abc.ABCMeta):
    """
    The Information Set of a GameState from the perspective of a particular observer (player).
    """

    @property
    @abc.abstractmethod
    def observer_id(self):
        """
        :return: The id of the observer player
        """

    @abc.abstractmethod
    def determinization(self, *args, **kwargs):
        """
        Returns a GameState of perfect information in accordance to the observed information of this state.
        
        :return: the GameState
        """









