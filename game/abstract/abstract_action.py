
import abc


class Action(metaclass=abc.ABCMeta):
    """
    The interface for a general Game Action
    """

    @abc.abstractmethod
    def played_by(self) -> int:
        """
        Use a 'Enviroment' Player to model actions played by the enviroment such as chance events.
        
        :return: The player_id of the player that played the action. 
        """