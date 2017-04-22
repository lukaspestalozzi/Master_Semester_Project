import abc

from game.abstract import Player, GameState, Action
from game.utils import check_param


class TichuPlayer(Player, metaclass=abc.ABCMeta):

    def __init__(self, player_id):
        super().__init__()
        check_param(player_id, int)
        self._id = player_id

    @property
    def id(self) -> int:
        return self._id

    @id.setter
    def id(self, new_id: int):
        self._id = new_id

    def new_round(self):
        pass






