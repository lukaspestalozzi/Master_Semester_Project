import abc
import datetime
import argparse
from collections import namedtuple
from time import time
import multiprocessing as mp
from multiprocessing import Pool

import logging

import sys, os
from typing import Tuple

import gym


this_folder = '/'.join(os.getcwd().split('/')[:])
parent_folder = '/'.join(os.getcwd().split('/')[:-1])
Tichu_gym_folder = parent_folder+"/Tichu-gym"

for p in [this_folder, parent_folder, Tichu_gym_folder]:  # Adds the parent folder (ie. game) to the python path
    if p not in sys.path:
        sys.path.append(p)

from gamemanager import TichuGame
from gym_agents.strategies import make_random_tichu_strategy, never_announce_tichu_strategy, always_announce_tichu_strategy
from gym_agents import (BaseMonteCarloAgent, BalancedRandomAgent, make_first_ismcts_then_random_agent,
                        DQN4LayerAgent, DefaultGymAgent, DQN2LayerAgent)
from gym_agents.mcts import (InformationSetMCTS, InformationSetMCTS_absolute_evaluation,
                             InformationSetMCTSWeightedDeterminization, EpicISMCTS,
                             InformationSetMCTSHighestUcbBestAction, InformationSetMCTS_ranking_evaluation)
from gym_tichu.envs.internals.utils import time_since
import logginginit


logger = logging.getLogger(__name__)


class Experiment(object, metaclass=abc.ABCMeta):

    @property
    def name(self)->str:
        return self.__class__.__name__

    @property
    @abc.abstractmethod
    def agents(self)->Tuple[DefaultGymAgent, DefaultGymAgent, DefaultGymAgent, DefaultGymAgent]:
        pass

    def run(self, target_points):
        start_t = time()
        start_ftime = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

        players_vs_string = (
"""
0: {0}
2: {2} 
        VS.
1: {1}
3: {3}
""").format(*[p.info for p in self.agents])

        logger.info("Playing: " + players_vs_string)

        game_res = self._run_game(target_points=target_points)

        end_ftime = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

        results_string = (
"""
################################## {me.name} ##################################
Log-folder: {log_folder}
Start-time: {start_time}
End-time: {end_time}
Duration: {duration}

{players_vs_string}

Final Points: {points}

""").format(me=self, log_folder=log_folder_name,
            start_time=start_ftime, end_time=end_ftime, duration=time_since(start_t),
            players_vs_string=players_vs_string, points=game_res.points)

        game_history_string = str(game_res.history)

        logger.info(results_string)
        logger.debug(game_history_string)

        with open(log_folder_name+"/results.log", "a") as f:
            f.write(results_string)

    @abc.abstractmethod
    def _run_game(self, target_points):
        pass


class SimpleExperiment(Experiment, metaclass=abc.ABCMeta):
    """
    Experiment that runs a game to a given amount of points with 4 agents.
    The only method to overwrite is **_init_agents**
    """

    def __init__(self):
        agents = self._init_agents()
        self._agents = agents

    @property
    def agents(self)->Tuple[DefaultGymAgent, DefaultGymAgent, DefaultGymAgent, DefaultGymAgent]:
        return self._agents

    def _run_game(self, target_points=1000):

        game = TichuGame(*self.agents)
        return game.start_game(target_points=target_points)

    @abc.abstractmethod
    def _init_agents(self)->Tuple[DefaultGymAgent, DefaultGymAgent, DefaultGymAgent, DefaultGymAgent]:
        raise NotImplementedError()

# CHEAT vs NONCHEAT
class CheatVsNonCheatUCB1(SimpleExperiment):

    def _init_agents(self):
        return (BaseMonteCarloAgent(InformationSetMCTS(), iterations=100, cheat=True),
                BaseMonteCarloAgent(InformationSetMCTS(), iterations=100),
                BaseMonteCarloAgent(InformationSetMCTS(), iterations=100, cheat=True),
                BaseMonteCarloAgent(InformationSetMCTS(), iterations=100))


#EPIC vs ISMCTS
class EpicVsIsMcts(SimpleExperiment):

    def _init_agents(self):
        return (BaseMonteCarloAgent(InformationSetMCTS(), iterations=100),
                BaseMonteCarloAgent(EpicISMCTS(), iterations=100),
                BaseMonteCarloAgent(InformationSetMCTS(), iterations=100),
                BaseMonteCarloAgent(EpicISMCTS(), iterations=100))


# BEST ACTION
class IsmctsBestActionMaxUcbVsMostVisited(SimpleExperiment):

    def _init_agents(self):
        return (BaseMonteCarloAgent(InformationSetMCTSHighestUcbBestAction(), iterations=100),
                BaseMonteCarloAgent(InformationSetMCTS(), iterations=100),
                BaseMonteCarloAgent(InformationSetMCTSHighestUcbBestAction(), iterations=100),
                BaseMonteCarloAgent(InformationSetMCTS(), iterations=100))


# REWARD
class RelativeVsAbsoluteReward(SimpleExperiment):

    def _init_agents(self):
        return (BaseMonteCarloAgent(InformationSetMCTS(), iterations=100),
                BaseMonteCarloAgent(InformationSetMCTS_absolute_evaluation(), iterations=100),
                BaseMonteCarloAgent(InformationSetMCTS(), iterations=100),
                BaseMonteCarloAgent(InformationSetMCTS_absolute_evaluation(), iterations=100))


class RelativeVsRankingReward(SimpleExperiment):
    def _init_agents(self):
        return (BaseMonteCarloAgent(InformationSetMCTS(), iterations=100),
                BaseMonteCarloAgent(InformationSetMCTS_ranking_evaluation(), iterations=100),
                BaseMonteCarloAgent(InformationSetMCTS(), iterations=100),
                BaseMonteCarloAgent(InformationSetMCTS_ranking_evaluation(), iterations=100))


class RankingVsAbsoluteReward(SimpleExperiment):

    def _init_agents(self):
        return (BaseMonteCarloAgent(InformationSetMCTS_ranking_evaluation(), iterations=100),
                BaseMonteCarloAgent(InformationSetMCTS_absolute_evaluation(), iterations=100),
                BaseMonteCarloAgent(InformationSetMCTS_ranking_evaluation(), iterations=100),
                BaseMonteCarloAgent(InformationSetMCTS_absolute_evaluation(), iterations=100))


# TICHU
class RandomVsNeverTichu(SimpleExperiment):

    def _init_agents(self):
        return (BalancedRandomAgent(announce_tichu=make_random_tichu_strategy(announce_weight=0.5)),
                BalancedRandomAgent(announce_tichu=never_announce_tichu_strategy),
                BalancedRandomAgent(announce_tichu=never_announce_tichu_strategy),
                BalancedRandomAgent(announce_tichu=never_announce_tichu_strategy),)


class AlwaysVsNeverTichu(SimpleExperiment):

    def _init_agents(self):
        return (BalancedRandomAgent(announce_tichu=always_announce_tichu_strategy),
                BalancedRandomAgent(announce_tichu=never_announce_tichu_strategy),
                BalancedRandomAgent(announce_tichu=never_announce_tichu_strategy),
                BalancedRandomAgent(announce_tichu=never_announce_tichu_strategy),)


# SPLIT AGENTS
class FirstMctsThenRandomVsRandom(SimpleExperiment):

    def _init_agents(self):
        return (make_first_ismcts_then_random_agent(switch_length=5),
                BalancedRandomAgent(),
                make_first_ismcts_then_random_agent(switch_length=5),
                BalancedRandomAgent())


# DETERMINIZATION
class RandomVsPoolDeterminization(SimpleExperiment):

    def _init_agents(self):
        return (BaseMonteCarloAgent(InformationSetMCTS(), iterations=100),
                BaseMonteCarloAgent(InformationSetMCTSWeightedDeterminization(), iterations=100),
                BaseMonteCarloAgent(InformationSetMCTS(), iterations=100),
                BaseMonteCarloAgent(InformationSetMCTSWeightedDeterminization(), iterations=100),)


# DQN
class DQNUntrainedVsRandom(SimpleExperiment):

    def _init_agents(self):
        return (DQN4LayerAgent(weights_file=None),
                BalancedRandomAgent(),
                DQN4LayerAgent(weights_file=None),
                BalancedRandomAgent())


class DQNRandomVsDQNLearned(SimpleExperiment):

    def _init_agents(self):
        return (DQN2LayerAgent(weights_file='./dqn/dqn_random.h5f'),
                DQN2LayerAgent(weights_file='./dqn/dqn_learned.h5f'),
                DQN2LayerAgent(weights_file='./dqn/dqn_random.h5f'),
                DQN2LayerAgent(weights_file='./dqn/dqn_learned.h5f'))


class DQNRandomVsDQNLearning(SimpleExperiment):

    def _init_agents(self):
        return (DQN2LayerAgent(weights_file='./dqn/dqn_random.h5f'),
                DQN2LayerAgent(weights_file='./dqn/dqn_learning.h5f'),
                DQN2LayerAgent(weights_file='./dqn/dqn_random.h5f'),
                DQN2LayerAgent(weights_file='./dqn/dqn_learning.h5f'))


class DQNLearnedVsDQNLearning(SimpleExperiment):

    def _init_agents(self):
        return (DQN2LayerAgent(weights_file='./dqn/dqn_learned.h5f'),
                DQN2LayerAgent(weights_file='./dqn/dqn_learning.h5f'),
                DQN2LayerAgent(weights_file='./dqn/dqn_learned.h5f'),
                DQN2LayerAgent(weights_file='./dqn/dqn_learning.h5f'))


class DQNVsRandom(SimpleExperiment):

    def _init_agents(self):
        return (DQN2LayerAgent(weights_file='./dqn/dqn_vs_random.h5f'),
                BalancedRandomAgent(),
                DQN2LayerAgent(weights_file='./dqn/dqn_vs_random.h5f'),
                BalancedRandomAgent())


experiments = {
    'cheat_vs_noncheat_ucb1': CheatVsNonCheatUCB1,

    'relative_vs_absolute_reward': RelativeVsAbsoluteReward,
    'relative_vs_ranking_reward': RelativeVsRankingReward,
    'ranking_vs_absolute_reward': RankingVsAbsoluteReward,

    'tichu_random_vs_never': RandomVsNeverTichu,
    'tichu_always_vs_never': AlwaysVsNeverTichu,

    'first_mcts_then_random_vs_random': FirstMctsThenRandomVsRandom,
    'random_vs_pool_determinization': RandomVsPoolDeterminization,

    'dqn_untrained_vs_random': DQNUntrainedVsRandom,
    'dqnrandom_vs_dqnlearned': DQNRandomVsDQNLearned,
    'dqnrandom_vs_dqnlearning': DQNRandomVsDQNLearning,
    'dqnlearned_vs_dqnlearning': DQNLearnedVsDQNLearning,
    'dqn_vs_random': DQNVsRandom,

    'epic_vs_ismcts': EpicVsIsMcts,
    'ismcts_best_action_maxucb_vs_most_visited': IsmctsBestActionMaxUcbVsMostVisited,
}

log_levels_map = {
    'DEBUG': logging.DEBUG,
    'INFO': logging.INFO,
    'WARNING': logging.WARNING,
    'ERROR': logging.ERROR,
    'CRITICAL': logging.CRITICAL,
}

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Run Experiments', allow_abbrev=False)
    # EXPERIMENT
    parser.add_argument('experiment_name', metavar='experiment_name', type=str, choices=[k for k in experiments.keys()],
                        help='The name of the experiment to run')

    # EXPERIMENT PARAMS
    parser.add_argument('--target', dest='target_points', type=int, required=False, default=1000,
                        help='The number of points to play for')
    parser.add_argument('--min_duration', dest='min_duration', type=int, required=False, default=None,
                        help='Repeat until this amount of minutes passed.')
    parser.add_argument('--max_duration', dest='max_duration', type=int, required=False, default=None,
                        help='Does not start a new experiment when this amount of minutes passed. Must be bigger than --min_duration if specified. Overwrites --nbr_experiments')
    parser.add_argument('--nbr_experiments', dest='nbr_experiments', type=int, required=False, default=1,
                        help='The amount of experiments to run sequentially (Default is 1). If --min_duration is specified, then stops when both constraints are satisfied.')
    # LOGING
    parser.add_argument('--log_mode', dest='log_mode', type=str, required=False, default='ExperimentMode', choices=[k for k in logginginit.logging_modes.keys()],
                        help="{}".format('\n'.join("{}: {}".format(modestr, str(mode)) for modestr, mode in logginginit.logging_modes.items())))
    parser.add_argument('--ignore_debug', dest='ignore_debug', required=False, action='store_true',
                        help='Whether to log debug level (set flag to NOT log debug level). Overwrites the --log_mode setting for debug level')
    parser.add_argument('--ignore_info', dest='ignore_info', required=False, action='store_true',
                        help='Whether to log info level (set flag to NOT log info (and debug) level). Overwrites the --log_mode setting for info level')
    # POOL SIZE
    parser.add_argument('--pool_size', dest='pool_size', type=int, required=False, default=5,
                        help='The amount of workers use in the Pool [default: 5].')

    args = parser.parse_args()
    print("args:", args)

    # Times
    start_t = time()
    max_t = start_t + args.max_duration*60 if args.max_duration else float('inf')
    min_t = start_t + args.min_duration*60 if args.min_duration else -2

    if max_t < min_t:
        raise ValueError("--max_duration must be bigger than --min_duration!")

    # init logging
    start_ftime = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    log_folder_name = "./logs/" + args.experiment_name + "_" + start_ftime

    logmode = logginginit.logging_modes[args.log_mode]
    gym.undo_logger_setup()
    min_loglevel = logging.DEBUG
    if args.ignore_debug:
        min_loglevel = logging.INFO
    if args.ignore_info:
        min_loglevel = logging.WARNING

    logginginit.initialize_loggers(output_dir=log_folder_name, logging_mode=logmode, min_loglevel=min_loglevel)

    # nbr expreiments
    nbr_exp_left = args.nbr_experiments

    # the experiment
    exp = experiments[args.experiment_name]

    # log the arguments
    logger.warning("Experiment summary: ")
    logger.warning("exp: {}; args: {}".format(exp.__name__, args))

    # run several experiments in multiple processors
    pool_size = args.pool_size
    if nbr_exp_left > 1:
        with Pool(processes=pool_size) as pool:
            logger.debug("Running experiments in Pool (of size {})".format(pool_size))
            # run all experiments in Pool
            multiple_results = [pool.apply_async(exp().run, (), {'target_points': args.target_points}) for i in range(nbr_exp_left)]
            # wait for processes to complete
            for res in multiple_results:
                res.get()
                nbr_exp_left -= 1

    # run experiment in parent process
    while (nbr_exp_left > 0 or time() < min_t) and time() < max_t:
        nbr_exp_left -= 1
        exp().run(target_points=args.target_points)

    logger.info("Total Experiments runningtime: {}".format(time_since(start_t)))

