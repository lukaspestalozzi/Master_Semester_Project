
import sys, os
import logging
import datetime
import gym
from profilehooks import timecall



this_folder = '/'.join(os.getcwd().split('/')[:])
parent_folder = '/'.join(os.getcwd().split('/')[:-1])

for p in [this_folder, parent_folder]:  # Adds the parent folder (ie. game) to the python path
    if p not in sys.path:
        sys.path.append(p)

from gym_agents.mcts import InformationSetMCTS, ISMCTS_old_rollout
from gamemanager import TichuGame
from gym_agents import *

import logginginit

logger = logging.getLogger(__name__)


def print_game_outcome(outcome):
    assert len(outcome) == 2
    print("Final Result: {}".format(outcome[0]))
    rounds = outcome[1]
    for round in rounds:
        # round is a History object
        print("====================  New Round  ===================")
        print(round)

    print("Final Result: {}".format(outcome[0]))


def create_agent_against_agent(type1, type2)->TichuGame:
    agents = [type1(), type2(),
              type1(), type2()]
    return TichuGame(*agents)


def dqn_against_random(target_points: int):
    weights_file1 = './gym_agents/agent_weights/dqn_4layers_weights.h5f'  # latest weights
    game = create_agent_against_agent(lambda: DQN4LayerAgent(weights_file=weights_file1),
                                      RandomAgent)

    res = game.start_game(target_points=target_points)
    return res


def dqn_against_ismcts(target_points: int):
    game = create_agent_against_agent(lambda: dqn_agent_4layers, lambda: BaseMonteCarloAgent(InformationSetMCTS(), iterations=100))

    res = game.start_game(target_points=target_points)
    return res


def dqn_against_dqn(target_points: int):
    weights_file1 = './gym_agents/agent_weights/dqn_4layers_weights.h5f'  # latest weights
    weights_file2 = './gym_agents/agent_weights/old_dqn_4layers_weights'  # previous weights
    game = create_agent_against_agent(lambda: DQN4LayerAgent(weights_file=weights_file1),
                                      lambda: DQN4LayerAgent(weights_file=weights_file2))

    res = game.start_game(target_points=target_points)
    return res


def random_against_random(target_points: int):
    game = create_agent_against_agent(RandomAgent, RandomAgent)
    res = game.start_game(target_points=target_points)
    return res


def balancedrandom_against_random(target_points: int):
    game = create_agent_against_agent(BalancedRandomAgent, RandomAgent)

    res = game.start_game(target_points=target_points)
    return res


def human_against_random(target_points: int):
    agents = [HumanInputAgent(position=0), RandomAgent(), RandomAgent(), RandomAgent()]
    game = TichuGame(*agents)

    res = game.start_game(target_points=target_points)
    return res


def ismcts_against_random(target_points: int):
    game = create_agent_against_agent(lambda: BaseMonteCarloAgent(InformationSetMCTS(), iterations=100), RandomAgent)
    res = game.start_game(target_points=target_points)
    return res


def ismcts_against_ismctsoldrollout(target_points: int):
    game = create_agent_against_agent(lambda: BaseMonteCarloAgent(InformationSetMCTS(), iterations=100),
                                      lambda: BaseMonteCarloAgent(ISMCTS_old_rollout(), iterations=100))  # ISMCTS_new_rollout
    res = game.start_game(target_points=target_points)
    return res


def ismcts_against_ismcts(target_points: int):
    game = create_agent_against_agent(lambda: BaseMonteCarloAgent(InformationSetMCTS(), iterations=100),
                                      lambda: BaseMonteCarloAgent(InformationSetMCTS(), iterations=100))  # ISMCTS_new_rollout
    res = game.start_game(target_points=target_points)
    return res

if __name__ == "__main__":
    gym.undo_logger_setup()

    start_ftime = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    log_folder_name = "/mnt/Data/Dropbox/Studium/EPFL/MA4/sem_project/logs/game_starter_" + start_ftime
    logging_mode = logginginit.RunGameMode
    logginginit.initialize_loggers(output_dir=log_folder_name, logging_mode=logging_mode, min_loglevel=logging.DEBUG)

    res = random_against_random(target_points=10000)
    print_game_outcome(res)
