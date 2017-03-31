import abc


class BaseAgent(metaclass=abc.ABCMeta):

    def __init__(self):
        self._position = None

    @property
    def position(self):
        return self._position

    @position.setter
    def position(self, pos):
        self._position = pos

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
    def announce_tichu(self, announced_tichu, announced_grand_tichu, round_history):
        """

        :param announced_tichu:
        :param announced_grand_tichu:
        :param round_history:
        :return:
        """
        # TODO describe

    @abc.abstractmethod
    def swap_cards(self, hand_cards):
        """

        :return:
        """
        # TODO describe

    @abc.abstractmethod
    def play_first(self, hand_cards, round_history, wish):
        """

        :param round_history:
        :param wish:
        :return:
        """
        # TODO describe

    @abc.abstractmethod
    def play_bomb(self, hand_cards, round_history):
        """

        :param round_history:
        :return:
        """

    @abc.abstractmethod
    def play_combination(self, wish, hand_cards, round_history):
        """

        :param round_history:
        :return:
        """
        # TODO describe

    @abc.abstractmethod
    def wish(self, hand_cards, round_history):
        """

        :param hand_cards:
        :param round_history:
        :return:
        """

    @abc.abstractmethod
    def give_dragon_away(self, hand_cards, trick, round_history):
        """

        :param hand_cards:
        :return:
        """


