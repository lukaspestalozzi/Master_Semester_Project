import abc
import logging
import uuid

from .agents import BaseAgent
from .cards import Cards, ImmutableCards
from .exceptions import IllegalActionException
from .tichu_actions import SwapCardAction, PassAction, CombinationAction, GiveDragonAwayAction, WishAction
from game.utils import check_true, check_isinstance, ignored


class TichuPlayer(metaclass=abc.ABCMeta):
    """
    'Save' Tichu Player. Checks whether it's agent moves are legal.
    """

    def __init__(self, name, agent, perfect_information_mode=False):
        """
        :param name: string, the name of the players, it is preferable that this is a unique name.
        :param agent: Agent, the agent deciding the players moves.
        """

        if not isinstance(agent, BaseAgent):
            raise ValueError("agent must inherit from BaseAgent")
        self._name = str(name)
        self._hash = int(uuid.uuid4())
        self._agent = agent
        self._position = None
        self._hand_cards = Cards(cards=list())
        self._tricks = list()  # list of won tricks
        self._teammate_pos = None  # position of the teammate
        self._pi_mode = perfect_information_mode
        self._copy_savely = not perfect_information_mode

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
        return self._teammate_pos

    @team_mate.setter
    def team_mate(self, player_pos):
        assert player_pos in range(4) and player_pos != self.position
        self._teammate_pos = player_pos

    @property
    def has_finished(self):
        return len(self._hand_cards) == 0

    @property
    def hand_cards(self):
        return ImmutableCards(self._hand_cards)

    @property
    def tricks(self):
        return list(self._tricks)

    def has_cards(self, cards):
        return all(c in self._hand_cards for c in cards)

    def remove_hand_cards(self):
        """
        Removes the hand cards of this players.
        :return: the (now old) hand cards of the players.
        """
        hcards = self._hand_cards
        self._hand_cards = Cards(cards=list())
        self._update_agent_handcards()
        return hcards

    def can_announce_tichu(self):
        return len(self._hand_cards) == 14

    def remove_tricks(self):
        """
        Removes the tricks from this players
        :return: List; the removed tricks
        """
        tricks = self._tricks
        self._tricks = list()
        return tricks

    def add_trick(self, trick):
        """
        Appends the given trick to the tricks made by the players
        :param trick: The trick to be added
        :return: Nothing
        """
        self._tricks.append(trick)

    def count_points_in_tricks(self):
        """
        :return: The number of points the players gained with his tricks
        """
        pts = sum([t.points for t in self._tricks])
        logging.debug(f"counting points of tricks, player:{self.position}, tricks:{self._tricks} -> {pts}")
        return pts

    def new_game(self, new_position, teammate):
        assert new_position in range(4) and teammate in range(4) and (new_position + 2) % 4 == teammate
        self._position = new_position
        self._teammate_pos = teammate
        self.remove_tricks()
        self.remove_hand_cards()
        self._agent.position = new_position
        self._agent.start_game()

    def new_round(self):
        self.remove_tricks()
        self.remove_hand_cards()

    def receive_first_8_cards(self, cards):
        """
        Called by the tichu manager to hand over the first 8 cards.
        :param cards: Cards; The 8 cards
        """
        assert len(cards) == 8
        assert len(self._hand_cards) == 0
        self._hand_cards.add_all(cards)
        assert len(self._hand_cards) == 8
        self._update_agent_handcards()

    def receive_last_6_cards(self, cards):
        """
        Called by the tichu manager to hand over the last 6 cards.
        :param cards: Cards; The 6 cards
        """
        assert len(cards) == 6
        self._hand_cards.add_all(cards)
        assert len(self._hand_cards) == 14
        self._update_agent_handcards()

    # ### Agent Methods ###

    def receive_swapped_cards(self, swapped_cards_actions):
        """
        :param swapped_cards_actions: A set of SwapCardAction instances.
        :return Nothing
        """
        assert len(swapped_cards_actions) == 3
        assert all([isinstance(sc, SwapCardAction) for sc in swapped_cards_actions])
        self._hand_cards.add_all([c.card for c in swapped_cards_actions])
        self._update_agent_handcards()
        self._agent.swap_cards_received(swapped_cards_actions=swapped_cards_actions)

    def swap_cards(self):
        """
        Called by the the tichu manager to ask for the 3 cards to be swapped
        :return a set (of length 3) of SwapCardAction instance.
        """
        self._update_agent_handcards()
        swap_cards = self._agent.swap_cards()
        check_true(len(swap_cards) == 3
                   and len({sw.player_pos for sw in swap_cards}) == 1
                   and next(iter(swap_cards)).player_pos == self._position
                   and len({sw.to for sw in swap_cards}) == 3,
                   ex=IllegalActionException, msg="swap card actions were not correct")
        for sw in swap_cards:
            self._hand_cards.remove(sw.card)
        self._update_agent_handcards()
        return swap_cards

    def announce_grand_tichu_or_not(self, announced_grand_tichu):
        """
        :param announced_grand_tichu: a collection of integers (in range(0, 4)), denoting playerIDs that already have announced a grand Tichu.
        :return True if this players announces a grand Tichu, False otherwise.
        """
        gt = self._agent.announce_grand_tichu(tuple(announced_grand_tichu))
        return bool(gt)

    def announce_tichu_or_not(self, announced_tichu, announced_grand_tichu, game_history):
        """
        :param game_history:
        :param announced_tichu: a collection of integers (in range(0, 4)), denoting playerIDs that already have announced a Tichu.
        :param announced_grand_tichu: a collection of integers (in range(0, 4)), denoting playerIDs that already have announced a grand Tichu.
        :return True if this player announces a normal Tichu, False otherwise.
        """
        nt = self._agent.announce_tichu(announced_tichu=tuple(announced_tichu), announced_grand_tichu=tuple(announced_grand_tichu))
        return bool(nt)

    def players_announced_tichus(self, tichu=tuple(), grand_tichu=tuple()):
        """
        Called by the the tichu manager to notify the players about announced grand Tichus.
        :param tichu: tichus already announced
        :param grand_tichu: grand tichus already announced
        :return None
        """
        self.agent.notify_about_announced_tichus(tichu=tuple(tichu), grand_tichu=tuple(grand_tichu))

    def play_first(self, game_history, wish):
        """
        Called by the the tichu manager to request a move.
        The combination must be a valid play according to the Tichu rules, in particular, PlayerAction must not be Pass.
        :return: the combination the players wants to play as a CombinationAction.
        """
        assert len(self._hand_cards) > 0
        action = self._agent.play_first(round_history=game_history.current_round.build(save=self._copy_savely),
                                        wish=wish)

        action.check(has_cards=self, is_combination=True, not_pass=True)
        TichuPlayer._check_wish(game_history.current_round.last_combination, action, self.hand_cards, wish)
        self._hand_cards.remove_all(action.combination.cards)
        self._update_agent_handcards()
        return action

    def play_combination(self, game_history, wish):
        """
        Called by the the tichu manager to request a move.
        :param game_history: The history of the tichu game so far.
        :param wish: The CardValue beeing wished, None if no wish is present
        :return: pass, or the combination the players wants to play as CombinationAction or PassAction.
        """
        assert len(self._hand_cards) > 0
        action = self._agent.play_combination(wish=wish, round_history=game_history.current_round.build(save=self._copy_savely))

        check_isinstance(action, (CombinationAction, PassAction))
        check_true(action.player_pos == self._position)
        with ignored(AttributeError, ValueError):
            action.combination.set_phoenix_height(game_history.current_round.last_combination.height + 0.5)

        action.check(played_on=game_history.current_round.last_combination, has_cards=self)
        TichuPlayer._check_wish(game_history.current_round.last_combination, action, self.hand_cards, wish)

        if isinstance(action, CombinationAction):
            self._hand_cards.remove_all(action.combination.cards)
        self._update_agent_handcards()
        return action

    @staticmethod
    def _check_wish(played_on, action, hand_cards, wish):
        """
        Checks whether the action does not fulfill the wish, but one could have fulfilled it with the handcards and played on Combination
        :param played_on: Combination to play on
        :param action: CombinationAction
        :param hand_cards: The available cards
        :param wish: CardValue (may be None)
        :return: True if ok
        :raise IllegalActionException: If wish could have been fulfilled, but was not.
        """
        if wish:  # there is a wish
            if isinstance(action, PassAction) or not action.combination.fulfills_wish(wish):  # player did not fulfill wish
                if wish in (c.card_value for c in hand_cards):  # player has wish in handcards
                    # look if the player could have fulfilled the wish
                    possible_combs = list(hand_cards.all_combinations(played_on, contains_value=wish))
                    if len(possible_combs) > 0:
                        raise IllegalActionException(
                                f"Could have played the wish, but did not. wish: {wish}, played {action}, handcards: {hand_cards}, possible combs:{possible_combs}, comb on table: {played_on}")
        return True

    def play_bomb_or_not(self, game_history):
        """
        Called by the the tichu manager to allow the players to play a bomb.
        :param game_history:The history of the tichu game so far.
        :return: the bomb (as CombinationAction) if the players wants to play a bomb. False or None otherwise
        """
        bomb_comb = self._agent.play_bomb(round_history=game_history.current_round.build(save=self._copy_savely))
        bomb_action = False
        if bomb_comb:
            bomb_action = CombinationAction(player_pos=self.position, combination=bomb_comb)
            bomb_action.check(played_on=game_history.current_round.last_combination, has_cards=self, is_bomb=True)
            self._hand_cards.remove_all(bomb_action.combination)
        self._update_agent_handcards()
        return bomb_action

    def give_dragon_away(self, game_history, trick):
        """
        :param game_history: The history of the tichu so far.
        :param trick: The dragon Trick
        :return: id of the players to give the trick to.
        """
        pos = self._agent.give_dragon_away(trick=trick, round_history=game_history.current_round.build(save=self._copy_savely))
        try:
            dragon_action = GiveDragonAwayAction(player_from=self._position, player_to=pos, trick=trick)
            return dragon_action
        except (TypeError, ValueError) as err:
            raise IllegalActionException("Giving the Dragon away failed.") from err

    def wish(self, game_history):
        """
        :param game_history: The history of the tichu game so far.
        :return: The WishAction to be wished
        """
        w = self._agent.wish(game_history.current_round.build(save=self._copy_savely))
        wish_action = WishAction(player_from=self._position, cardvalue=w)
        return wish_action

    def _update_agent_handcards(self):
        """
        Updates the agents handcards with this players handcards
        """
        self._agent.hand_cards = self.hand_cards

    def __hash__(self):
        return self._hash

    def __eq__(self, other):
        return isinstance(other, self.__class__) and self.__hash__() == hash(other) and self.name == other.name

    def __str__(self):
        return f"{self.__class__.__name__}(\n\tname: {self.name}, pos: {self._position}, teammate:{self.team_mate},\n\thandcards:{self._hand_cards}, \n\ttricks:{self._tricks}, \n\tagent:{self._agent.__class__.__name__}, \n\thash:{self._hash}\n)"

    def __repr__(self):
        return "{}(\n\tname: {}, pos: {}, \n\thandcards:{}, \n\ttricks:{}\n)".format(str(self.__class__), str(self.name), str(self.position), str(self._hand_cards), str(self.tricks))

