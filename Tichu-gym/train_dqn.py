import abc
import argparse
import os
import time
import datetime

import gym
import logging

from gym_agents import BalancedRandomAgent, DQNAgent2L_56x5, BaseMonteCarloAgent
import logginginit
from gym_tichu.envs.internals.utils import time_since

from gym_agents.keras_rl_utils import TichuSinglePlayerTrainEnv
from gym_agents.mcts import InformationSetMCTS

logger = logging.getLogger(__name__)


if __name__ == '__main__':
    poss_envs = {'random': lambda _=None: (BalancedRandomAgent(), BalancedRandomAgent(), BalancedRandomAgent()),
                 'learned': lambda _=None: (DQNAgent2L_56x5(), DQNAgent2L_56x5(), DQNAgent2L_56x5()),
                 'learning': lambda agent: (agent, agent, agent),
                 'ismcts': lambda _=None: (BaseMonteCarloAgent(InformationSetMCTS(), iterations=50, cheat=True))}

    poss_agents = {'dqn_2l56x6': DQNAgent2L_56x5}

    parser = argparse.ArgumentParser(description='Train Agent', allow_abbrev=False)
    # ENV
    parser.add_argument('env', metavar='environment_name', type=str, choices=[k for k in poss_envs.keys()],
                        help='The name environment to rain on')

    # Steps
    parser.add_argument('steps', metavar='steps', type=int,
                        help='The number of steps to train for.')

    # Agent
    parser.add_argument('--agent', dest='agent', type=str, choices=[k for k in poss_envs.keys()], required=False, default='dqn_2l56x6',
                        help='The agent to be trained. default: dqn_2l56x6')

    args = parser.parse_args()
    print("train agent args:", args)

    start_t = time.time()
    start_ftime = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

    NBR_STEPS = args.steps
    AGENT = poss_agents[args.agent]()
    ENV = TichuSinglePlayerTrainEnv(processor=AGENT.processor)
    ENV.configure(other_agents=poss_envs[args.env](AGENT))

    gym.undo_logger_setup()

    description = '{agentinfo}_{envn}'.format(agentinfo=AGENT.__class__.__name__, envn=args.env)

    # Folders
    parent_folder = '/'.join(os.path.dirname(os.path.realpath(__file__)).split("/")[:-1])
    train_base_folder = '{parent_folder}/nn_training/{descr}_{t}_steps_{nbr}'.format(parent_folder=parent_folder,
            t=start_ftime, nbr=NBR_STEPS, descr=description)

    log_folder_name = "{base}/my_logs".format(base=train_base_folder)

    # Logging
    logging_mode = logginginit.DebugMode
    logginginit.initialize_loggers(output_dir=log_folder_name, logging_mode=logging_mode, min_loglevel=logging.DEBUG)

    # Training
    print("Training DQN Agent for {} steps ...".format(NBR_STEPS))

    AGENT.train(env=ENV, base_folder=train_base_folder, nbr_steps=NBR_STEPS)

    print("Training time: {}".format(time_since(start_t)))
