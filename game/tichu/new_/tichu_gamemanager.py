from collections import Sequence

import logging
from time import time

from game.abstract import GameManager
from game.tichu import TichuPlayer
from game.tichu.new_.tichu_states import TichuState
from game.tichu.tichu_actions import RoundStartEvent, RoundEndEvent
from game.utils import check_all_isinstance


class TichuGameManager(GameManager):

    def __init__(self, verbosity=logging.WARNING):
        super().__init__()
        self._v = verbosity
        self._players = None

    @property
    def verbosity(self) -> int:
        return self._v

    @verbosity.setter
    def verbosity(self, v: int):
        self._v = v

    def start_game(self, players: Sequence, target_points: int = 1000) -> object:
        """

        :param players: 
        :param target_points: 
        :return: The Game History
        """
        check_all_isinstance(players, TichuPlayer)
        self._players = players

        game_history = list()  # list of alternating gamestates and actions   # TODO make class

        for k, player in enumerate(players):
            player.reset()
            player.id = k

        game_state = self._get_init_game_state(players)
        game_history.append(game_state)
        while not game_state.is_terminal():
            round_history = self._start_round(current_gamestate=game_state)
            game_history.extend(round_history)

        return game_history

    def _get_init_game_state(self, players: Sequence) -> TichuState:
        # TODO
        raise NotImplementedError()

    def _start_round(self, current_gamestate: TichuState) -> list:
        # TODO what to do when both teams may win in this round.
        start_t = time()
        round_history = [RoundStartEvent()]

        game_state = current_gamestate

        # inform players about new round
        for player in self._players:
            player.new_round()

        # distribute cards


        # Players may announce a normal tichu before card swap

        # card swaps

        # round-loop

        # trick's loop

        # round ended, count scores

        round_history.append(RoundEndEvent())
        end_t = time() - start_t
        return round_history