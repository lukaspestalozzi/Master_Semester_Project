import logging

import abc
from typing import Optional

import time

from game.tichu.cards import CardValue
from game.tichu.new_.tichu_states import TichuState
from game.tichu.tichu_actions import TichuAction, PlayerGameEvent, PassAction, CombinationAction, SimpleWinTrickEvent
from game.tichu.trick import Trick
from ..cards import Single
# from game.tichu.tichu_actions import SwapCardAction  INFO: Imported later


class BaseAgent(metaclass=abc.ABCMeta):

    def __init__(self):
        self._position = None
        self._hand_cards = None

    @property
    def name(self)->str:
        return self.__class__.__name__

    @property
    def position(self)->int:
        return self._position

    @position.setter
    def position(self, pos):
        self._position = pos

    @property
    def hand_cards(self):
        return self._hand_cards

    @abc.abstractmethod
    def info(self)->str:
        """
        Info string about this agent
        :return: 
        """

    @hand_cards.setter
    def hand_cards(self, hcs):
        self._hand_cards = hcs

    @abc.abstractmethod
    def start_game(self):
        """
        Should be called before a game starts and after the position of the agent is set
        :return:
        """

    @abc.abstractmethod
    def announce_grand_tichu(self, announced_grand_tichu):
        """

        :param announced_grand_tichu:
        :return:
        """
        # TODO describe

    @abc.abstractmethod
    def notify_about_announced_tichus(self, tichu, grand_tichu):
        """

        :param tichu:
        :param grand_tichu:
        :return:
        """
        # TODO describe

    @abc.abstractmethod
    def announce_tichu(self, announced_tichu, announced_grand_tichu):
        """

        :param announced_tichu:
        :param announced_grand_tichu:
        :return:
        """
        # TODO describe

    @abc.abstractmethod
    def swap_cards(self):
        """

        :return:
        """
        # TODO describe

    @abc.abstractmethod
    def swap_cards_received(self, swapped_cards_actions):
        """

        :param swapped_cards_actions:
        :return:
        """

    @abc.abstractmethod
    def play_first(self, round_history, wish):
        """

        :param round_history:
        :param wish:
        :return:
        """
        # TODO describe

    @abc.abstractmethod
    def play_bomb(self, round_history):
        """

        :param round_history:
        :return:
        """

    @abc.abstractmethod
    def play_combination(self, wish, round_history):
        """
        
        :param wish:
        :param round_history:
        :return:
        """
        # TODO describe

    @abc.abstractmethod
    def wish(self, round_history):
        """

        :param round_history:
        :return:
        """

    @abc.abstractmethod
    def give_dragon_away(self, trick, round_history):
        """

        :param trick:
        :param round_history:
        :return:
        """


class DefaultAgent(BaseAgent):
    """
    Default Agent implements the Methods of the BaseAgent in the most trivial way.

    - give_dragon_away: To player on the right
    - wish: None
    - play_first: Plays any first Single card Combination, or plays any card that satisfies the wish
    - play_combination: Pass if possible, or plays any card that satisfies the wish
    - play_bomb: False
    - swap_cards: swaps 3 random cards
    - announce_tichu: False
    - announce_grand_tichu: False

    all other methods just 'pass'
    """

    def info(self):
        return "{s.__class__.__name__}({s.name})".format(s=self)

    def swap_cards_received(self, swapped_cards_actions):
        pass

    def start_game(self):
        pass

    def give_dragon_away(self, trick, round_history):
        pl_pos = (self.position + 1) % 4
        return pl_pos

    def wish(self, round_history):
        return None

    def play_combination(self, wish, round_history):
        if wish and wish in (c.card_value for c in self.hand_cards):
            try:
                comb = next((c for c in self.hand_cards.all_combinations(round_history.last_combination) if c.contains_cardval(wish)))
                return comb
            except StopIteration:
                pass
        return None

    def play_bomb(self, round_history):
        return False

    def play_first(self, round_history, wish):
        card = next(iter(self.hand_cards))
        if wish:
            try:
                card = next((c for c in self.hand_cards if c.card_value is wish))
            except StopIteration:
                pass

        comb = Single(card)
        return comb

    def swap_cards(self):
        from game.tichu.tichu_actions import SwapCardAction
        sc = self.hand_cards.random_cards(3)
        scards = [
            SwapCardAction(player_from=self._position, card=sc[0], player_to=(self.position + 1) % 4),
            SwapCardAction(player_from=self._position, card=sc[1], player_to=(self.position + 2) % 4),
            SwapCardAction(player_from=self._position, card=sc[2], player_to=(self.position + 3) % 4)
        ]
        return scards

    def notify_about_announced_tichus(self, tichu, grand_tichu):
        pass

    def announce_tichu(self, announced_tichu, announced_grand_tichu):
        return False

    def announce_grand_tichu(self, announced_grand_tichu):
        return False


class SearchAgent(BaseAgent):
    """
    Defines the methods 'play_combination' and 'play_first'
    
    Those methods create the start state and initialize the search
    
    method to overwrite: 
    
    :search: given a state returns the action to play
    """

    def play_combination(self, wish, round_history):
        state = self._create_tichu_state(round_history=round_history,
                                         wish=wish,
                                         trick_on_table=round_history.tricks[-1])
        action = self._start_search(state)
        return action

    def play_first(self, round_history, wish):
        state = self._create_tichu_state(round_history=round_history,
                                         wish=wish,
                                         trick_on_table=Trick())
        action = self._start_search(state)
        return action

    def _create_tichu_state(self, round_history, wish: Optional[CardValue], trick_on_table: Trick)->TichuState:
        return TichuState(player_id=self.position,
                          hand_cards=round_history.last_handcards,
                          won_tricks=round_history.won_tricks,
                          trick_on_table=trick_on_table,
                          wish=wish,
                          ranking=tuple(round_history.ranking),
                          announced_tichu=frozenset(round_history.announced_tichus),
                          announced_grand_tichu=frozenset(round_history.announced_grand_tichus),
                          history=tuple([a for a in round_history.events if isinstance(a, (SimpleWinTrickEvent, CombinationAction, PassAction))]))

    def _start_search(self, start_state: TichuState)->TichuAction:
        logging.debug(f"agent {self.name} (pos {self._position}) starts search.")
        start_t = time.time()
        if len(start_state.possible_actions()) == 1:
            logging.debug(f"agent {self.name} (pos {self._position}) there is only one action to play.")
            action = next(iter(start_state.possible_actions()))
        else:
            action = self.search(start_state)

        logging.debug(f"agent {self.name} (pos {self._position}) found action: {action} (time: {time.time()-start_t})")
        return action

    @abc.abstractmethod
    def search(self, state: TichuState)->TichuAction:
        """
        
        :param state: The state from which the search starts
        :return: The Action to play
        """
        pass

