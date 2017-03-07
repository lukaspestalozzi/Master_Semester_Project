import abc
import uuid
from enum import Enum
import logging

from game.cards import Combination, CombinationType, Cards
from game.exceptions import IllegalActionError



class TichuPlayer(metaclass=abc.ABCMeta):

    def __init__(self, name, agent):
        """
        :param name: string, the name of the player, it is preferable that this is a unique name.
        :param agent: Agent, the agent deciding the players moves.
        """
        # TODO verify parameters
        self._name = name
        self._hash = int(uuid.uuid4())
        self._agent = agent
        self._position = None
        self._hand_cards = Cards(cards=list())
        self._tricks = list()  # list of won tricks
        self._team_mate_id = None  # id of the teammate

    @property
    def name(self):
        return self._name

    @property
    def agent(self):
        return self._agent

    @property
    def position(self):
        return self._position

    @position.setter
    def position(self, value):
        if value not in range(4):
            raise ValueError("position must be one of [0, 1, 2, 3]. But was {}".format(value))
        else:
            self._position = value

    @property
    def team_mate(self):
        return self._team_mate_id

    @team_mate.setter
    def team_mate(self, player_id):
        assert 0 <= player_id < 4
        self._team_mate_id = player_id

    @property
    def has_finished(self):
        return len(self.hand_cards) == 0

    @property
    def hand_cards(self):
        return self._hand_cards

    @property
    def tricks(self):
        return self._tricks

    def __hash__(self):
        return self._hash

    def __eq__(self, other):
        return isinstance(other, self.__class__) and self.__hash__() == hash(other) and self.name == other.name

    def __str__(self):
        return "{}(\n\tname: {}, pos: {}, teammate:{},\n\thandcards:{}, \n\ttricks:{}, \n\tagent:{}, \n\thash:{}\n)".format(str(self.__class__), str(self.name), str(self.position), str(self.team_mate), str(self.hand_cards), str(self.tricks), str(self._agent), str(self._hash))

    def __repr__(self):
        return "{}(\n\tname: {}, pos: {}, \n\thandcards:{}, \n\ttricks:{}\n)".format(str(self.__class__), str(self.name), str(self.position), str(self.hand_cards), str(self.tricks))

    def remove_hand_cards(self):
        """
        Removes the hand cards of this player.
        :return: the (now old) hand cards of the player.
        """
        hcards = self._hand_cards
        self._hand_cards = Cards(cards=list())
        return hcards

    def can_announce_tichu(self):
        return len(self.hand_cards) == 14

    def remove_tricks(self):
        """
        Removes the tricks from this player
        :return: List; the removed tricks
        """
        tricks = self._tricks
        self._tricks = list()
        return tricks

    def add_trick(self, trick):
        """
        Appends the given trick to the tricks made by the player
        :param trick: The trick to be added
        :return: Nothing
        """
        self._tricks.append(trick)
        logging.info("{} added trick {}".format(self.name, trick))

    def count_points_in_tricks(self):
        """
        :return: The number of points the player gained with his tricks
        """
        return sum(t.points() for t in self._tricks)

    def receive_first_8_cards(self, cards):
        """
        Called by the game manager to hand over the first 8 cards.
        :param cards: Cards; The 8 cards
        """
        assert len(cards) == 8
        self.hand_cards.add_all(cards)
        assert len(self.hand_cards) == 8
        logging.info("{} added 8 cards: {}".format(self.name, cards))

    def receive_last_6_cards(self, cards):
        """
        Called by the game manager to hand over the last 6 cards.
        :param cards: Cards; The 6 cards
        """
        assert len(cards) == 6
        self.hand_cards.add_all(cards)
        assert len(self.hand_cards) == 14
        logging.info("{} added 6 cards: {}".format(self.name, cards))

    def receive_swapped_cards(self, swapped_cards):
        """
        :param swapped_cards: A set of SwapCard instances.
        :return Nothing
        """
        from game.round import SwapCard  # TODO
        assert len(swapped_cards) == 3
        assert all([isinstance(sc, SwapCard) for sc in swapped_cards])
        # print("swapped cards",self.position, "->", [c.card for c in swapped_cards])
        self.hand_cards.add_all([c.card for c in swapped_cards])  # TODO agent, store info about swapped card
        logging.info("{} received swap cards: {}".format(self.name, swapped_cards))

    @abc.abstractmethod
    def announce_grand_tichu_or_not(self, announced_tichu, announced_grand_tichu):
        """
        :param announced_tichu: a list of integers (in range(0, 4)), denoting playerIDs that already have announced a Tichu.
        :param announced_grand_tichu: a list of integers (in range(0, 4)), denoting playerIDs that already have announced a grand Tichu.
        :return True if this player announces a grand Tichu, False otherwise.
        """

    @abc.abstractmethod
    def announce_tichu_or_not(self, announced_tichu, announced_grand_tichu):
        """
        :param announced_tichu: a list of integers (in range(0, 4)), denoting playerIDs that already have announced a Tichu.
        :param announced_grand_tichu: a list of integers (in range(0, 4)), denoting playerIDs that already have announced a grand Tichu.
        :return True if this player announces a normal Tichu, False otherwise.
        """

    @abc.abstractmethod
    def players_announced_grand_tichu(self, announced):
        """
        Called by the the game manager to notify the player about announced grand Tichus.
        :param announced: a list of integers (in range(0, 4)), denoting playerIDs that have announced a grand Tichu.
        :return None
        """

    @abc.abstractmethod
    def players_announced_tichu(self, announced):
        """
        Called by the the game manager to notify the player about announced normal Tichus.
        :param announced: a list of integers (in range(0, 4)), denoting playerIDs that have announced a normal Tichu.
        :return None
        """

    @abc.abstractmethod
    def play_first(self):
        """
        Called by the the game manager to request a move.
        The combination must be a valid play according to the Tichu rules, in particular, PlayerAction must not be Pass.
        :return: the combination the player wants to play as PlayerAction.
        """

    @abc.abstractmethod
    def play_combination(self, on_trick, wish):
        """
        Called by the the game manager to request a move.
        :param on_trick:
        :param wish: The CardValue beeing wished, None if no wish is present
        :return: pass, or the combination the player wants to play as PlayerAction.
        """
        """
        Called by the the game manager to request a move.
        on_trick: the highest trick on the table
        Returns
        """

    @abc.abstractmethod
    def play_bomb_or_not(self, on_trick):
        """
        Called by the the game manager to allow the player to play a bomb.
        :param on_trick: Trick; The tricks currently on the table
        :return: the bomb (as PlayerAction) if the player wants to play a bomb. False or None otherwise

        """

    @abc.abstractmethod
    def swap_cards(self):
        """
        Called by the the game manager to ask for the 3 cards to be swapped
        :return a SwapCards instance.
        """

    @abc.abstractclassmethod
    def give_dragon_away(self, trick):
        """
        :param trick: Trick; the trick to give away
        :return: id of the player to give the trick to.
        """

    @abc.abstractclassmethod
    def wish(self):
        """
        :return: The CardValue to be wished
        """


class PlayerActionType(Enum):
    PASS = 0
    COMBINATION = 1
    COMBINATION_TICHU = 2

    def __str__(self):
        return self.name

    def __repr__(self):
        return self.__str__()


class PlayerAction(object):
    """
    Encodes the players action.
    The Action may be:
    - The pass action
    - A combination of cards
    - May include a Tichu announcement

    It is guaranteed that:
    - It is either a Pass-action or a Combination
    - If it is a Combination, it is a valid Combination (according to the Tichu rules)
    -
    """

    def __init__(self, player, combination=None, pass_=True, tichu=False):
        """
        Note that PlayerAction() denotes the Pass-action by default.
        :param player: The player playing the action.
        :param combination: Combination (default None); The combination the player wants to play, or False when player wants to pass.
        :param pass_: boolean (default True); True when the player wants to pass (Pass-action). Ignored when combination is not False
        :param tichu: boolean (default False); flag if the player wants to announce a Tichu with this action. Ignored when pass_=True and combination=False
        """
        # check params
        if not isinstance(player, TichuPlayer):
            raise ValueError("Player must be instance of TichuPlayer, but was {}".format(player.__class__))
        elif not combination and not pass_:
            raise ValueError("Either combination or pass must be truthy.")
        elif not pass_ and not isinstance(combination, Combination):
            raise ValueError("combination must be an instance of Combination, but was {}".format(combination.__class__))

        self._player = player
        self._comb = combination if combination else None
        self._tichu = bool(tichu)

        # determine type
        self._type = PlayerActionType.PASS
        if combination:
            if tichu:
                self._type = PlayerActionType.COMBINATION_TICHU
            else:
                self._type = PlayerActionType.COMBINATION

    @property
    def type(self):
        return self._type

    @property
    def player(self):
        return self._player

    @property
    def combination(self):
        """
        :return: The combination of the Action. May be None
        """
        return self._comb

    def __str__(self):
        return ("Action[{}](player: {})".format(self._type, self._player.name)
                if self.is_pass()
                else "Action[{}](player: {}, tichu:{}, comb:{})".format(self._type, self._player.name, self._tichu, self._comb))

    def __repr__(self):
        return self.__str__()

    def is_combination(self):
        return self._type is PlayerActionType.COMBINATION or self._type is PlayerActionType.COMBINATION_TICHU

    def is_tichu(self):
        return self._type is PlayerActionType.COMBINATION_TICHU

    def is_pass(self):
        return self._type is PlayerActionType.PASS

    def is_bomb(self):
        return not self.is_pass() and self.combination.type is CombinationType.SQUAREBOMB or self.combination.type is CombinationType.STRAIGHTBOMB

    def can_be_played_on(self, comb, raise_exception=False):
        """
        Checks whether this action can be played on the given combination.
        That means in particular:
        - if the Action is a Pass-action, check succeeds
        - else, the Actions combination must be playable on the given comb
        :param comb: the Combination
        :param raise_exception: boolean (default False); if True, instead of returning False, raises an IllegalActionError.
        :return: True iff this check succeeds, False otherwise
        """
        if comb is None:
            return True
        try:
            res = self._type is PlayerActionType.PASS or comb < self._comb  # Do not change < (or a single phoenix does not work anymore.)
        except ValueError as ve:
            res = False
        except TypeError as te:
            res = False

        if not res and raise_exception:
            raise IllegalActionError("{} can not be played on {}".format(self._comb, comb))
        return res

    def does_player_have_cards(self, player=None, raise_exception=False):
        """
        :param player: TichuPlayer (default None); the player whose hand_cards are to be tested. If is None, then the player playing the Action is taken.
        :param raise_exception: boolean (default False); if True, instead of returning False, raises an IllegalActionError.
        :return: True iff the Actions combination is a subset of the players hand_cards. False otherwise.
        """
        if player is None:
            player = self.player
        res = self._type is PlayerActionType.PASS or self._comb.issubset(player.hand_cards)
        if not res and raise_exception:
            raise IllegalActionError("Player {} does not have the right cards for {}".format(player, self._comb))
        return res



