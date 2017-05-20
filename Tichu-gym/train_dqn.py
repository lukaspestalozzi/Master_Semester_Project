import os
import random
import time
import datetime
import gym
import logging

import keras
from gym_tichu.envs.internals.utils import make_sure_path_exists
from profilehooks import timecall

import numpy as np

from keras.models import Sequential, Model
from keras.layers import Dense, Activation, Flatten, Masking, Input, Merge
from keras.optimizers import Adam

from rl.agents.dqn import DQNAgent
from rl.core import Processor
from rl.policy import BoltzmannQPolicy, GreedyQPolicy, LinearAnnealedPolicy
from rl.memory import SequentialMemory

import gym_agents
import logginginit
from gym_tichu.envs.internals.utils import time_since
from gym_agents import BalancedRandomAgent, make_dqn_agent_2layers, make_dqn_agent_4layers, make_dqn_trainagent_4layers, \
    make_dqn_trainagent_2layers

logger = logging.getLogger(__name__)
ENV_NAME = 'tichu_singleplayer-v0'


class EncodedRandomAgent(BalancedRandomAgent):

    def __init__(self):
        super().__init__()

    @timecall(immediate=False)
    def action(self, encoded_state):
        # logger.debug(encoded_state)
        possible = [idx for idx, b in enumerate(encoded_state[-258:]) if b]
        return random.choice(possible)


@timecall(immediate=False)
def run_singleplayer_with_random_agent(goal_reward=1000):
    agent = EncodedRandomAgent()
    env = gym.make(ENV_NAME)
    tot_reward = 0
    while tot_reward < goal_reward:
        obs = env.reset()
        done = False
        reward = None
        while not done:
            action = agent.action(obs)
            logger.debug("Chose action {}".format(action))
            obs, reward, done, info = env.step(action)
        tot_reward += reward
        logger.info("Got reward: {} -> {}".format(reward, tot_reward))


class MyProcessor(Processor):

    # def process_observation(self, observation):
    #     return []

    def process_step(self, observation, r, done, info):
        return observation, r, done, dict()

    def process_state_batch(self, batch):
        # logger.warning("batch: " + str(batch))
        if len(batch) == 1:
            state = batch[0][0]
            # logger.warning("state: {} shape {}, {}".format(state.__class__, state.shape, state))
            # logger.warning("state shapes: {} {}".format(state[0].shape, state[1].shape))
            retbatch = {'cards_input': np.array([state[0]]), 'possible_actions_input': np.array([state[1]])}

            return retbatch

        # logger.warning("Batch > 1: ")
        d = {'cards_input': [], 'possible_actions_input': []}
        for state in batch:
            # logger.warning("state: {} shape {}, {}".format(state.__class__, state.shape, state))
            d['cards_input'].append(state[0][0])
            d['possible_actions_input'].append(state[0][1])
            # logger.warning("shapes: {}, {}".format(processed_state[0].shape, processed_state[1].shape))

            # logger.warning("mybatch: {}".format(mybatch))

        retbatch = [np.array(d['cards_input']), np.array(d['possible_actions_input'])]
        # logger.debug("retbatch: {}".format(retbatch))
        return retbatch


def generate_random_state_batch(batchsize=32):

    return [np.array([[random.random() < 0.2 for _ in range(56*5)] for _ in range(batchsize)]),
            np.array([[random.random() < 0.2 for _ in range(258)] for _ in range(batchsize)])]


# def train_dqn_experimenting():
#     env = gym.make(ENV_NAME)
#     nb_actions = env.action_space.n
#     NB_TRAIN_STEPS = 50000
#     NB_TEST_STEPS = 20
#     weights_file = 'dqn_{}_weights.h5f'.format(ENV_NAME)
#
#     # ######## Build a model. ########
#     main_input_len = 56*5
#     main_input = Input(shape=(main_input_len,), name='cards_input')
#     main_line = Dense(main_input_len, activation='tanh')(main_input)
#     main_line = Dense(nb_actions, activation='sigmoid')(main_line)
#
#     # combine with the possible_actions input
#     possible_actions_input = Input(shape=(258,), name='possible_actions_input')
#     output = keras.layers.add([possible_actions_input, main_line])  # possible_actions_input is 0 where a legal move is, -500 where not. -> should set all illegal actions to -500
#
#     model = Model(inputs=[main_input, possible_actions_input], outputs=[output])
#
#     print(model.summary())
#
#     # ######## Build Agent ########
#     # Finally, we configure and compile our agent. You can use every built-in Keras optimizer and even the metrics!
#     memory = SequentialMemory(limit=50000, window_length=1)
#     policy = LinearAnnealedPolicy(BoltzmannQPolicy(clip=(-500, 300)), attr='tau', value_max=1., value_min=.1, value_test=.01, nb_steps=NB_TRAIN_STEPS)
#     processor = MyProcessor()
#     dqn = DQNAgent(model=model, nb_actions=nb_actions, memory=memory, nb_steps_warmup=100,
#                    target_model_update=1e-2, policy=policy, processor=processor)
#     dqn.compile(Adam(lr=1e-3), metrics=['mae'])
#
#     # ###### Load weights ######
#     dqn.load_weights(weights_file)
#
#     # ######## Fit model. ########
#     # Okay, now it's time to learn something! We visualize the training here for show, but this
#     # slows down training quite a lot. You can always safely abort the training prematurely using
#     # Ctrl + C.
#     dqn.fit(env, nb_steps=NB_TRAIN_STEPS, visualize=False, verbose=1, nb_max_start_steps=0)
#
#     # After training is done, we save the final weights.
#     dqn.save_weights(weights_file, overwrite=True)
#
#     # do some predicitons
#     # batch = generate_random_state_batch()
#     # pred = model.predict_on_batch(batch)
#     # for k in range(len(pred)):
#     #     logger.info("state: {}; {}".format(list(batch[0][k]), list(batch[1][k])))
#     #     logger.info("pred: {}".format(list(pred[k])))
#
#     # ######## Test ########
#     # Finally, evaluate our algorithm for 10 episodes.
#     history = dqn.test(env, nb_episodes=NB_TEST_STEPS, visualize=True)
#     print(history)


def train_dqn_agent(nbr_steps: int, descr: str, env_name, base_folder: str):
    print("Training DQN Agent for {} steps ...".format(nbr_steps))
    agent = gym_agents.agents.agent_to_train

    agent.train(base_folder=base_folder, nbr_steps=nbr_steps, description=descr, env_name=env_name)


if __name__ == '__main__':
    start_t = time.time()
    NBR_STEPS = 100000
    gym.undo_logger_setup()

    env_name = 'tichu_singleplayer_random-v0'
    # env_name = 'tichu_singleplayer_learned-v0'
    # env_name = 'tichu_singleplayer_learning-v0'

    start_ftime = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    description = '{envn}'.format(envn=env_name)

    train_base_folder = base_folder = '../nn_training/{descr}_{t}_steps_{nbr}'.format(
            t=start_ftime, nbr=NBR_STEPS, descr=description)

    log_folder_name = "{base}/my_logs".format(base=train_base_folder)
    logging_mode = logginginit.TrainMode
    logginginit.initialize_loggers(output_dir=log_folder_name, logging_mode=logging_mode, min_loglevel=logging.INFO)

    train_dqn_agent(nbr_steps=NBR_STEPS, descr=description, env_name=env_name, base_folder=train_base_folder)
    print("Training took {}".format(time_since(start_t)))
