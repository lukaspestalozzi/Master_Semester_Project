from time import time
import logging

import gym
from gym import wrappers

import gym_tichu


class TichuGame(object):

    def __init__(self, agent0, agent1, agent2, agent3, target_points=1000):
        """

        :param target_points: (integer > 0, default=1000) The game ends when one team reaches this amount of points
        """

        env = gym.make('tichu_multiplayer-v0')
        # env = wrappers.Monitor(env, "/home/lu/semester_project/tmp/gym-results")
        self.env = env

        self._agents = (agent0, agent1, agent2, agent3)

        self._target_points = target_points

    @property
    def agents(self):
        return self._agents

    def start_game(self):
        """
        Starts the tichu game
        Returns a tuple containing the points the two teams made
        """
        start_t = time()
        logging.info(f"Starting game... target: {self._target_points}")

        points = (0, 0)

        while points[0] < self._target_points and points[1] < self._target_points:
            # run rounds until there is a winner
            round_points, round_history = self._start_round()
            points = (round_points[0] + points[0], round_points[1] + points[1])

        logging.warning("Game ended: {p} (time: {time} sec)".format(p=points, time=time()-start_t))

        return points

    def _start_round(self):
        # TODO what to do when both teams may win in this round.
        start_t = time()
        logging.info("Start round...")

        observation = self.env.reset()
        reward = (0, 0, 0, 0)
        done = False
        info = {'next_player': observation.player_pos}
        while not done:
            current_player = info['next_player']
            action = self._agents[current_player].action(observation)
            observation, reward, done, info = self.env.step(action)

        logging.info("Round ended [Time: {}]".format(time()-start_t))
        return (reward[0] + reward[2], reward[1] + reward[3]), observation.history


