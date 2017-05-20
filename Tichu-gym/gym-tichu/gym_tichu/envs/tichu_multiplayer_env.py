from typing import Callable, Optional, Collection, Tuple, Set, Any, Iterable, Union

import random
import gym
import logging
import itertools
import numpy as np

from gym import spaces
from profilehooks import timecall


from .internals import *
from .internals.error import IllegalActionError, LogicError


logger = logging.getLogger(__name__)

__all__ = ('TichuMultiplayerEnv', 'TichuSinglePlayerAgainstRandomEnv',
           'TichuSinglePlayerAgainstLatestQAgentEnv', 'TichuSinglePlayerAgainstTheTrainingQAgentEnv')


class TichuMultiplayerEnv(gym.Env):
    metadata = {'render.modes': ['human']}

    def __init__(self, illegal_move_mode: str='raise', verbose: bool=True):
        """
        :param illegal_move_mode: 'raise' or 'loose'. If 'raise' an exception is raised, 'loose' and the team looses 200:0
        :param verbose: if True, logs to the info log, if false, logs to the debug log
        """
        assert illegal_move_mode in ['raise'], "'loose' is not yet implemented"  # ['raise', 'loose']

        super().__init__()

        self._current_state = None
        self.verbose = verbose
        self._reset()

    def _step(self, action: Any)-> Tuple[TichuState, int, bool, dict]:
        logger.debug("_step with action {}".format(action))

        state = self._current_state.next_state(action)
        self._current_state = state

        done = state.is_terminal()
        points = state.count_points() if done else (0, 0, 0, 0)
        if done:
            state = state.change(history=state.history.add_last_state(state))
        return state, points, done, dict()  # state, reward, done, info

    def _reset(self)->InitialState:
        self._current_state = InitialState()
        return self._current_state

    def _render(self, mode='human', close=False):
        # print("RENDER: ", self._current_state)
        pass

    def _log(self, message, *args, **kwargs):
        if self.verbose:
            logger.info(message, *args, **kwargs)
        else:
            logger.debug(message, *args, **kwargs)


class TichuSinglePlayerAgainstRandomEnv(gym.Env):
    metadata = {'render.modes': ['human']}

    def __init__(self, illegal_move_mode: str='loose', verbose: bool=True):
        """
        :param illegal_move_mode: 'raise' or 'loose'. If 'raise' an exception is raised, 'loose' and the team looses 200:0
        :param verbose: if True, logs to the info log, if false, logs to the debug log
        """
        assert illegal_move_mode in ['loose'], "'raise' is not yet implemented"  # ['raise', 'loose']

        super().__init__()

        self.agents = [None] + self._make_3_enemy_agents()

        self._general_combinations = list(all_general_combinations_gen())
        self.action_space = spaces.Discrete(len(self._general_combinations)+1)  # +1 because there is also the Pass action
        self.nbr_to_gcomb = {idx: gcomb for idx, gcomb in enumerate(self._general_combinations)}
        self.gcomb_to_nbr = {v: k for k, v in self.nbr_to_gcomb.items()}
        self.pass_action = PassAction(0)
        self.pass_action_nbr = len(self._general_combinations)
        logging.debug("self.pass_action_nbr: {}".format(self.pass_action_nbr))

        self.observation_space = spaces.MultiBinary(56*5+258)

        self.nbr_action = {self.pass_action_nbr: self.pass_action}  # dictionary used to keep directly track of nbrs -> actual actions. This dict changes during the game

        self._current_state = None
        self.verbose = verbose
        self._reset()

    @timecall(immediate=False)
    def _step(self, action: Union[int, PlayerAction])-> Tuple[Any, int, bool, dict]:
        try:
            # logger.debug("State: {}".format(self._current_state))
            # logger.debug(" Action {} ({})".format(action, action.__class__))
            # logger.debug("nbr->action dict: {}".format(self.nbr_action))
            #
            # poss_actions_encoding = list(self.encode_state(self._current_state)[1])
            # legal_int_actions = [idx for idx, a in enumerate(poss_actions_encoding) if a]
            # logger.debug("Legal actions: {}".format(legal_int_actions))

            action = self.nbr_action[int(action)]
            # logger.debug(" -> {}".format(action))
        except ValueError:
            logger.debug("Action is not an int: {}".format(action))
            pass  # action is not an int, so it must be a PlayerAction
        except KeyError:
            logger.debug("Action was not in the nbr_action dict (probably illegal action): {}".format(action))
            pass  # Action was not in the nbr_action dict (probably illegal action), lets see what happens...

        try:
            self._current_state = self._current_state.next_state(action)
            # logger.debug("Legal Action! {}".format(action))
        except IllegalActionError:
            logger.debug("Illegal Action! {}, legal are: {}".format(action, [idx for idx, a in enumerate(list(self.encode_state(self._current_state)[1])) if a]))
            return self.encode_state(self._current_state), -500, True, {'illegalAction': action}

        state = self._forward_to_player()
        self._current_state = state

        done = state.is_terminal()
        assert done or state.player_pos == 0
        if done:
            logger.debug("TichuSinglePlayerAgainstRandomEnv, Final State: {}".format(state))

        reward = state.count_points()[0] if done else 0
        return self.encode_state(state), reward, done, {'state': state}  # state, reward, done, info

    def _reset(self)->TichuState:
        self._current_state = InitialState().announce_grand_tichus([]).announce_tichus([]).trade_cards(trades=list())
        self._current_state = self._forward_to_player()
        # logger.debug("Done Resetting")
        return self.encode_state(self._current_state)

    def _forward_to_player(self)->TichuState:
        """
        
        :return: The next state in which the player 0 can play a Combiantion.
        """
        # logger.debug("Forwarding to player 0")
        state = self._current_state

        if state.is_terminal():
            logger.debug("State is already terminal, Nothing to forward.")
            return state

        first_action = state.possible_actions_list[0]
        # Note: for both tichu and wish action, state.player_pos is not the same as action.player_pos, it is the pos of the next player to play a combination

        while not isinstance(first_action, (PassAction, PlayCombination)) or first_action.player_pos != 0:
            # logger.debug("state: {}".format(state))
            # TICHU
            if isinstance(first_action, TichuAction):
                no_tichu_action = next(filter(lambda act: act.announce is False, state.possible_actions_list))
                state = state.next_state(no_tichu_action)

            # WISH
            elif isinstance(first_action, WishAction):
                no_wish_action = WishAction(player_pos=first_action.player_pos, wish=None)
                state = state.next_state(no_wish_action)

            # TRICK ENDS
            elif isinstance(first_action, WinTrickAction):
                state = state.next_state(first_action)

            # Play Combination
            elif isinstance(first_action, (PassAction, PlayCombination)):
                assert state.player_pos != 0
                # predefined agents choose action

                action = self.agents[state.player_pos].action(state=state)
                state = state.next_state(action)

            else:
                raise LogicError()

            if state.is_terminal():
                # logger.debug("State is terminal -> break out of forward to player")
                # logger.debug("Final State: {}".format(state))
                break

            first_action = state.possible_actions_list[0]

        return state

    def _render(self, mode='human', close=False):
        pass
        # if mode == 'human':
        #     logger.info("Render: {}".format(self._current_state))

    def _log(self, message, *args, **kwargs):
        if self.verbose:
            logger.info(message, *args, **kwargs)
        else:
            logger.debug(message, *args, **kwargs)

    def _make_3_enemy_agents(self)->list:
        from gym_agents import BalancedRandomAgent
        return [BalancedRandomAgent(), BalancedRandomAgent(), BalancedRandomAgent()]

    @timecall(immediate=False)
    def encode_state(self, state: TichuState)->Any:
        """
        Return a 1D binary numpy.array of length 56*4+258:
        
        The first 5*56 positions represent the handcards of the 4 players + trick on table ( each length 56)
        the rest the indexes of the possible general-combinations (length 258)
        
        """
        def encode_cards(cards: Iterable[Card]):
            l = [False]*56
            for c in state.handcards.iter_all_cards(player=0):
                l[c.number] = True
            return l

        encoded = []
        for cards in state.handcards:
            encoded.extend(encode_cards(cards))

        encoded.extend(encode_cards(state.trick_on_table.last_combination))

        # clear the nbr->action dict
        self.nbr_action = {self.pass_action_nbr: self.pass_action}

        encoded_gen_actions = [-500]*(len(self.gcomb_to_nbr)+1)
        for action in state.possible_actions_list:
            if isinstance(action, PassAction):
                nbr = self.pass_action_nbr
            else:
                gcomb = GeneralCombination.from_combination(action.combination)
                try:
                    nbr = self.gcomb_to_nbr[gcomb]
                except KeyError:
                    logging.debug("comb: {}".format(action.combination))
                    logging.debug("gcomb: {}".format(gcomb))
                    raise
            encoded_gen_actions[nbr] = 0
            self.nbr_action[nbr] = action

        assert len(encoded) == 56*5
        assert len(encoded_gen_actions) == 258
        enc = (np.array(encoded, dtype=bool), np.array(encoded_gen_actions))
        # logger.warning("enc: {}".format(enc))
        return enc


class TichuSinglePlayerAgainstLatestQAgentEnv(TichuSinglePlayerAgainstRandomEnv):

    def _make_3_enemy_agents(self)->list:
        from gym_agents import make_dqn_agent_2layers
        return [make_dqn_agent_2layers('./dqn_2layers_weights.h5f'),
                make_dqn_agent_2layers('./dqn_2layers_weights.h5f'),
                make_dqn_agent_2layers('./dqn_2layers_weights.h5f')]


class TichuSinglePlayerAgainstTheTrainingQAgentEnv(TichuSinglePlayerAgainstRandomEnv):

    def _make_3_enemy_agents(self)->list:
        from gym_agents.agents import agent_to_train
        return [agent_to_train, agent_to_train, agent_to_train]
