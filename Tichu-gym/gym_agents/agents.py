import abc
import os
import logging

import rl

import logginginit
import random
from typing import Union, Optional, List, Set, Tuple, Collection, Any, Iterable, Dict
from collections import defaultdict, OrderedDict

import gym
from gym_tichu.envs.internals import (TichuState, PlayerAction, CardRank, Card, wishable_card_ranks,
                                      PassAction, CardTrade, HandCards)
import numpy as np

import keras
from keras.models import Sequential, Model
from keras.layers import Dense, Activation, Flatten, Masking, Input, Merge
from keras.optimizers import Adam

from rl.agents.dqn import DQNAgent
from rl.core import Processor
from rl.policy import BoltzmannQPolicy, GreedyQPolicy, LinearAnnealedPolicy
from rl.memory import SequentialMemory


from .q_learning import DQNProcessor
from .mcts import MCTS, InformationSetMCTS, InformationSetMCTS_absolute_evaluation, EpicISMCTS
from . import strategies

__all__ = ('DefaultGymAgent', 'RandomAgent', 'BalancedRandomAgent', 'BaseMonteCarloAgent', 'HumanInputAgent',
           'information_set_mcts_agent', 'information_set_mcts_absolute_evaluation_agent', 'epic_ismcts_agent',
           'DQNTichuAgent', 'dqn_agent_2layers', 'dqn_agent_4layers')

logger = logging.getLogger(__name__)
human_logger = logginginit.CONSOLE_LOGGER


class DefaultGymAgent(object):
    """
    Returns the first action presented to it
    """

    def __init__(self, announce_tichu: strategies.TichuStrategyType=strategies.never_announce_tichu_strategy,
                       announce_grand_tichu: strategies.TichuStrategyType=strategies.never_announce_tichu_strategy,
                       make_wish: strategies.WishStrategyType=strategies.random_wish_strategy,
                       trade: strategies.TradingStrategyType=strategies.random_trading_strategy,
                       give_dragon_away: strategies.DragonAwayStrategyType=strategies.give_dragon_to_the_right_strategy):

        self.announce_tichu = announce_tichu
        self.announce_grand_tichu = announce_grand_tichu
        self.make_wish = make_wish
        self.trade = trade
        self.give_dragon_away = give_dragon_away

    @property
    def info(self):
        return "{me.__class__.__name__}, Takes always the first action".format(me=self)

    def action(self, state):
        logger.debug("BaseAgent chooses from actions: {}".format([str(a) for a in state.possible_actions()]))
        return next(state.possible_actions())


class RandomAgent(DefaultGymAgent):
    """
    Returns one of the possible actions at random
    """

    def action(self, state):
        logger.debug("RandomAgent chooses from actions: {}".format([str(a) for a in state.possible_actions()]))
        return random.choice(list(state.possible_actions()))


class BalancedRandomAgent(RandomAgent):
    """
    Chooses one combination type first, then returns one of the possible actions of this type (at random)
    """

    def action(self, state):
        logger.debug("BalancedRandomAgent chooses from actions: {}".format([str(a) for a in state.possible_actions()]))
        d = defaultdict(list)
        for action in state.possible_actions():
            try:
                d[action.combination].append(action)
            except AttributeError:
                d[action.__class__].append(action)

        return random.choice(d[random.choice(list(d.keys()))])


class BaseMonteCarloAgent(DefaultGymAgent):

    def __init__(self, search_algorithm: MCTS, iterations: int=100, cheat: bool=False):
        super().__init__()
        self._search = search_algorithm
        self.iterations = iterations
        self.cheat = cheat

    @property
    def info(self):
        return "{me.__class__.__name__}, {me._search.info}, iterations: {me.iterations}, cheat: {me.cheat}".format(me=self)

    def action(self, state: TichuState)->PlayerAction:
        if len(state.possible_actions_set) == 1:
            act = next(iter(state.possible_actions_set))
            logger.debug("There is only one possible action: {}".format(act))
            return act
        return self._search.search(root_state=state,
                                   observer_id=state.player_pos,
                                   iterations=self.iterations,
                                   cheat=self.cheat)

    def __str__(self):
        return "{me.__class__.__name__}({me.search.__class__.__name__}, {me.iterations}, {me.cheat})".format(me=self)


information_set_mcts_agent = BaseMonteCarloAgent(InformationSetMCTS())
information_set_mcts_absolute_evaluation_agent = BaseMonteCarloAgent(InformationSetMCTS_absolute_evaluation())
epic_ismcts_agent = BaseMonteCarloAgent(EpicISMCTS())


class HumanInputAgent(DefaultGymAgent):

    def __init__(self, position: int):
        super().__init__(announce_tichu=HumanInputAgent.announce_tichu,
                         announce_grand_tichu=HumanInputAgent._announce_grand_tichu,
                         make_wish=HumanInputAgent.make_wish,
                         trade=HumanInputAgent.trade,
                         give_dragon_away=HumanInputAgent.give_dragon_away)

        assert position in range(4)
        self._position = position
        human_logger.info(f"You are Player Number {self._position}")
        human_logger.info(f"Your Teammate is {(self._position + 2) % 4}")
        self._can_announce_tichu = True

    @staticmethod
    def give_dragon_away(state: TichuState, player: int)->int:
        e_left = (player  - 1) % 4
        e_right = (player + 1) % 4
        human_logger.info("You won the Trick with the Dragon. Therefore you have to give it away.")
        human_logger.info("Whom do you want to give it?")
        human_logger.info("The enemy to the left ({e_left}) has {el_cards} cards, the enemy to the right ({e_right}) has {er_cards} cards left".format(e_left=e_left, el_cards=len(state.handcards[e_left]),
                                                                                                                                           e_right=e_right, er_cards=len(state.handcards[e_right])))
        pl_pos = int(HumanInputAgent.ask_user_to_choose_one_of([str((player + 1) % 4), str((player - 1) % 4)]))
        return pl_pos

    @staticmethod
    def make_wish(state: TichuState, player: int)->CardRank:
        human_logger.info(f"You played the MAHJONG ({str(Card.MAHJONG)}) -> You may wish a card Value:")
        answ = HumanInputAgent.ask_user_to_choose_one_of([cv.name for cv in wishable_card_ranks])
        cv = CardRank.from_name(answ)
        return cv

    @staticmethod
    def trade(state: TichuState, player: int)->Tuple[Card, Card, Card]:
        human_logger.info("Random Cards are being Traded for you!")
        return strategies.random_trading_strategy(state, player)

    @staticmethod
    def _announce_grand_tichu(state: TichuState, already_announced: Set[int], player: int):
        return HumanInputAgent._ask_announce_tichu(state.handcards[player], announced_tichu=set(), announced_grand_tichu=already_announced, grand=True)

    @staticmethod
    def announce_tichu(state: TichuState, already_announced: Set[int], player: int):
        return HumanInputAgent._ask_announce_tichu(state.handcards[player], announced_tichu=already_announced, announced_grand_tichu=state.announced_grand_tichu)

    def action(self, state: TichuState)->PlayerAction:
        if state.trick_on_table.is_empty():
            human_logger.info("Your turn to Play first. There is no Trick on the Table.")

        else:
            human_logger.info("Your turn to Play:")
            human_logger.info("Current Trick on the Table: "+str(state.trick_on_table))
            human_logger.info("On the Table is following Combination: {}".format(str(state.trick_on_table.last_combination)))

        human_logger.info(f"You have following cards: {list(map(str, (sorted(state.handcards[self._position]))))}")
        if state.wish:
            human_logger.info(f"If you can you have to play a {state.wish} because this is the wish of the MAHJONG.")

        possible_actions = state.possible_actions_list
        pass_ = False
        possible_combinations = []
        comb_action_dict = {}
        for action in possible_actions:
            if isinstance(action, PassAction):
                pass_ = "PASS"
                comb_action_dict[pass_] = action
            else:
                comb_action_dict[action.combination] = action
                possible_combinations.append(action.combination)

        possible_combinations = sorted(possible_combinations, key=lambda comb: (len(comb), comb.height))
        if pass_:
            possible_combinations.insert(0, pass_)

        comb = self.ask_user_to_choose_with_numbers(possible_combinations)

        return comb_action_dict[comb]

    def traded_cards_received(self, card_trades: CardTrade):
        print("You received following Cards during swapping:")
        for sw in card_trades:
            relative_pos = 'Teammate'
            if sw.from_ == (self._position + 1) % 4:
                relative_pos = 'Enemy Right'
            elif sw.from_ == (self._position - 1) % 4:
                relative_pos = 'Enemy Left'
            print(f"From {sw.from_}({relative_pos}) you got {sw.card}")
        self.ask_user_for_keypress()

    @staticmethod
    def _ask_announce_tichu(handcards: HandCards, announced_tichu: Set[int], announced_grand_tichu: Set[int], grand: bool=False):
        if len(announced_grand_tichu):
            human_logger.info("Following Players announced a Grand Tichu: {}".format(announced_grand_tichu))
        if len(announced_tichu):
            human_logger.info("Following Players announced a Normal Tichu: {}".format(announced_tichu))

        human_logger.info(f"Your handcards are: {handcards}")
        answ = HumanInputAgent.ask_user_yes_no_question("Do you want to announce a {}Tichu?".format("Grand-" if grand else ""))
        assert answ in {True, False}
        return answ

    @staticmethod
    def ask_user_to_choose_one_of(possible_answers: List[Any])->Any:
        options_dict = OrderedDict([(k, k) for k in possible_answers])
        answer, _ = HumanInputAgent.ask_user_to_choose_from_options(options_dict)
        return answer

    @staticmethod
    def ask_user_to_choose_with_numbers(options: Iterable[Any])->Any:
        """
        Asks the user to choose one of the options, but makes it easier by numbering the options and the user only has to enter the number.
        :param options:
        :return: The chosen option
        """
        options_dict = OrderedDict(sorted((nr, o) for nr, o in enumerate(options)))
        inpt, comb = HumanInputAgent.ask_user_to_choose_from_options(options_dict)
        return comb

    @staticmethod
    def ask_user_yes_no_question(question: str)->bool:
        """
        Asks the user to answer the question.
        :param question: string
        :return: True if the answer is 'Yes', False if the answer is 'No'.
        """
        inpt, val = HumanInputAgent.ask_user_to_choose_from_options({'y': 'Yes', 'n': 'No'}, text=question + " \n{}\n")
        return val == 'Yes'

    @staticmethod
    def ask_user_to_choose_from_options(answer_option_dict,
                                        text: str='Your options: \n{}\n',
                                        no_option_text: str="You have no options, press Enter to continue.\n",
                                        one_option_text: str="You have only one option ({}), press Enter to choose it.\n"):

        """
        1 Displays the mapping from keys to values in option_answer_dict. (If key and value are the same, only key is displayed)

        2 and asks the user to choose one of the key values (waiting for user input is blocking).

        3 Repeats the previous steps until the input matches with one of the keys.

        4 Then returns the chosen key and corresponding value.

        :param answer_option_dict: Dictionary of answer -> option mappings. where answer is the text the user has to input to choose the option.
        :param text: Text displayed when there are 2 or more options. It must contain one {} where the possible options should be displayed.
        :param no_option_text: Text displayed when there is no option to choose from.
        :param one_option_text: Text displayed when there is exactly 1 option to choose from. It must contain one {} where the possible option is displayed.
        :return: The key, value pair (as tuple) chosen by the user. If the dict is empty, returns (None, None).
        """

        if len(answer_option_dict) == 0:
            HumanInputAgent.ask_user_for_input(no_option_text)
            return None, None
        elif len(answer_option_dict) == 1:
            HumanInputAgent.ask_user_for_input(one_option_text.format(next(iter(answer_option_dict.values()))))
            return next(iter(answer_option_dict.items()))
        else:
            answer_option_dict = OrderedDict({str(k): o for k, o in answer_option_dict.items()})
            opt_string = "\n".join("'"+str(answ)+"'"+(" for "+str(o) if answ != o else "") for answ, o in answer_option_dict.items())
            possible_answers = {str(k) for k in answer_option_dict}
            while True:
                inpt = HumanInputAgent.ask_user_for_input(text.format(opt_string))
                if inpt in possible_answers:
                    human_logger.info("You chose: {} -> {}".format(inpt, answer_option_dict[inpt]))
                    return inpt, answer_option_dict[inpt]
                else:
                    human_logger.info("Wrong input, please try again.")

    @staticmethod
    def ask_user_for_keypress():
        """
        Asks the user to press any key.
        :return: The input given by the user
        """
        return HumanInputAgent.ask_user_for_input("Press Enter to continue.")

    @staticmethod
    def ask_user_for_input(text: str)->str:
        """
        Displays the text and waits for user input
        :param text:
        :return: The user input
        """
        human_logger.info(text)
        return input()


class LearningAgent(DefaultGymAgent):

    def __init__(self, agent: rl.core.Agent, weights_file: Optional[str]):
        super().__init__()
        self.agent = agent
        if weights_file:
            print("{} loading the weights from {}".format(self.__class__.__name__, weights_file))
            try:
                self.agent.load_weights(weights_file)
            except OSError as oserr:
                logger.error("Could not load file. Continuing with previous weights.")
                logger.exception(oserr)

    def action(self, state: TichuState)->PlayerAction:
        if len(state.possible_actions_list) == 1:
            logger.debug("Q-agent has only 1 possible action: {}".format(state.possible_actions_list[0]))
            return state.possible_actions_list[0]
        processed_state, nbr_action_dict = self._process_tichu_state(state)
        chosen_nbr = self.agent.forward(processed_state)
        action = self._tichu_action_from_number(nbr=chosen_nbr, state=state, nbr_action_dict=nbr_action_dict)
        logger.debug("Q-agent chooses action {} -> {}".format(chosen_nbr, action))
        return action

    def train(self, weights_out_file: str, nbr_steps: int=1000):
        """
        Trains the agent
        :param weights_out_file: saves the weights to that file after training.
        :param nbr_steps: 
        """
        raise NotImplementedError()

    def _process_tichu_state(self, state: TichuState)->Tuple[Any, Dict[int, PlayerAction]]:
        raise NotImplementedError()

    def _tichu_action_from_number(self, nbr: int, state: TichuState, nbr_action_dict: Dict[int, PlayerAction])->PlayerAction:
        raise NotImplementedError()


NBR_TICHU_ACTIONS = 258


def _make_2Layer_model()->Model:
    main_input_len = 56 * 5
    main_input = Input(shape=(main_input_len,), name='cards_input')
    main_line = Dense(main_input_len, activation='tanh')(main_input)
    main_line = Dense(NBR_TICHU_ACTIONS, activation='sigmoid')(main_line)

    # combine with the possible_actions input
    possible_actions_input = Input(shape=(NBR_TICHU_ACTIONS,), name='possible_actions_input')
    output = keras.layers.add([possible_actions_input, main_line])  # possible_actions_input is 0 where a legal move is, -500 where not. -> should set all illegal actions to -500

    model = Model(inputs=[main_input, possible_actions_input], outputs=[output])
    return model


def _make_4Layer_model()->Model:
    main_input_len = 56 * 5
    main_input = Input(shape=(main_input_len,), name='cards_input')
    main_line = Dense(NBR_TICHU_ACTIONS*5, activation='tanh')(main_input)
    main_line = Dense(NBR_TICHU_ACTIONS*5, activation='elu')(main_line)
    main_line = Dense(NBR_TICHU_ACTIONS, activation='relu')(main_line)
    main_line = Dense(NBR_TICHU_ACTIONS, activation='sigmoid')(main_line)

    # combine with the possible_actions input
    possible_actions_input = Input(shape=(NBR_TICHU_ACTIONS,), name='possible_actions_input')
    output = keras.layers.add([possible_actions_input, main_line])  # possible_actions_input is 0 where a legal move is, -500 where not. -> should set all illegal actions to -500

    model = Model(inputs=[main_input, possible_actions_input], outputs=[output])
    return model


def _make_dqn_agent(model)->DQNAgent:
    memory = SequentialMemory(limit=50000, window_length=1)
    # TODO maybe parametrizise the nb_steps for annealingPolicy
    policy = LinearAnnealedPolicy(BoltzmannQPolicy(clip=(-500, 300)), attr='tau', value_max=1., value_min=.1, value_test=.01, nb_steps=100000)
    processor = DQNProcessor()
    dqn = DQNAgent(model=model, nb_actions=NBR_TICHU_ACTIONS, memory=memory, nb_steps_warmup=100,
                   target_model_update=1e-2, policy=policy, processor=processor)
    dqn.compile(Adam(lr=1e-3), metrics=['mae'])
    return dqn


class DQNTichuAgent(LearningAgent):

    def __init__(self, model: Model, weights_file: Optional[str]):
        self.weights_file = weights_file
        self.model = model
        self.processor = self._make_processor()
        agent = self._make_agent()
        super().__init__(agent=agent, weights_file=weights_file)

    def train(self, weights_out_file: str, nbr_steps: int=1000):
        """
        Trains on the 'tichu_singleplayer-v0' environment.
        :param weights_out_file: saves the weights to that file after training.
        :param nbr_steps: 
        """
        self.agent.fit(gym.make('tichu_singleplayer-v0'), nb_steps=nbr_steps, visualize=False, verbose=1, nb_max_start_steps=0)
        logger.info("saving the weights to {}".format(weights_out_file))
        self.agent.save_weights(weights_out_file, overwrite=True)

    def _process_tichu_state(self, state: TichuState)->Any:
        return self.processor.encode_tichu_state(state)

    def _tichu_action_from_number(self, nbr: int, state: TichuState, nbr_action_dict: Dict[int, PlayerAction])->PlayerAction:
        try:
            return nbr_action_dict[nbr]
        except KeyError:
            logging.warning("KeyError in _tichu_action_from_number. Probably Illegal action. returning random Possible action!")
            return random.choice(state.possible_actions_list)

    def _make_agent(self):
        return _make_dqn_agent(self.model)

    def _make_processor(self):
        return DQNProcessor()


dqn_agent_2layers = DQNTichuAgent(model=_make_2Layer_model(), weights_file='{}/agent_weights/dqn_2layers_weights.h5f'.format(os.path.dirname(os.path.realpath(__file__))))
dqn_agent_4layers = DQNTichuAgent(model=_make_4Layer_model(), weights_file='{}/agent_weights/dqn_4layers_weights.h5f'.format(os.path.dirname(os.path.realpath(__file__))))
