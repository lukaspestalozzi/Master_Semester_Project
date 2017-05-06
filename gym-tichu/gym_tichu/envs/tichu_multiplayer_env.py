from typing import Callable, Optional, Collection, Tuple

import random
import gym
from gym import error, spaces, utils
from gym.utils import seeding

from .internals import *


try:
   pass
except ImportError as e:
    raise error.DependencyNotInstalled("{}. (HINT: you can install the dependencies with 'pip install gym[tichu].)'".format(e))

__all__ = ('TichuMultiplayerEnv',)

Tuple4OptionalCallables = Tuple[Optional[Callable], Optional[Callable], Optional[Callable], Optional[Callable]]


def default_trading_strategy(state: TichuState, player: int) -> Tuple[Card, Card, Card]:
    sc = state.handcards[player].random_cards(3)
    return tuple(sc)


def default_wish_strategy(state: TichuState, player: int) -> CardRank:
    wish = random.choice(list(all_wish_actions_gen()))
    return wish


def default_announce_tichu_strategy(*args, **kwargs) -> bool:
    return False


def default_announce_grand_tichu_strategy(*args, **kwargs) -> bool:
    return False


class TichuMultiplayerEnv(gym.Env):
    metadata = {'render.modes': ['human']}

    def __init__(self, trading_strategies: Collection[Callable[[TichuState, int], Tuple[Card, Card, Card]]],
                 wish_strategies: Collection[Callable[[TichuState, int], CardRank]],
                 announce_tichu_strategies: Collection[Callable[[TichuState, Collection[int], int], bool]],
                 announce_grand_tichu_strategies: Collection[Callable[[TichuState, Collection[int], int], bool]],
                 illegal_move_mode: str='raise'):
        """
        :param trading_strategies: 
        :param wish_strategies: 
        :param announce_tichu_strategies: 
        :param announce_grand_tichu_strategies: 
        :param illegal_move_mode: 'raise' or 'loose'. If 'raise' an exception is raised, 'loose' and the team looses 200:0
        """
        assert illegal_move_mode in ['raise'], 'loose is not yet implemented'  # ['raise', 'loose']
        assert all((len(s) == 4 for s in [trading_strategies, wish_strategies, announce_tichu_strategies, announce_grand_tichu_strategies]))

        # Strategies
        self._trading_strategies = tuple([(ts if ts else default_trading_strategy) for ts in trading_strategies])
        self._wish_strategies = tuple([(ws if ws else default_wish_strategy) for ws in wish_strategies])
        self._announce_tichu_strategies = tuple([(ats if ats else default_announce_tichu_strategy) for ats in announce_tichu_strategies])
        self._announce_grand_tichu_strategies = tuple([(agts if agts else default_announce_grand_tichu_strategy) for agts in announce_grand_tichu_strategies])

        self._current_state: TichuState = None
        self._reset()

    def _setup_initial_state(self)->Tuple[TichuState, TichuState, TichuState, TichuState, TichuState, TichuState]:
        """
        
        :return: tuple of the following states (in this order): 
        - initial (without any cards)
        - when all players got 8 cards
        - after all players decided to announce grand tichu (or not)
        - after all players got 14 cards
        - after all players decided to announce tichu (or not)
        - after all players traded their 3 cards. This is then the initial state and the player with the mahjong can play next.
        """
        s_initial = TichuState.initial()
        s_8cards = TichuState.distributed_8_cards()
        # grand tichu
        announced_gt = set()
        for ppos, strategy in enumerate(self._announce_grand_tichu_strategies):
            if strategy(state=s_8cards, already_announced=set(announced_gt), player=ppos):
                announced_gt.add(ppos)
        s_after_gt = s_8cards.announce_grand_tichus(player_positions=announced_gt)
        # distribute remaining cards
        s_14cards = s_after_gt.distribute_14_cards()

        # players may announce tichu now
        announced_t = set()
        for ppos, strategy in enumerate(self._announce_tichu_strategies):
            if ppos not in announced_gt and strategy(state=s_14cards, already_announced=set(announced_t), player=ppos):
                announced_t.add(ppos)
        s_before_trading = s_14cards.announce_tichus(player_positions=announced_t)

        # trade cards
        traded_cards = list()
        for ppos, strategy in enumerate(self._trading_strategies):
            tc = strategy(state=s_before_trading, player=ppos)
            # some checks
            assert len(set(tc)) == len(tc)  # cant trade the same card twice
            assert all(s_14cards.has_cards(player=ppos, card=c) for c in tc)  # player must have the card

            traded_cards.append(CardTrade(from_=ppos, to=(ppos-1)%4, card=tc[0]))
            traded_cards.append(CardTrade(from_=ppos, to=(ppos + 2) % 4, card=tc[1]))
            traded_cards.append(CardTrade(from_=ppos, to=(ppos + 1) % 4, card=tc[2]))

        s_traded = s_before_trading.trade_cards(trades=traded_cards)

        return (s_initial, s_8cards, s_after_gt, s_14cards, s_before_trading, s_traded)

    def _step(self, action: PlayerAction)-> Tuple[TichuState, int, bool, dict]:
        state = self._current_state.next_state(action=action)
        self._current_state = state
        # handle tichu and wish actions:
        # TODO if wish action in state.possible_actions then apply wish_strategy
        # TODO if tichu action in state.possible_actions apply tichu strategy
        # -> in both cases, don't return but make next state
        # Note: for both tichu and wish action, player_pos is not the same as action.player_pos, it is the pos of the next player
        #
        # TODO handle dragon away strategy
        # TODO also handle when finish action is the only action


        self._current_state = state
        reward = state.reward_vector() if state.is_terminal() else (0, 0, 0, 0)

        return state, reward, state.is_terminal(), {'state': state, 'next_player': state.player}

    def _reset(self):
        # Initialise initial state (includes distributing cards, grand tichus and trading cards)
        states = self._setup_initial_state()
        self._current_state = states[-1]

    def _render(self, mode='human', close=False):
        self._current_state.render()


