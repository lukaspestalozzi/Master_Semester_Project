from collections import namedtuple

from game.tichu.tichuplayers import TichuPlayer
from game.utils import check_isinstance


class Team(namedtuple("T", ["player1", "player2"])):
    def __init__(self, player1, player2):
        check_isinstance(player1, TichuPlayer)
        check_isinstance(player2, TichuPlayer)
        super(Team, self).__init__()

    @property
    def second_player(self):
        return self.player2

    @property
    def first_player(self):
        return self.player1

    def __contains__(self, player):
        return player == self.player1 or player == self.player2

    def __str__(self):
        return "Team(player1:{}, player2:{})".format(self.player1, self.player2)

