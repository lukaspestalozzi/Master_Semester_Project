
import abc

# Imported later: from .handcardsnapshot import HandCardSnapshot
from .trick import Trick
from .cards import Combination, Card, CardValue, Bomb
from .exceptions import IllegalActionException
# from .tichuplayers import TichuPlayer  Info: imported later
from game.utils import check_param, check_isinstance, check_true, indent


class GameEvent(object, metaclass=abc.ABCMeta):

    def pretty_string(self, indent_=0):
        return f"{indent(indent_, s=' ')}{str(self)}"

    def __str__(self):
        return f"{self.__class__.__name__}"


class RoundEndEvent(GameEvent):
    """ The event of finishing a round """
    __slots__ = ("_ranking", )

    def __init__(self, ranking):
        super().__init__()
        self._ranking = tuple(ranking)

    @property
    def ranking(self):
        return tuple(self._ranking)

    def __str__(self):
        return f"{self.__class__.__name__}(ranking:{self._ranking})"


class RoundStartEvent(GameEvent):
    """ The event of starting a round """
    __slots__ = ()
    # TODO store information here


class PlayerGameEvent(GameEvent, metaclass=abc.ABCMeta):
    """ abstract parent class for all game events possible in the game """

    __slots__ = ("_player_pos",)

    def __init__(self, player_pos):
        check_param(player_pos in range(4))
        self._player_pos = player_pos

    @property
    def player_pos(self):
        return self._player_pos

    def pretty_string(self, indent_=0):
        return f"{indent(indent_, s=' ')}"+self.__str__()

    def __repr__(self):
        return f"{self.__class__.__name__}({self._player_pos})"

    def __str__(self):
        return self.__repr__()

    def __eq__(self, other):
        return self.__class__ == other.__class__ and self.player_pos == other.player_pos

    def __hash__(self):
        return hash(self.__class__) + self._player_pos


class FinishEvent(PlayerGameEvent):
    """ A player finished action"""
    __slots__ = ()


class SimpleWinTrickEvent(PlayerGameEvent):
    __slots__ = ("_trick",)

    def __init__(self, player_pos, trick):
        """
        :param player_pos: the player winning the trick
        :param trick: The won trick
        """
        check_isinstance(trick, Trick)
        super().__init__(player_pos=player_pos)
        self._trick = trick

    @property
    def trick(self):
        return self._trick

    def pretty_string(self, indent_=0):
        return f"{indent(indent_, s=' ')}{self.__class__.__name__}(winner:{self._player_pos})"

    def __repr__(self):
        return f"{self.__class__.__name__}({self._player_pos}, trick:{self._trick})"

    def __eq__(self, other):
        return super().__eq__(other) and self.trick == other.trick

    def __hash__(self):
        return hash((self._player_pos, self._trick))


class WinTrickEvent(SimpleWinTrickEvent):
    """ Win a trick """

    __slots__ = ("_hand_cards",)

    def __init__(self, player_pos, trick, hand_cards):
        """
        :param player_pos:
        :param hand_cards: The HandCardSnapshot of the players when the trick finished
        """
        from .handcardsnapshot import HandCardSnapshot
        check_isinstance(hand_cards, HandCardSnapshot)
        super().__init__(player_pos=player_pos, trick=trick)
        self._hand_cards = hand_cards

    @property
    def hand_cards(self):
        return self._hand_cards

    def __repr__(self):
        return f"{self.__class__.__name__}({self._player_pos} handcards:{self._hand_cards}, trick:{self._trick})"

    def __eq__(self, other):
        return super().__eq__(other) and self.hand_cards == self.hand_cards and self.trick == other.trick

    def __hash__(self):
        return hash((self._player_pos, self.hand_cards, self._trick))


class PlayerAction(PlayerGameEvent, metaclass=abc.ABCMeta):
    """
    An action instigated by a player
    """
    __slots__ = ()

    def check(self, played_on=False, has_cards=None, is_combination=False, not_pass=False, is_bomb=False):
        """
        Checks the following properties when the argument is not False:
        :param played_on: Combination, whether the action can be played on the combination
        :param has_cards: Player, whether the player has the cards to play this action
        :param not_pass: bool, whether the action can be pass or not. (not_pass = True, -> action must not be pass action)
        :param is_bomb: bool, whether the action must be a bomb or not.
        :return: True if all checks succeed, False otherwise
        """
        from .tichuplayers import TichuPlayer

        if isinstance(played_on, Combination):
            check_true(self.can_be_played_on_combination(played_on), ex=IllegalActionException,
                       msg=f"{self} can't be played on {played_on}")

        if isinstance(has_cards, TichuPlayer):
            check_true(self.does_player_have_cards(has_cards), ex=IllegalActionException,
                       msg=f"{has_cards} does not have the cards for {self}")

        if not_pass:
            check_true(not isinstance(self, PassAction), ex=IllegalActionException,
                       msg=f"Action must not be Pass, but was {self}")

        if is_combination:
            check_true(isinstance(self, CombinationAction), ex=IllegalActionException,
                       msg=f"Action must be a CombinationAction, but was {self}")

        if is_bomb:
            check_true(self.is_bomb(), ex=IllegalActionException, msg=f"Action must be Bomb, but was {self}")
        return True

    def can_be_played_on_combination(self, comb):
        return True

    def does_player_have_cards(self, player):
        return player is not None

    def is_bomb(self):
        return False


class PassAction(PlayerAction):
    """ The pass action"""

    __slots__ = ()

    def can_be_played_on_combination(self, comb):
        return comb is not None

    def unique_id(self):
        """
        A string that has following property (A and B are instances of the same class): 

        - A.unique_id() == B.unique_id() implies A == B
        - A.unique_id() != B.unique_id() implies A != B

        :return: A unique string for this instance 
        """
        return str(self._player_pos)

    def __str__(self):
        return f"Pass({self._player_pos})"


class TichuAction(PlayerAction):
    """ Announce a tichu action """

    __slots__ = ()


class GrandTichuAction(PlayerAction):
    """ Announce a grand tichu action """
    __slots__ = ()


class GiveDragonAwayAction(PlayerAction):
    """ Give dragon trick away action"""

    __slots__ = ("_trick", "_to")

    def __init__(self, player_from, player_to, trick):
        check_param(player_to in range(4) and ((player_from+1)% 4 == player_to or (player_from-1)% 4 == player_to), param=(player_from, player_to))
        check_isinstance(trick, Trick)
        check_param(Card.DRAGON is trick.last_combination.card)
        super().__init__(player_pos=player_from)
        self._trick = trick
        self._to = player_to

    @property
    def trick(self):
        return self._trick

    @property
    def to(self):
        return self._to

    def can_be_played_on_combination(self, comb):
        return Card.DRAGON is comb.card

    def __eq__(self, other):
        return super().__eq__(other) and self.trick == other.trick and self.to == other.to

    def __hash__(self):
        return hash((self._player_pos, self._trick, self._to))

    def __str__(self):
        return f"{self.__class__.__name__}({self._player_pos} -> {self._to}: {str(self._trick)})"


class SwapCardAction(PlayerAction):
    """ Swap a card action """

    __slots__ = ("_card", "_to")

    def __init__(self, player_from, player_to, card):
        check_param(player_to in range(4) and player_from != player_to)
        check_isinstance(card, Card)
        super().__init__(player_pos=player_from)
        self._card = card
        self._to = player_to

    @property
    def card(self):
        return self._card

    @property
    def to(self):
        return self._to

    @property
    def from_(self):
        return self.player_pos

    def does_player_have_cards(self, player):
        return self._card in player.hand_cards

    def __eq__(self, other):
        return super().__eq__(other) and self.card == other.card and self.to == other.to

    def __hash__(self):
        return hash((self._player_pos, self._card, self._to))

    def __str__(self):
        return f"{self.__class__.__name__}({self._player_pos} -> {self._to}: {str(self._card)})"


class WishAction(PlayerAction):
    """ wish a CardValue action """

    __slots__ = ("_cardval",)

    def __init__(self, player_from, cardvalue):
        if cardvalue is not None:
            check_isinstance(cardvalue, CardValue)
            check_param(cardvalue not in {CardValue.PHOENIX, CardValue.DRAGON, CardValue.DOG, CardValue.MAHJONG}, msg="Wish can't be a special card, but was "+str(cardvalue))
        super().__init__(player_pos=player_from)
        self._cardval = cardvalue

    @property
    def card_value(self):
        return self._cardval

    def can_be_played_on_combination(self, comb):
        return Card.MAHJONG in comb

    def __eq__(self, other):
        return super().__eq__(other) and self.card_value == other.card_value

    def __hash__(self):
        return hash((self._player_pos, self._cardval))

    def __str__(self):
        return f"Wish({self._player_pos}:{str(self._cardval)})"


class CombinationAction(PlayerAction):
    """ Action of playing a combination"""

    __slots__ = ("_comb",)

    def __init__(self, player_pos, combination):
        check_isinstance(combination, Combination)
        super().__init__(player_pos=player_pos)
        self._comb = combination

    @property
    def combination(self):
        return self._comb

    def does_player_have_cards(self, player):
        return player.has_cards(self._comb)

    def can_be_played_on_combination(self, comb):
        return comb is None or comb < self._comb

    def is_bomb(self):
        return isinstance(self._comb, Bomb)

    def unique_id(self):
        """
        A string that has following property: 

        - A.unique_id() == B.unique_id() implies A == B
        - A.unique_id() != B.unique_id() implies A != B

        :return: A unique string for this instance 
        """
        return str(self._player_pos)+self._comb.unique_id()

    def __repr__(self):
        return f"{self.__class__.__name__}({self._player_pos}, {str(self._comb)})"

    def __str__(self):
        return f"({self.player_pos}:{self.combination})"

    def __eq__(self, other):
        return super().__eq__(other) and self.combination == other.combination

    def __hash__(self):
        return hash((self._player_pos, self._comb))

    def __contains__(self, item):
        return self._comb.__contains__(item)

    def __iter__(self):
        return self._comb.__iter__()


class CombinationTichuAction(CombinationAction, TichuAction):
    """ Action to say Tichu while playing a combination """
    def __str__(self):
        return f"{self.__class__.__name__}({self.player_pos}:{self.combination})"
