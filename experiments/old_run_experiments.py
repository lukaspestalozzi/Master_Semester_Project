import abc
import datetime
import argparse
from collections import namedtuple
from time import time
import multiprocessing as mp
from multiprocessing import Pool

import logging

import sys, os

this_folder = '/'.join(os.getcwd().split('/')[:])
parent_folder = '/'.join(os.getcwd().split('/')[:-1])

for p in [this_folder, parent_folder]:  # Adds the parent folder (ie. game) to the python path
    if p not in sys.path:
        sys.path.append(p)

# print('PATH:', sys.path)
# print('this_folder:', this_folder)
# print('parent_folder:', parent_folder)

from game.tichu import (HumanInputAgent, SimpleMonteCarloPerfectInformationAgent, RandomAgent,
                        ISMctsUCB1Agent, ISMctsEpicAgent, ISMctsLGRAgent, ISMctsEpicLGRAgent,
                        ISMctsUCB1Agent_old_evalAgent)
from game.tichu import Team
from game.tichu import TichuPlayer
from game.tichu import TichuGame, logginginit


class Experiment(object):

    @property
    def name(self)->str:
        return self.__class__.__name__

    @property
    @abc.abstractmethod
    def players(self)->list:
        pass

    def run(self, target_points):
        stime = time()
        start_ftime = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

        players_vs_string = "0: {0}\n2: {2} \nVS.\n1: {1}\n3: {3}\n\n".format(*[p.agent_info() for p in self.players])
        logging.info("Playing: \n" + players_vs_string)

        res = self._run_game(target_points=target_points)

        res_string = res.pretty_string()
        out_string = "\n\n################################## "+self.name.upper()+" ##################################\n"
        out_string += "start-time: {}\n".format(start_ftime) + "\n"
        out_string += "end-time: {}\n".format(datetime.datetime.now().strftime("%Y-%m-%d_%H:%M")) + "\n"
        time_in_seconds = time() - stime
        out_string += "duration: {} seconds ({} hours,{} minutes and {} seconds)\n".format(time_in_seconds,
                                                                                           (time_in_seconds // 60) // 60,
                                                                                           time_in_seconds // 60,
                                                                                           time_in_seconds % 60) + "\n"
        out_string += players_vs_string
        out_string += "Outcome: " + str(res.points) + "\n"

        info_string = out_string  # copy before adding game history

        out_string += res_string + "\n"

        logging.info(out_string)
        logging.info(info_string)

        with open(log_folder_name+"/results.log", "a") as f:
            f.write(info_string)

    @abc.abstractmethod
    def _run_game(self, target_points):
        pass


class CheatVsNonCheatUCB1(Experiment):

    def __init__(self):
        players = [
            TichuPlayer(name="player0", agent=ISMctsUCB1Agent(iterations=100, cheat=True)),
            TichuPlayer(name="player1", agent=ISMctsUCB1Agent(iterations=100, cheat=False)),
            TichuPlayer(name="player2", agent=ISMctsUCB1Agent(iterations=100, cheat=True)),
            TichuPlayer(name="player3", agent=ISMctsUCB1Agent(iterations=100, cheat=False)),
        ]
        self._players = players
        self.team1 = Team(player1=players[0], player2=players[2])
        self.team2 = Team(player1=players[1], player2=players[3])

    @property
    def players(self) -> list:
        return self._players

    def _run_game(self, target_points=1000):

        game = TichuGame(self.team1, self.team2, target_points=target_points)
        return game.start_game()


class RelativeVsAbsoluteReward(Experiment):
    def __init__(self):
        players = [
            TichuPlayer(name="player0", agent=ISMctsUCB1Agent(iterations=100, cheat=False)),
            TichuPlayer(name="player1", agent=ISMctsUCB1Agent_old_evalAgent(iterations=100, cheat=False)),
            TichuPlayer(name="player2", agent=ISMctsUCB1Agent(iterations=100, cheat=False)),
            TichuPlayer(name="player3", agent=ISMctsUCB1Agent_old_evalAgent(iterations=100, cheat=False)),
        ]
        self._players = players
        self.team1 = Team(player1=players[0], player2=players[2])
        self.team2 = Team(player1=players[1], player2=players[3])

    @property
    def players(self) -> list:
        return self._players

    def _run_game(self, target_points=1000):
        game = TichuGame(self.team1, self.team2, target_points=target_points)
        return game.start_game()


experiments = {
    'cheat_vs_noncheat_ucb1': CheatVsNonCheatUCB1,
    'relative_vs_absolute_reward': RelativeVsAbsoluteReward
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
    logginginit.initialize_logger(log_folder_name,
                                  console_log_level=logmode.console_log_level if not args.console_log_level_str else log_levels_map[args.console_log_level_str],
                                  all_log=None if args.ignore_debug else logmode.all_log,
                                  info_log=None if args.ignore_info else logmode.info_log,
                                  warn_err_log=logmode.warn_err_log)

    nbr_exp_left = args.nbr_experiments

    exp = experiments[args.experiment_name]

    # run several experiments in multiple processors
    if nbr_exp_left > 1:
        with Pool(processes=10) as pool:
            multiple_results = [pool.apply_async(exp().run, (), {'target_points': args.target_points}) for i in range(nbr_exp_left)]
            # wait for processes to complete
            for res in multiple_results:
                res.get()
                nbr_exp_left -= 1

    while (nbr_exp_left > 0 or time() < min_t) and time() < max_t:
        nbr_exp_left -= 1
        exp().run(target_points=args.target_points)

    print("Total runningtime: {} seconds".format(time() - start_t))

