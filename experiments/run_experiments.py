import abc
import datetime
import argparse
from collections import namedtuple
from time import time
import multiprocessing as mp
from multiprocessing import Pool

import logging

import sys, os

import gym

from gym_agents.strategies import make_random_tichu_strategy, never_announce_tichu_strategy

this_folder = '/'.join(os.getcwd().split('/')[:])
parent_folder = '/'.join(os.getcwd().split('/')[:-1])
Tichu_gym_folder = parent_folder+"/Tichu-gym"

for p in [this_folder, parent_folder, Tichu_gym_folder]:  # Adds the parent folder (ie. game) to the python path
    if p not in sys.path:
        sys.path.append(p)


from gamemanager import TichuGame
from gym_agents.strategies import make_random_tichu_strategy, never_announce_tichu_strategy, always_announce_tichu_strategy
from gym_agents import BaseMonteCarloAgent, BalancedRandomAgent
from gym_agents.mcts import InformationSetMCTS, InformationSetMCTS_absolute_evaluation
from gym_tichu.envs.internals.utils import time_since
import logginginit


logger = logging.getLogger(__name__)


# print('PATH:', sys.path)
# print('this_folder:', this_folder)
# print('parent_folder:', parent_folder)



class Experiment(object):

    @property
    def name(self)->str:
        return self.__class__.__name__

    @property
    @abc.abstractmethod
    def agents(self)->list:
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

        game_history_string = str(game_res)

        logger.info(results_string)
        logger.debug(game_history_string)

        with open(log_folder_name+"/results.log", "a") as f:
            f.write(results_string)

    @abc.abstractmethod
    def _run_game(self, target_points):
        pass


class CheatVsNonCheatUCB1(Experiment):

    def __init__(self):
        agents = [
            BaseMonteCarloAgent(InformationSetMCTS(), iterations=100, cheat=True),
            BaseMonteCarloAgent(InformationSetMCTS(), iterations=100),
            BaseMonteCarloAgent(InformationSetMCTS(), iterations=100, cheat=True),
            BaseMonteCarloAgent(InformationSetMCTS(), iterations=100)
        ]
        self._agents = agents

    @property
    def agents(self) -> list:
        return self._agents

    def _run_game(self, target_points=1000):

        game = TichuGame(*self.agents)
        return game.start_game(target_points=target_points)


class RelativeVsAbsoluteReward(Experiment):
    def __init__(self):
        agents = [
            BaseMonteCarloAgent(InformationSetMCTS(), iterations=100),
            BaseMonteCarloAgent(InformationSetMCTS_absolute_evaluation(), iterations=100),
            BaseMonteCarloAgent(InformationSetMCTS(), iterations=100),
            BaseMonteCarloAgent(InformationSetMCTS_absolute_evaluation(), iterations=100)
        ]
        self._agents = agents

    @property
    def agents(self) -> list:
        return self._agents

    def _run_game(self, target_points=1000):

        game = TichuGame(*self.agents)
        return game.start_game(target_points=target_points)


class RandomVsNeverTichu(Experiment):
    def __init__(self):
        agents = [
            BalancedRandomAgent(announce_tichu=make_random_tichu_strategy(announce_weight=0.5)),
            BalancedRandomAgent(announce_tichu=never_announce_tichu_strategy),
            BalancedRandomAgent(announce_tichu=never_announce_tichu_strategy),
            BalancedRandomAgent(announce_tichu=never_announce_tichu_strategy),
        ]
        self._agents = agents

    @property
    def agents(self) -> list:
        return self._agents

    def _run_game(self, target_points=1000):

        game = TichuGame(*self.agents, )
        return game.start_game(target_points=target_points)


class AlwaysVsNeverTichu(Experiment):
    def __init__(self):
        agents = [
            BalancedRandomAgent(announce_tichu=always_announce_tichu_strategy),
            BalancedRandomAgent(announce_tichu=never_announce_tichu_strategy),
            BalancedRandomAgent(announce_tichu=never_announce_tichu_strategy),
            BalancedRandomAgent(announce_tichu=never_announce_tichu_strategy),
        ]
        self._agents = agents

    @property
    def agents(self) -> list:
        return self._agents

    def _run_game(self, target_points=1000):

        game = TichuGame(*self.agents, )
        return game.start_game(target_points=target_points)


experiments = {
    'cheat_vs_noncheat_ucb1': CheatVsNonCheatUCB1,
    'relative_vs_absolute_reward': RelativeVsAbsoluteReward,
    'tichu_random_vs_never': RandomVsNeverTichu,
    'tichu_always_vs_never': AlwaysVsNeverTichu,
}


LogMode = namedtuple('LM', ['console_log_level', 'all_log', 'info_log', 'warn_err_log'])
LogMode.__new__.__defaults__ = (logging.DEBUG, 'all.log', 'info.log', 'warn_error.log')  # set default values
log_modes = {
    'cluster': LogMode(console_log_level=None, all_log=None),
    'test': LogMode(console_log_level=logging.INFO),
    'full': LogMode(),
}

log_levels_map = {
    'DEBUG': logging.DEBUG,
    'INFO': logging.INFO,
    'WARNING': logging.WARNING,
    'ERROR': logging.ERROR,
}

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Run Experiments', allow_abbrev=False)
    parser.add_argument('experiment_name', metavar='name', type=str, choices=[k for k in experiments.keys()],
                        help='The name of the experiment to run')

    parser.add_argument('--target', dest='target_points', type=int, required=False, default=1000,
                        help='The number of points to play for')
    parser.add_argument('--min_duration', dest='min_duration', type=int, required=False, default=None,
                        help='Repeat until this amount of minutes passed.')
    parser.add_argument('--max_duration', dest='max_duration', type=int, required=False, default=None,
                        help='Does not start a new experiment when this amount of minutes passed. Must be bigger than --min_duration if specified. Overwrites --nbr_experiments')
    parser.add_argument('--nbr_experiments', dest='nbr_experiments', type=int, required=False, default=1,
                        help='The amount of experiments to run sequentially (Default is 1). If --min_duration is specified, then stops when both constraints are satisfied.')
    parser.add_argument('--log_mode', dest='log_mode', type=str, required=False, default='cluster', choices=[k for k in log_modes.keys()],
                        help='''The logging mode:
                                "cluster": only logs info and above; 
                                "test": logs all, and console log level is Info.
                                "full": logs everything, console log level is Debug
                            ''')
    parser.add_argument('--console_log_level', dest='console_log_level_str', type=str, required=False, default=None, choices=[k for k in log_levels_map.keys()],
                        help='The level of logging printed to console. Overwrites the --log_mode setting for console_log_level')
    parser.add_argument('--ignore_debug', dest='ignore_debug', required=False, action='store_true',
                        help='Whether to log debug level (set flag to NOT log debug level). Overwrites the --log_mode setting for debug level')
    parser.add_argument('--ignore_info', dest='ignore_info', required=False, action='store_true',
                        help='Whether to log info level (set flag to NOT log info level). Overwrites the --log_mode setting for info level')
    parser.add_argument('--pool_size', dest='pool_size', type=int, required=False, default=10,
                        help='The amount of workers use in the Pool.')

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

    logmode = log_modes[args.log_mode]
    gym.undo_logger_setup()
    logginginit.initialize_logger(log_folder_name,
                                  console_log_level=logmode.console_log_level if not args.console_log_level_str else log_levels_map[args.console_log_level_str],
                                  all_log=None if args.ignore_debug else logmode.all_log,
                                  info_log=None if args.ignore_info else logmode.info_log,
                                  warn_err_log=logmode.warn_err_log,
                                  logger_name=None)

    nbr_exp_left = args.nbr_experiments

    exp = experiments[args.experiment_name]

    # run several experiments in multiple processors
    pool_size = 10
    if nbr_exp_left > 1:
        with Pool(processes=pool_size) as pool:
            logger.debug("Running experiments in Pool (of size {})".format(pool_size))
            multiple_results = [pool.apply_async(exp().run, (), {'target_points': args.target_points}) for i in range(nbr_exp_left)]
            # wait for processes to complete
            for res in multiple_results:
                res.get()
                nbr_exp_left -= 1

    while (nbr_exp_left > 0 or time() < min_t) and time() < max_t:
        nbr_exp_left -= 1
        exp().run(target_points=args.target_points)

    logger.info("Total Experiments runningtime: {}".format(time_since(start_t)))

