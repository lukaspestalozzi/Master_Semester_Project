import abc

from game.tichu.cards import CardValue
from .baseagent import BaseAgent, DefaultAgent
from ..exceptions import LogicError
# from game.tichu.tichu_actions import SwapCardAction INFO: Imported later


class DragonTrickPartialAgent(BaseAgent, metaclass=abc.ABCMeta):
    """
    PartialAgent overwriting only one particular method/functionality of BaseAgent

    Overwriting:

    :give_dragon_away: Gives the Dragon to the enemy player with the least handcards. Ties are broken arbitrarilly.
    """

    def give_dragon_away(self, trick, round_history):
        """
        :param trick:
        :param round_history:
        :return: The enemy player with the fewest handcards
        """
        return min((round_history.nbr_handcards(enemy), enemy) for enemy in [(self.position + 1) % 4, (self.position - 1) % 4])[1]


class WishSwappedCardPartialAgent(BaseAgent, metaclass=abc.ABCMeta):
    """
    PartialAgent overwriting only one particular method/functionality of BaseAgent

    Overwriting:

    :wish: wishes the card that was swapped to the player on the right.
    """

    def wish(self, round_history):
        from game.tichu.tichu_actions import SwapCardAction
        for e in round_history.events:
            if isinstance(e, SwapCardAction) and e.from_ == self.position and e.to == (self.position + 1) % 4:
                return e.card.card_value if e.card.card_value not in (CardValue.PHOENIX, CardValue.DRAGON, CardValue.DOG, CardValue.MAHJONG) else None
        raise LogicError("No Swap-cards to the right")


class RandomSwappingCardsPartialAgent(BaseAgent, metaclass=abc.ABCMeta):
    """
    PartialAgent overwriting only one particular method/functionality of BaseAgent

    Overwriting:

    :swap_cards: Chooses 3 random cards to swap to the 3 other players
    """

    def swap_cards(self):
        from game.tichu.tichu_actions import SwapCardAction
        sc = self.hand_cards.random_cards(3)
        scards = [
            SwapCardAction(player_from=self._position, card=sc[0], player_to=(self.position + 1) % 4),
            SwapCardAction(player_from=self._position, card=sc[1], player_to=(self.position + 2) % 4),
            SwapCardAction(player_from=self._position, card=sc[2], player_to=(self.position + 3) % 4)
        ]
        return scards


class NoTichuAnnouncePartialAgent(BaseAgent, metaclass=abc.ABCMeta):
    """
    PartialAgent overwriting only one particular method/functionality of BaseAgent

    Does never announce a tichu when asked.

    Overwriting:

    :announce_tichu: False
    :announce_grand_tichu: False
    """

    def announce_tichu(self, announced_tichu, announced_grand_tichu):
        return False

    def announce_grand_tichu(self, announced_grand_tichu):
        return False


class PlayNoBombPartialAgent(BaseAgent, metaclass=abc.ABCMeta):
    """
    PartialAgent overwriting only one particular method/functionality of BaseAgent

    Does never play a bomb when asked.

    Overwriting:

    :play_bomb: False
    """

    def play_bomb(self, round_history):
        return False


class SimplePartialAgent(PlayNoBombPartialAgent, NoTichuAnnouncePartialAgent,
                         DragonTrickPartialAgent, WishSwappedCardPartialAgent,
                         RandomSwappingCardsPartialAgent, DefaultAgent, metaclass=abc.ABCMeta):
    """
    PartialAgent overwriting only one particular method/functionality of BaseAgent

    Inherits from Following Partial Agents:

    - PlayNoBombPartialAgent
    - NoTichuAnnouncePartialAgent
    - DragonTrickPartialAgent
    - WishSwappedCardPartialAgent
    - RandomSwappingCardsPartialAgent
    - DefaultAgent
    """
    pass


