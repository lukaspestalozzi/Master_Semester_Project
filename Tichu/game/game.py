
# TODO integrate Logging
from collections import namedtuple

from game.agent import Agent
from game.tichuplayers import PassingTichuPlayer
from game.abstract_tichuplayer import TichuPlayer
from game.round import Round

GameOutcome = namedtuple("GameOutcome", ['team1', 'team2', 'winner_team_id', 'game_history'])


class TichuGameHistory(object):
    pass  # TODO


class TichuGameManager(object):

    def __init__(self, target_points):
        # TODO get teams as parameters

        self._players = [
            PassingTichuPlayer(name="player0", agent=Agent),
            PassingTichuPlayer(name="player1", agent=Agent),
            PassingTichuPlayer(name="player2", agent=Agent),
            PassingTichuPlayer(name="player3", agent=Agent)
        ]

        self._teams = [
            Team(self._players[0], self._players[2], team_id=0),
            Team(self._players[1], self._players[2], team_id=1)
        ]

        self._target_points = target_points
        self._current_round_nbr = 0
        self._history = TichuGameHistory()

    def start(self):
        """
        Starts the game
        Returns a tuple containing the two teams, the winner team, and the game history
        """
        for k in range(4):
            self._players[k].position = k

        while not (self._teams[0].points > self._target_points or self._teams[1].points > self._target_points):
            self._current_round_nbr += 1
            # create the round
            next_round = Round(team1=self._teams[0], team2=self._teams[1])
            round_res = next_round.run()
            # update the points
            self._teams[0].add_points(round_res.points_team1)
            self._teams[1].add_points(round_res.points_team2)

        # determine winner
        return GameOutcome(team1=self._teams[0],
                           team2=self._teams[1],
                           winner_team_id=max(self._teams, key=lambda t: t.points).id,
                           game_history=self._history)


class Team(object):

    def __init__(self, player1, player2, team_id):
        if not (isinstance(player1, TichuPlayer) and isinstance(player2, TichuPlayer)):
            raise ValueError("player1 and player2 must be instances of 'Player' class.")
        self._player1 = player1
        self._player2 = player2
        self._points = 0
        self._id = team_id

    @property
    def points(self):
        return self._points

    @property
    def id(self):
        return self._id

    @property
    def second_player(self):
        return self._player2

    @property
    def first_player(self):
        return self._player1

    def add_points(self, amount):
        self._points += amount

    def in_team(self, player):
        return self.__contains__(player)

    def __contains__(self, player):
        return player == self._player1 or player == self._player2
