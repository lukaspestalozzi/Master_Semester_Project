import abc
from typing import Any, Dict, Tuple, Iterable
import logging
import numpy as np

import keras
from keras.models import Model
from keras.layers import Dense, Activation, Flatten, Masking, Input, Merge
from keras.optimizers import Adam

from rl.agents.dqn import DQNAgent
from rl.core import Processor, Env, MultiInputProcessor
from rl.policy import BoltzmannQPolicy, GreedyQPolicy, LinearAnnealedPolicy
from rl.memory import SequentialMemory

from gym_tichu.envs.internals import (all_general_combinations_gen, BaseTichuState, PlayerAction, Card, PassAction, GeneralCombination)
from gym_tichu.envs import TichuSinglePlayerEnv

logger = logging.getLogger(__name__)

NBR_TICHU_ACTIONS = 258

# ### Processors ###
PASS_ACTION_NBR = 257
all_general_combinations = list(all_general_combinations_gen())
GENERALCOMBINATION_TO_NBR = {gcomb: idx for idx, gcomb in enumerate(all_general_combinations)}
NBR_TO_GENERALCOMBINATION = {v: k for k, v in GENERALCOMBINATION_TO_NBR.items()}


class Processor_56x5(Processor):

    def __init__(self):
        super().__init__()
        self.pass_action = PassAction(0)
        self.nbr_action_dict = {PASS_ACTION_NBR: self.pass_action}  # dictionary used to keep directly track of nbrs -> actual actions. This dict changes during the game

    # My functions
    def encode_tichu_state(self, state: BaseTichuState)->Any:
        """
        Encodes the tichu-state for the NN,
        :param state: 
        :return: the encoded state and a dict mapping move nbrs to the action represented by that nbr.
        """
        # logger.debug("ecode tichu state: {}".format(state))

        def encode_cards(cards: Iterable[Card]):
            l = [False]*56
            if cards:
                for c in cards:
                    l[c.number] = True
            return l

        # encode handcards
        encoded = []
        for ppos in ((state.player_pos + k) % 4 for k in range(4)):
            # The players handcards are always in first position
            encoded.extend(encode_cards(state.handcards[ppos]))

        # encode trick on table
        encoded.extend(encode_cards(state.trick_on_table.last_combination))

        # encode possible actions
        encoded_gen_actions = [-500]*(len(all_general_combinations)+1)
        for action in state.possible_actions_list:
            if isinstance(action, PassAction):
                nbr = PASS_ACTION_NBR
            else:
                gcomb = GeneralCombination.from_combination(action.combination)
                try:
                    nbr = GENERALCOMBINATION_TO_NBR[gcomb]
                except KeyError:
                    logger.debug("comb: {}".format(action.combination))
                    logger.debug("gcomb: {}".format(gcomb))
                    logger.debug("dict: {}".format('\n'.join(map(str, GENERALCOMBINATION_TO_NBR.items()))))
                    raise
            encoded_gen_actions[nbr] = 0
            self.nbr_action_dict[nbr] = action

        assert len(encoded) == 56*5
        assert len(encoded_gen_actions) == 258
        enc = (np.array(encoded, dtype=bool), np.array(encoded_gen_actions))
        # logger.warning("enc: {}".format(enc))
        return enc

    def decode_action(self, action)->PlayerAction:
        try:
            t_action = self.nbr_action_dict[action]
        except KeyError:
            logger.debug("Process Action KeyError, There is probably no action possible.")  #action: {}, dict: {}".format(action, self.nbr_action_dict))
            t_action = action  # Happens when no action is possible
        # logger.debug('process_action: {} -> t_action {}'.format(action, t_action))
        return t_action

    def create_model(self, nbr_layers: int=2):
        """
        Creates the keras model for this processor with the given amount of hidden (dense) layers.
        :param nbr_layers: must be bigger or equal to 1
        :return: 
        """
        assert nbr_layers >= 1
        nbr_layers -= 1
        main_input_len = 56 * 5
        main_input = Input(shape=(main_input_len,), name='cards_input')
        main_line = Dense(NBR_TICHU_ACTIONS * 5, activation='elu')(main_input)
        for _ in range(nbr_layers):
            main_line = Dense(NBR_TICHU_ACTIONS, activation='elu')(main_line)

        # combine with the possible_actions input
        possible_actions_input = Input(shape=(NBR_TICHU_ACTIONS,), name='possible_actions_input')
        output = keras.layers.add([possible_actions_input, main_line])  # possible_actions_input is 0 where a legal move is, -500 where not. -> should set all illegal actions to -500

        model = Model(inputs=[main_input, possible_actions_input], outputs=[output])
        return model

    def process_state_batch(self, batch):
        """
        
        :param batch: batch of keras-rl observations
        :return: 
        """
        # logger.debug("process state batch")
        # logger.warning("batch: " + str(batch))
        if len(batch) == 1:
            state = list(batch[0][0])
            # logger.warning("list(batch[0][0]): {}".format(state))
            # logger.warning("list(batch[0][0])[0] class: {}".format(state[0].__class__))
            if isinstance(state[0], BaseTichuState):
                state = self.encode_tichu_state(state[0])

            # logger.warning("encoded state: {}".format(state))
            retbatch = {'cards_input': np.array([state[0]]), 'possible_actions_input': np.array([state[1]])}

            return retbatch

        # logger.warning("Batch len > 1: ")
        d = {'cards_input': [], 'possible_actions_input': []}
        for state in batch:
            # logger.warning("state: {} shape {}, {}".format(state.__class__, state.shape, state))
            d['cards_input'].append(state[0][0])
            d['possible_actions_input'].append(state[0][1])
            # logger.warning("shapes: {}, {}".format(processed_state[0].shape, processed_state[1].shape))
            #
            # logger.warning("mybatch: {}".format(mybatch))

        retbatch = [np.array(d['cards_input']), np.array(d['possible_actions_input'])]
        # logger.debug("retbatch: {}".format(retbatch))
        return retbatch

    # def process_action(self, action):
    #     """
    #
    #     :param action: keras action (int probably)
    #     :return: PlayerAction
    #     """
    #     if isinstance(action, PlayerAction):
    #         return action
    #     else:
    #         try:
    #             t_action = self.nbr_action_dict[action]
    #         except KeyError:
    #             logger.debug("Process Action KeyError, There is probably no action possible.")  #action: {}, dict: {}".format(action, self.nbr_action_dict))
    #             t_action = action  # Happens when no action is possible
    #         # logger.debug('process_action: {} -> t_action {}'.format(action, t_action))
    #         return t_action

    # def process_observation(self, observation: BaseTichuState):
    #     logger.debug("Process observation. {}".format(observation))
    #     if isinstance(observation, BaseTichuState):
    #         return self._encode_tichu_state(observation)
    #     else:
    #         return observation


def make_dqn_rl_agent(type: str='56x5', nbr_layers=2):
    """
    
    :param type: 
    :param nbr_layers: 
    :return: 
    """
    if type == '56x5':
        processor = Processor_56x5()
        model = processor.create_model(nbr_layers=nbr_layers)
        test_policy = GreedyQPolicy()
        memory = SequentialMemory(limit=50000, window_length=1)

        dqn_agent = DQNAgent(model=model, nb_actions=NBR_TICHU_ACTIONS, memory=memory, nb_steps_warmup=100, target_model_update=1e-2, test_policy=test_policy, processor=processor)
        dqn_agent.compile(Adam(lr=1e-3), metrics=['mae'])
        return dqn_agent
    else:
        raise ValueError("Unknown type: {}; possible types are: {}".format(type, ['56x5']))


class TichuSinglePlayerTrainEnv(Env, metaclass=abc.ABCMeta):

    def __init__(self, processor: Processor_56x5, verbose: bool=True):
        super().__init__()
        self.game = TichuSinglePlayerEnv()
        self.processor = processor

    def reset(self):
        state = self.game._reset()
        return self.processor.encode_tichu_state(state)

    def step(self, action):
        playeraction = self.processor.decode_action(action)
        state, r, done, info = self.game._step(playeraction)
        return self.processor.encode_tichu_state(state), r, done, info

    def render(self, mode='human', close=False):
        pass

    def configure(self, *args, **kwargs):
        return self.game.configure(*args, **kwargs)

    def close(self):
        pass

    def seed(self, seed=None):
        pass

