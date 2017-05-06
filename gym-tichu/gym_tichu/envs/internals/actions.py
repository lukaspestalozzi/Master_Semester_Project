
import abc
from collections import namedtuple, Generator

from .cards import Combination, DOG, Trick, CardRank

CardTrade = namedtuple('CardTrade', ['from_', 'to', 'card'])


class PlayerAction(object, metaclass=abc.ABCMeta):

    def __init__(self, player_pos: int):
        assert player_pos in range(4)
        self._player_pos = player_pos

    @property
    def player_pos(self):
        return self._player_pos


class PlayCombination(PlayerAction):

    def __init__(self, player_pos: int, combination: Combination):
        super().__init__(player_pos=player_pos)
        self._combination = combination

    @property
    def combination(self):
        return self._combination


class PlayFirst(PlayCombination):
    pass


class PlayDog(PlayFirst):

    def __init__(self, player_pos: int):
        super().__init__(player_pos=player_pos, combination=DOG)


class PlayBomb(PlayCombination):

    def __init__(self, player_pos: int, combination: Combination):
        assert combination.is_bomb()
        super().__init__(player_pos=player_pos, combination=combination)


class PassAction(PlayerAction):
    pass


class TichuAction(PlayerAction):

    def __init__(self, player_pos: int, announce_tichu: bool):
        super().__init__(player_pos=player_pos)
        self._announce = announce_tichu

    @property
    def announce(self):
        return self._announce


class WinTrickAction(PlayerAction):
    def __init__(self, player_pos: int, trick: Trick):
        super().__init__(player_pos=player_pos)
        self._trick = trick

    @property
    def trick(self):
        return self._trick


class GiveDragonAwayAction(WinTrickAction):

    def __init__(self, player_from: int, player_to: int, trick: Trick):
        assert player_to in range(4)
        super().__init__(player_pos=player_from, trick=trick)
        self._to = player_to

    @property
    def to(self):
        return self._to


class WishAction(PlayerAction):

    __slots__ = ("_cardval",)

    def __init__(self, player_pos, wish):
        super().__init__(player_pos=player_pos)
        self._wish = wish

    @property
    def wish(self):
        return self._wish


# ###### PREDEFINED ACTIONS ######
# Pass
pass_actions = tuple((PassAction(k) for k in range(4)))

# Tichu
tichu_actions = tuple((TichuAction(k, True) for k in range(4)))
no_tichu_actions = tuple((TichuAction(k, False) for k in range(4)))

# Play Dog
play_dog_actions = tuple((PlayDog(k) for k in range(4)))


def all_wish_actions_gen(player_pos: int)->Generator:
    """
    :param player_pos: 
    :return: Generator yielding all wish actions with the given player id
    """
    yield WishAction(player_pos=player_pos, wish=None)
    for rank in (CardRank.TWO, CardRank.THREE, CardRank.FOUR, CardRank.FIVE, CardRank.SIX,
                 CardRank.SEVEN, CardRank.EIGHT, CardRank.NINE, CardRank.TEN, CardRank.J,
                 CardRank.Q, CardRank.K, CardRank.A):
        yield WishAction(player_pos=player_pos, wish=rank)
