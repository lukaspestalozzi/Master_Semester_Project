
from player import DummyPlayer

# TODO create a calss to keep track of points
# TODO create a class Team containing the players and score and other statistics
# TODO integrate Logging

class TichuGameManager():

    def __init__(target_points):
        self._player0 = DummyPlayer(name="player0")
        self._player1 = DummyPlayer(name="player1")
        self._player2 = DummyPlayer(name="player2")
        self._player3 = DummyPlayer(name="player3")


        self._players = [self._player0, self._player1, self._player2, self._player3]

        self._target_points = target_points

    def start(self):
        """
        Starts the game
        Returns the final points as tuple (points for team 1, points for team 2, winner), where winner is the integer 1 or 2
        """

        while self._points_team1 < self._target_points and self._points_team2 < self._target_points:
            self._current_round_nbr += 1
            # create the round TODO give teams as arguments
            next_round = Round(players=self._players, points=(self._points_team1, self._points_team2, self._target_points))
            round_res = next_round.run()
            # update the points TODO update directly into the team instances
            self._points_team1 += round_res.points_team1
            self._points_team2 += round_res.points_team2

        # determine winner
        return (self._points_team1, self._points_team2, 1 if self._points_team1 > self._points_team2 else 2)

class Team():

    def __init__(self, player1, player2, teamID):
        if not (isinstance(player1, Player) and isinstance(player2, Player)):
            raise ValueError("player1 and player2 must be instances of 'Player' class.")
        self._player1 = player1
        self._player2 = player2
        self._points = 0
        self._id = teamID

        # TODO add point counting here?

    def second_player(self):
        return self._player2

    def first_player(self):
        return self._player1

    def in_team(self, player):
        return player == self._player1 or player == self._player2

    def __contains__(self, player):
        return self.in_team(player)

    # TODO add methods: add_points; get_points; Hash == UUID; eq
