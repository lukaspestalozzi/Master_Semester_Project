import logging

import abc


from ..cards import Single
# from game.tichu.tichu_actions import SwapCardAction  INFO: Imported later


class BaseAgent(metaclass=abc.ABCMeta):

    def __init__(self):
        self._position = None
        self._hand_cards = None

    @property
    def position(self):
        return self._position

    @position.setter
    def position(self, pos):
        self._position = pos

    @property
    def hand_cards(self):
        return self._hand_cards

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
        :param round_history:
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

    def __init__(self):
        super().__init__()

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


