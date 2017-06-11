import abc
import datetime
import argparse
from collections import namedtuple
from time import time, sleep
import multiprocessing as mp
from multiprocessing import Pool, Lock

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
from gym_agents import *
from gym_agents.mcts import *
from gym_tichu.envs.internals.utils import time_since, check_param
import logginginit


logger = logging.getLogger(__name__)

_this_folder = os.path.dirname(os.path.realpath(__file__))  # Folder where this file is located


class Experiment(object, metaclass=abc.ABCMeta):

    @property
    def name(self)->str:
        return self.__class__.__name__

    @property
    @abc.abstractmethod
    def agents(self)->Tuple[DefaultGymAgent, DefaultGymAgent, DefaultGymAgent, DefaultGymAgent]:
        pass

    def run(self, target_points):
        logger.warning("Running {}".format(self.name))
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

        logger.warning("Finished Running {}".format(self.name))

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


#EPIC
class EpicVsIsMcts(SimpleExperiment):

    def _init_agents(self):
        return (BaseMonteCarloAgent(EpicISMCTS(), iterations=100),
                BaseMonteCarloAgent(InformationSetMCTS(), iterations=100),
                BaseMonteCarloAgent(EpicISMCTS(), iterations=100),
                BaseMonteCarloAgent(InformationSetMCTS(), iterations=100))


class EpicNoRolloutVsEpic(SimpleExperiment):
    def _init_agents(self):
        return (BaseMonteCarloAgent(EpicNoRollout(), iterations=100),
                BaseMonteCarloAgent(EpicISMCTS(), iterations=100),
                BaseMonteCarloAgent(EpicNoRollout(), iterations=100),
                BaseMonteCarloAgent(EpicISMCTS(), iterations=100))


class EpicNoRolloutVsIsmcts(SimpleExperiment):
    def _init_agents(self):
        return (BaseMonteCarloAgent(EpicNoRollout(), iterations=100),
                BaseMonteCarloAgent(InformationSetMCTS(), iterations=100),
                BaseMonteCarloAgent(EpicNoRollout(), iterations=100),
                BaseMonteCarloAgent(InformationSetMCTS(), iterations=100))


# BEST ACTION
class BestAction_MaxUcb_Vs_MostVisited(SimpleExperiment):

    def _init_agents(self):
        return (BaseMonteCarloAgent(InformationSetMCTSHighestUcbBestAction(), iterations=100),
                BaseMonteCarloAgent(InformationSetMCTS(), iterations=100),
                BaseMonteCarloAgent(InformationSetMCTSHighestUcbBestAction(), iterations=100),
                BaseMonteCarloAgent(InformationSetMCTS(), iterations=100))


# REWARD
class Reward_Relative_Vs_Absolute(SimpleExperiment):

    def _init_agents(self):
        return (BaseMonteCarloAgent(InformationSetMCTS_relative_evaluation(), iterations=100),
                BaseMonteCarloAgent(InformationSetMCTS_absolute_evaluation(), iterations=100),
                BaseMonteCarloAgent(InformationSetMCTS_relative_evaluation(), iterations=100),
                BaseMonteCarloAgent(InformationSetMCTS_absolute_evaluation(), iterations=100))


class Reward_Relative_Vs_Ranking(SimpleExperiment):
    def _init_agents(self):
        return (BaseMonteCarloAgent(InformationSetMCTS_relative_evaluation(), iterations=100),
                BaseMonteCarloAgent(InformationSetMCTS(), iterations=100),
                BaseMonteCarloAgent(InformationSetMCTS_relative_evaluation(), iterations=100),
                BaseMonteCarloAgent(InformationSetMCTS(), iterations=100))


class Reward_Ranking_Vs_Absolute(SimpleExperiment):

    def _init_agents(self):
        return (BaseMonteCarloAgent(InformationSetMCTS(), iterations=100),
                BaseMonteCarloAgent(InformationSetMCTS_absolute_evaluation(), iterations=100),
                BaseMonteCarloAgent(InformationSetMCTS(), iterations=100),
                BaseMonteCarloAgent(InformationSetMCTS_absolute_evaluation(), iterations=100))


# Move Groups
class MoveGroups_With_Vs_No(SimpleExperiment):

    def _init_agents(self):
        return (BaseMonteCarloAgent(InformationSetMCTS_move_groups(), iterations=1200, max_time=10),
                BaseMonteCarloAgent(DefaultIsmcts(), iterations=1000, max_time=10),
                BaseMonteCarloAgent(InformationSetMCTS_move_groups(), iterations=1200, max_time=10),
                BaseMonteCarloAgent(DefaultIsmcts(), iterations=1000, max_time=10))


# TICHU
class Tichu_Random_Vs_Never(SimpleExperiment):

    def _init_agents(self):
        return (BalancedRandomAgent(announce_tichu=make_random_tichu_strategy(announce_weight=0.5)),
                BalancedRandomAgent(announce_tichu=never_announce_tichu_strategy),
                BalancedRandomAgent(announce_tichu=never_announce_tichu_strategy),
                BalancedRandomAgent(announce_tichu=never_announce_tichu_strategy),)


class Tichu_Always_Vs_Never(SimpleExperiment):

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
                BaseMonteCarloAgent(InformationSetMCTSPoolDeterminization(), iterations=100),
                BaseMonteCarloAgent(InformationSetMCTS(), iterations=100),
                BaseMonteCarloAgent(InformationSetMCTSPoolDeterminization(), iterations=100))


class RandomVsSingleDeterminization(SimpleExperiment):

    def _init_agents(self):

        return (BaseMonteCarloAgent(make_default_ismctsearch(name='Det_Random', determinizationpolicy=RandomDeterminePolicy), iterations=1200, max_time=10, cheat=False),
                BaseMonteCarloAgent(make_default_ismctsearch(name='Det_Single', determinizationpolicy=SingleDeterminePolicy), iterations=1200, max_time=10, cheat=False),
                BaseMonteCarloAgent(make_default_ismctsearch(name='Det_Random', determinizationpolicy=RandomDeterminePolicy), iterations=1200, max_time=10, cheat=False),
                BaseMonteCarloAgent(make_default_ismctsearch(name='Det_Single', determinizationpolicy=SingleDeterminePolicy), iterations=1200, max_time=10, cheat=False))


class SingleVsPoolDeterminization(SimpleExperiment):

    def _init_agents(self):
        return (BaseMonteCarloAgent(InformationSetMCTSSingleDeterminization(), iterations=100),
                BaseMonteCarloAgent(InformationSetMCTSPoolDeterminization(), iterations=100),
                BaseMonteCarloAgent(InformationSetMCTSSingleDeterminization(), iterations=100),
                BaseMonteCarloAgent(InformationSetMCTSPoolDeterminization(), iterations=100))



# DQN
class DQNUntrainedVsRandom(SimpleExperiment):

    def _init_agents(self):
        return (DQNAgent2L_56x5(weights_file=None),
                BalancedRandomAgent(),
                DQNAgent2L_56x5(weights_file=None),
                BalancedRandomAgent())


class DQNRandomVsDQNLearned(SimpleExperiment):

    def _init_agents(self):
        return (DQNAgent2L_56x5(weights_file='{}/dqn/dqn_random.h5f'.format(_this_folder)),
                DQNAgent2L_56x5(weights_file='{}/dqn/dqn_learned.h5f'.format(_this_folder)),
                DQNAgent2L_56x5(weights_file='{}/dqn/dqn_random.h5f'.format(_this_folder)),
                DQNAgent2L_56x5(weights_file='{}/dqn/dqn_learned.h5f'.format(_this_folder)))


class DQNRandomVsDQNLearning(SimpleExperiment):

    def _init_agents(self):
        return (DQNAgent2L_56x5(weights_file='{}/dqn/dqn_random.h5f'.format(_this_folder)),
                DQNAgent2L_56x5(weights_file='{}/dqn/dqn_learning.h5f'.format(_this_folder)),
                DQNAgent2L_56x5(weights_file='{}/dqn/dqn_random.h5f'.format(_this_folder)),
                DQNAgent2L_56x5(weights_file='{}/dqn/dqn_learning.h5f'.format(_this_folder)))


class DQNLearnedVsDQNLearning(SimpleExperiment):

    def _init_agents(self):
        return (DQNAgent2L_56x5(weights_file='{}/dqn/dqn_learned.h5f'.format(_this_folder)),
                DQNAgent2L_56x5(weights_file='{}/dqn/dqn_learning.h5f'.format(_this_folder)),
                DQNAgent2L_56x5(weights_file='{}/dqn/dqn_learned.h5f'.format(_this_folder)),
                DQNAgent2L_56x5(weights_file='{}/dqn/dqn_learning.h5f'.format(_this_folder)))


class DQNRandomVsDQNismcts(SimpleExperiment):

    def _init_agents(self):
        return (DQNAgent2L_56x5(weights_file='{}/dqn/dqn_random.h5f'.format(_this_folder)),
                DQNAgent2L_56x5(weights_file='{}/dqn/dqn_ismcts.h5f'.format(_this_folder)),
                DQNAgent2L_56x5(weights_file='{}/dqn/dqn_random.h5f'.format(_this_folder)),
                DQNAgent2L_56x5(weights_file='{}/dqn/dqn_ismcts.h5f'.format(_this_folder)))


class DQNLearnedVsDQNismcts(SimpleExperiment):

    def _init_agents(self):
        return (DQNAgent2L_56x5(weights_file='{}/dqn/dqn_learned.h5f'.format(_this_folder)),
                DQNAgent2L_56x5(weights_file='{}/dqn/dqn_ismcts.h5f'.format(_this_folder)),
                DQNAgent2L_56x5(weights_file='{}/dqn/dqn_learned.h5f'.format(_this_folder)),
                DQNAgent2L_56x5(weights_file='{}/dqn/dqn_ismcts.h5f'.format(_this_folder)))


class DQNLearningVsDQNismcts(SimpleExperiment):

    def _init_agents(self):
        return (DQNAgent2L_56x5(weights_file='{}/dqn/dqn_learning.h5f'.format(_this_folder)),
                DQNAgent2L_56x5(weights_file='{}/dqn/dqn_ismcts.h5f'.format(_this_folder)),
                DQNAgent2L_56x5(weights_file='{}/dqn/dqn_learning.h5f'.format(_this_folder)),
                DQNAgent2L_56x5(weights_file='{}/dqn/dqn_ismcts.h5f'.format(_this_folder)))


class DQNUntrainedVsDQNismcts(SimpleExperiment):

    def _init_agents(self):
        return (DQNAgent2L_56x5(weights_file=None),
                DQNAgent2L_56x5(weights_file='{}/dqn/dqn_ismcts.h5f'.format(_this_folder)),
                DQNAgent2L_56x5(weights_file=None),
                DQNAgent2L_56x5(weights_file='{}/dqn/dqn_ismcts.h5f'.format(_this_folder)))


# Multiple Experiments Together
class MultipleExperiments(Experiment):

    def __init__(self, experiment_clazzes, nbr_to_run_each: int, parallel: bool, poolsize: int=5):
        self.experiment_clazzes = experiment_clazzes
        self.nbr_to_run_each = nbr_to_run_each
        self.parallel = parallel
        self._current_agents = None
        self.poolsize = poolsize
        assert nbr_to_run_each > 0

    @property
    def name(self) -> str:
        return ' and '.join(ex.__name__ for ex in self.experiment_clazzes)

    @property
    def agents(self):
        raise AttributeError("MultipleExperiments has no agents, this should not be used")

    def run(self, target_points):
        if self.parallel:
            return self._run_parallel(target_points=target_points)
        else:
            return self._run_sequential(target_points=target_points)

    def _run_parallel(self, target_points):
        """
        Runs all experiments in different processes. (in a pool of size 'self.poolsize')
        :param target_points: 
        :return: None
        """
        logger.warning("Running the MultipleExperiments in Pool (of size {}): {}  ({} times each)".format(self.poolsize, self.experiment_clazzes, self.nbr_to_run_each))
        assert self.poolsize > 0

        with Pool(processes=self.poolsize) as pool:
            # run all experiments in Pool
            jobs = list()
            for n in range(self.nbr_to_run_each):
                for exp in self.experiment_clazzes:
                    experiment = exp()
                    print("experiment: ", experiment)
                    jobs.append(pool.apply_async(experiment.run, (), {'target_points': target_points}))

            # wait for processes to complete
            for k, job in enumerate(jobs):
                logger.warning("waiting for job {k}".format(k=k))
                job.get()

        print("Pool exit")

    def _run_sequential(self, target_points):
        """
        Runs all experiments in this process.
        Each experiment is run 'self.nbr_to_run_each' times.
        
        :param target_points: 
        :return: None
        """
        logger.warning("Running the MultipleExperiments sequential")
        for n in range(self.nbr_to_run_each):
            for exp in self.experiment_clazzes:
                logger.warning("Sequential MultipleExperiments starting {}".format(exp))
                # logger.warning("agents: "+str(list(a.info for a in exp().agents)))
                exp().run(target_points=target_points)

    def _run_game(self, target_points):
        raise AttributeError("MultipleExperiments has single game to be run, this should not be used")

    # To be able to do:
    # exp = MultipleExperiments([exp1, exp2], nbr_to_run_each=2, parallel=True)
    # exp().run(target_points=args.target_points)
    #     ^
    def __call__(self):
        return self


class Tournament(Experiment):
    """
    Given some agents plays each agent against each other agent once.
    NOTE: There are n*(n+1)/2 games played.
    """

    def __init__(self, *agents):
        check_param(len(agents) >= 2)
        self.participating_agents = list(agents)

    @property
    def agents(self) -> Tuple[DefaultGymAgent, DefaultGymAgent, DefaultGymAgent, DefaultGymAgent]:
        raise AttributeError("Tournament has no agents, this should not be used")

    def _run_game(self, target_points):
        raise AttributeError("Tournament has no agents, this should not be used")

    def run(self, target_points):
        for k0, agent0 in enumerate(self.participating_agents):
            for agent1 in self.participating_agents[k0+1:]:
                expclazz = type("Tournament_{}_vs_{}".format(agent0.__class__.__name__, agent1.__class__.__name__),
                                (SimpleExperiment, object),
                                {'_init_agents': lambda self_: (agent0, agent1, agent0, agent1)})
                exp = expclazz()
                logger.warning("Tournament starting game {}".format(exp))
                exp.run(target_points=target_points)

    # To be able to do:
    # exp = Tournament(agent1, agent2)
    # exp().run(target_points=args.target_points)
    #     ^
    def __call__(self):
        return self


experiments = {

    'best_action_tournament': Tournament(
            BaseMonteCarloAgent(
                    make_default_ismctsearch(name='BestAction_MostVisited', bestactionpolicy=MostVisitedBestActionPolicy),
                    iterations=100, cheat=False
            ),
            BaseMonteCarloAgent(
                    make_default_ismctsearch(name='BestAction_MaxUCB', bestactionpolicy=HighestUCBBestActionPolicy),
                    iterations=100, cheat=False
            ),
            BaseMonteCarloAgent(
                    make_default_ismctsearch(name='BestAction_HighestAvgReward', bestactionpolicy=HighestAvgRewardBestActionPolicy),
                    iterations=100, cheat=False
            )

    ),

    'determinization_tournament': Tournament(
            BaseMonteCarloAgent(
                    make_default_ismctsearch(name='Det_Random', determinizationpolicy=RandomDeterminePolicy),
                    iterations=1200, max_time=10, cheat=False
            ),
            BaseMonteCarloAgent(
                    make_default_ismctsearch(name='Det_Pool', determinizationpolicy=PoolDeterminePolicy),
                    iterations=1200, max_time=10, cheat=False
            ),
            BaseMonteCarloAgent(
                    make_default_ismctsearch(name='Det_Single', determinizationpolicy=SingleDeterminePolicy),
                    iterations=1200, max_time=10, cheat=False
            )

    ),

    'reward_tournament': Tournament(
            BaseMonteCarloAgent(
                    make_default_ismctsearch(name='Eval_Ranking', evaluationpolicy=RankingEvaluationPolicy),
                    iterations=1200, max_time=5, cheat=False
            ),
            BaseMonteCarloAgent(
                    make_default_ismctsearch(name='Eval_Absolute', evaluationpolicy=AbsoluteEvaluationPolicy),
                    iterations=1200, max_time=5, cheat=False
            ),
            BaseMonteCarloAgent(
                    make_default_ismctsearch(name='Eval_Relative', evaluationpolicy=RelativeEvaluationPolicy),
                    iterations=1200, max_time=5, cheat=False
            ),
            BaseMonteCarloAgent(
                    make_default_ismctsearch(name='Eval_Norm_Relative', evaluationpolicy=RelativeNormalizedEvaluationPolicy),
                    iterations=1200, max_time=5, cheat=False
            ),
            BaseMonteCarloAgent(
                    make_default_ismctsearch(name='Eval_Norm_Absolute', evaluationpolicy=AbsoluteNormalizedEvaluationPolicy),
                    iterations=1200, max_time=5, cheat=False
            )
    ),

    'split_tournament': Tournament(
            make_first_ismcts_then_random_agent(switch_length=9),
            make_first_ismcts_then_random_agent(switch_length=7),
            make_first_ismcts_then_random_agent(switch_length=5),
            make_first_ismcts_then_random_agent(switch_length=3),
            BalancedRandomAgent()
    ),

    'split_tournament_upper': Tournament(
            make_first_ismcts_then_random_agent(switch_length=13),
            make_first_ismcts_then_random_agent(switch_length=12),
            make_first_ismcts_then_random_agent(switch_length=11),
            make_first_ismcts_then_random_agent(switch_length=10),
            make_first_ismcts_then_random_agent(switch_length=9),
            BalancedRandomAgent()
    ),

    'epic_tournament': Tournament(
            BaseMonteCarloAgent(
                    make_default_ismctsearch(name='Epic_ismcts', nodeidpolicy=EpicNodePolicy),
                    iterations=1200, max_time=5, cheat=True
            ),
            BaseMonteCarloAgent(
                    make_default_ismctsearch(name='Epic_norollout', nodeidpolicy=EpicNodePolicy, treepolicy=NoRolloutPolicy),
                    iterations=1200, max_time=5, cheat=True
            ),
            BaseMonteCarloAgent(DefaultIsmcts(), iterations=1200, max_time=5, cheat=True),
            
    ),

    'nn_rollout_tournament': Tournament(
            BaseMonteCarloAgent(
                    make_default_ismctsearch(name='2L_ismcts', rolloutpolicy=DQNAgent2L_56x5_2_sepRolloutPolicy),
                    iterations=1200, max_time=5, cheat=True
            ),
            BaseMonteCarloAgent(DefaultIsmcts(), iterations=1200, max_time=5, cheat=True),
            BalancedRandomAgent(),
            # TODO add more agents
    ),

    'best_tournament': Tournament(
            BaseMonteCarloAgent(
                    make_best_ismctsearch(name='Best'),
                    iterations=100, cheat=False
            ),
            BaseMonteCarloAgent(
                    make_best_ismctsearch(name='Best_randomRollout', rolloutpolicy=RandomRolloutPolicy),
                    iterations=100, cheat=False
            ),
            BaseMonteCarloAgent(
                    make_best_ismctsearch(name='Best_randomRollout', determinizationpolicy=RandomDeterminePolicy),
                    iterations=100, cheat=False
            ),
            BaseMonteCarloAgent(
                    make_best_ismctsearch(name='Best_movegroups', treepolicy=MoveGroupsTreeSelectionPolicy),
                    iterations=100, cheat=False
            ),
            BaseMonteCarloAgent(DefaultIsmcts(), iterations=100, cheat=False),
    ),

    'minmax_tournament': Tournament(
            MinimaxAgent(depth=9),
            BaseMonteCarloAgent(DefaultIsmcts(), iterations=100, cheat=False),
            BalancedRandomAgent()
    ),

    'cheat_tournament': Tournament(
            BaseMonteCarloAgent(DefaultIsmcts(), iterations=100, cheat=False),
            BaseMonteCarloAgent(DefaultIsmcts(), iterations=100, cheat=0.2),
            BaseMonteCarloAgent(DefaultIsmcts(), iterations=100, cheat=0.6),
            BaseMonteCarloAgent(DefaultIsmcts(), iterations=100, cheat=0.8),
            BaseMonteCarloAgent(DefaultIsmcts(), iterations=100, cheat=True),
    ),

    'cheat_vs_noncheat': CheatVsNonCheatUCB1,

    'all_rewards': MultipleExperiments([Reward_Relative_Vs_Absolute, Reward_Relative_Vs_Ranking, Reward_Ranking_Vs_Absolute], nbr_to_run_each=10, parallel=True),
    'relative_vs_absolute_reward': Reward_Relative_Vs_Absolute,
    'relative_vs_ranking_reward': Reward_Relative_Vs_Ranking,
    'ranking_vs_absolute_reward': Reward_Ranking_Vs_Absolute,

    'all_split_experiments': MultipleExperiments([FirstMctsThenRandomVsRandom], nbr_to_run_each=10, parallel=True),
    'first_mcts_then_random_vs_random': FirstMctsThenRandomVsRandom,

    'all_determinization_vs': MultipleExperiments([RandomVsPoolDeterminization], nbr_to_run_each=10, parallel=True),
    'random_vs_pool_determinization': RandomVsPoolDeterminization,
    'random_vs_single_determinization': RandomVsSingleDeterminization,
    'single_vs_pool_determinization': SingleVsPoolDeterminization,

    'all_dqn_vs_dqn': MultipleExperiments([DQNUntrainedVsRandom, DQNRandomVsDQNLearned,
                                           DQNRandomVsDQNLearning, DQNLearnedVsDQNLearning,
                                           DQNRandomVsDQNismcts, DQNLearnedVsDQNismcts,
                                           DQNLearningVsDQNismcts, DQNUntrainedVsDQNismcts],
                                          nbr_to_run_each=1, parallel=False),

    'dqn_untrained_vs_random_agent': DQNUntrainedVsRandom,
    'dqn_random_vs_learned': DQNRandomVsDQNLearned,
    'dqn_random_vs_learning': DQNRandomVsDQNLearning,
    'dqn_learned_vs_learning': DQNLearnedVsDQNLearning,
    'dqn_random_vs_dqnismcts': DQNRandomVsDQNismcts,
    'dqn_learned_vs_dqnismcts': DQNLearnedVsDQNismcts,
    'dqn_learning_vs_dqnismcts': DQNLearningVsDQNismcts,
    'dqn_untrained_vs_dqnismcts': DQNUntrainedVsDQNismcts,

    'all_epic_vs': MultipleExperiments([EpicVsIsMcts, EpicNoRolloutVsEpic, EpicNoRolloutVsIsmcts], nbr_to_run_each=10, parallel=True),
    'epic_vs_ismcts': EpicVsIsMcts,
    'epic_norollout_vs_epic': EpicNoRolloutVsEpic,
    'epic_norollout_vs_ismcts': EpicNoRolloutVsIsmcts,

    'ismcts_best_action_maxucb_vs_most_visited': BestAction_MaxUcb_Vs_MostVisited,

    'move_groups_vs_none': MoveGroups_With_Vs_No,

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
    try:
        expname = exp.__name__
    except AttributeError:
        # exp is probably a MultipleExperiments instance
        expname = exp.name
    logger.warning("exp: {}; args: {}".format(expname, args))

    # run several experiments in multiple processors
    pool_size = args.pool_size
    if nbr_exp_left > 1 and pool_size > 1:
        with Pool(processes=pool_size) as pool:
            logger.warning("Running experiments in Pool (of size {})".format(pool_size))
            # run all experiments in Pool
            multiple_results = list()
            for i in range(nbr_exp_left):
                multiple_results.append(pool.apply_async(exp().run, (), {'target_points': args.target_points}))
            # wait for processes to complete
            for res in multiple_results:
                res.get()
                nbr_exp_left -= 1

    # run experiment in parent process
    while (nbr_exp_left > 0 or time() < min_t) and time() < max_t:
        logger.warning("Running a experiment in parent process... ")
        nbr_exp_left -= 1
        exp().run(target_points=args.target_points)

    logger.info("Total Experiments runningtime: {}".format(time_since(start_t)))

