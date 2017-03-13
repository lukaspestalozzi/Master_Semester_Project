import abc
import logging
import uuid
from enum import Enum

import itertools

from tichu.agents.abstractagent import BaseAgent
from tichu.cards.card import CardValue
from tichu.cards.cards import Cards, Combination, Bomb, ImmutableCards
from tichu.exceptions import IllegalActionException
from tichu.utils import assert_


class TichuPlayer(metaclass=abc.ABCMeta):
    """
    'Save' Tichu Player. Checks whether it's agent moves are legal.
    """

    def __init__(self, name, agent):
        """
        :param name: string, the name of the players, it is preferable that this is a unique name.
        :param agent: Agent, the agent deciding the players moves.
        """
        # TODO check arguments
        if not isinstance(agent, BaseAgent):
            raise ValueError("agent must inherit from BaseAgent")
        self._name = str(name)
        self._hash = int(uuid.uuid4())
        self._agent = agent
        self._position = None
        self._hand_cards = Cards(cards=list())
        self._tricks = list()  # list of won tricks
        self._team_mate_pos = None  # id of the teammate

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
        return self._team_mate_pos

    @team_mate.setter
    def team_mate(self, player_pos):
        assert player_pos in range(4) and player_pos != self.position
        self._team_mate_pos = player_pos

    @property
    def has_finished(self):
        return len(self._hand_cards) == 0

    @property
    def hand_cards(self):
        return ImmutableCards(self._hand_cards)

    @property
    def tricks(self):
        return list(self._tricks)

    def remove_hand_cards(self):
        """
        Removes the hand cards of this players.
        :return: the (now old) hand cards of the players.
        """
        hcards = self._hand_cards
        self._hand_cards = Cards(cards=list())
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
        logging.debug("counting points of tricks: {} -> {}".format(self._tricks, pts))
        return pts

    def new_game(self, new_position, teammate):
        assert new_position in range(4) and teammate in range(4) and (new_position + 2) % 4 == teammate
        self._position = new_position
        self._team_mate_pos = teammate
        self.remove_tricks()
        self.remove_hand_cards()
        self._agent.position = new_position

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

    def receive_last_6_cards(self, cards):
        """
        Called by the tichu manager to hand over the last 6 cards.
        :param cards: Cards; The 6 cards
        """
        assert len(cards) == 6
        self._hand_cards.add_all(cards)
        assert len(self._hand_cards) == 14

    def receive_swapped_cards(self, swapped_cards):
        """
        :param swapped_cards: A set of SwapCard instances.
        :return Nothing
        """
        from tichu.game.gameutils import SwapCard
        assert len(swapped_cards) == 3
        assert all([isinstance(sc, SwapCard) for sc in swapped_cards])
        self._hand_cards.add_all([c.card for c in swapped_cards])  # TODO agent, store info about swapped card

    # ### Agent Methods ###
    def swap_cards(self):
        """
        Called by the the tichu manager to ask for the 3 cards to be swapped
        :return a SwapCards instance.
        """
        from tichu.game.gameutils import SwapCards
        swap_cards = self._agent.swap_cards(self.hand_cards)
        sc = SwapCards(self, *swap_cards)
        self._hand_cards.remove_all(sc.cards())
        return sc

    def announce_grand_tichu_or_not(self, announced_grand_tichu):
        """
        :param announced_grand_tichu: a list of integers (in range(0, 4)), denoting playerIDs that already have announced a grand Tichu.
        :return True if this players announces a grand Tichu, False otherwise.
        """
        gt = self._agent.announce_grand_tichu(announced_grand_tichu)
        return bool(gt)

    def announce_tichu_or_not(self, announced_tichu, announced_grand_tichu, game_history):
        """
        :param announced_tichu: a list of integers (in range(0, 4)), denoting playerIDs that already have announced a Tichu.
        :param announced_grand_tichu: a list of integers (in range(0, 4)), denoting playerIDs that already have announced a grand Tichu.
        :return True if this players announces a normal Tichu, False otherwise.
        """
        nt = self._agent.announce_tichu(announced_tichu, announced_grand_tichu, round_history=game_history.current_round.copy(save=self.position))
        return bool(nt)

    def players_announced_tichus(self, tichu=list(), grand_tichu=list()):
        """
        Called by the the tichu manager to notify the players about announced grand Tichus.
        :param tichu: tichus already announced
        :param grand_tichu: grand tichus already announced
        :return None
        """
        # TODO maybe, rename the function.
        self.agent.notify_about_announced_tichus(tichu=tichu, grand_tichu=grand_tichu)

    def play_first(self, game_history, wish):
        """
        Called by the the tichu manager to request a move.
        The combination must be a valid play according to the Tichu rules, in particular, PlayerAction must not be Pass.
        :return: the combination the players wants to play as PlayerAction.
        """
        assert len(self._hand_cards) > 0
        comb = self._agent.play_first(hand_cards=self.hand_cards,
                                      round_history=game_history.current_round.copy(save=self.position),
                                      wish=wish)
        action = PlayerAction(self, combination=comb)
        action.check(has_cards=self, not_pass=True, raise_exception=True)
        TichuPlayer._check_wish(game_history.last_combination, action, self.hand_cards, wish)
        self._hand_cards.remove_all(action.combination.cards)
        self._log_remaining_handcards()
        return action

    def play_combination(self, game_history, wish):
        """
        Called by the the tichu manager to request a move.
        :param game_history: The history of the tichu so far.
        :param wish: The CardValue beeing wished, None if no wish is present
        :return: pass, or the combination the players wants to play as PlayerAction.
        """
        assert len(self._hand_cards) > 0
        comb = self._agent.play_combination(wish=wish, hand_cards=self.hand_cards,
                                            round_history=game_history.current_round.copy(save=self.position))
        action = PlayerAction(self, combination=comb)
        action.check(played_on=game_history.last_combination(), has_cards=self, raise_exception=True)
        TichuPlayer._check_wish(game_history.last_combination, action, self.hand_cards, wish)

        if not action.is_pass():
            self._hand_cards.remove_all(action.combination.cards)
            self._log_remaining_handcards()

        return action

    @staticmethod
    def _check_wish(played_on, action, hand_cards, wish):
        """
        Checks whether the action does not fulfill the wish, but one could have fulfilled it with the handcards and played on Combination
        :param played_on: Combination to play on
        :param action: PlayerAction
        :param hand_cards: The available cards
        :param wish: CardValue (may be None)
        :return: True if ok
        :raise IllegalActionException: If wish could have been fulfilled, but was not.
        """
        if wish:  # there is a wish
            if action.is_pass() or not action.combination.fulfills_wish(wish):  # player did not fulfill wish
                if wish in {c.card_value for c in hand_cards}:  # player has wish in handcards
                    # look if the player could have fulfilled the wish
                    possible_combs = hand_cards.all_combinations(played_on, contains_value=wish)
                    if len(possible_combs) > 0:
                        raise IllegalActionException("""Could have played the wish, but did not. wish: {} \n
                                                        handcards: {}, \n
                                                        possible combs:{}""".format(wish, hand_cards, possible_combs))
        return True

    def play_bomb_or_not(self, game_history):
        """
        Called by the the tichu manager to allow the players to play a bomb.
        :param game_history:The history of the tichu so far.
        :return: the bomb (as PlayerAction) if the players wants to play a bomb. False or None otherwise
        """
        bomb_comb = self._agent.play_bomb(hand_cards=self.hand_cards, round_history=game_history.current_round.copy(save=self.position))
        bomb_action = False
        if bomb_comb:
            bomb_action = PlayerAction(self, combination=bomb_comb)
            bomb_action.check(played_on=game_history.last_combination(), has_cards=self, is_bomb=True, raise_exception=True)
            self._hand_cards.remove_all(bomb_action.combination.cards)
            self._log_remaining_handcards()
        return bomb_action

    def give_dragon_away(self, game_history):
        """
        :param game_history:The history of the tichu so far.
        :return: id of the players to give the trick to.
        """
        pos = self._agent.give_dragon_away(hand_cards=self.hand_cards, round_history=game_history.current_round.copy(save=self.position))
        assert_(pos in range(4) and pos != self.position and pos != self.team_mate)
        return pos

    def wish(self, game_history):
        """
        :param game_history:The history of the tichu so far.
        :return: The CardValue to be wished
        """
        w = self._agent.wish(self.hand_cards, game_history.current_round.copy(save=self.position))
        assert_(isinstance(w, CardValue) and w not in {CardValue.PHOENIX, CardValue.DRAGON, CardValue.DOG, CardValue.MAHJONG},
                IllegalActionException("The wish must be a CardValue and not a special card, but was "+repr(w)))
        return w

    def _log_remaining_handcards(self):
        logging.debug("remaining Handcards {}: {}".format(self.name, ", ".join([str(c) for c in sorted(self._hand_cards)])))

    def __hash__(self):
        return self._hash

    def __eq__(self, other):
        return isinstance(other, self.__class__) and self.__hash__() == hash(other) and self.name == other.name

    def __str__(self):
        return "{}(\n\tname: {}, pos: {}, teammate:{},\n\thandcards:{}, \n\ttricks:{}, \n\tagent:{}, \n\thash:{}\n)".format(str(self.__class__), str(self.name), str(self.position), str(self.team_mate), str(self._hand_cards), str(self.tricks), str(self._agent), str(self._hash))

    def __repr__(self):
        return "{}(\n\tname: {}, pos: {}, \n\thandcards:{}, \n\ttricks:{}\n)".format(str(self.__class__), str(self.name), str(self.position), str(self._hand_cards), str(self.tricks))


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
        :param player: The players playing the action.
        :param combination: Combination (default None); The combination the players wants to play, or False when players wants to pass.
        :param pass_: boolean (default True); True when the players wants to pass (Pass-action). Ignored when combination is not None
        :param tichu: boolean (default False); flag if the players wants to announce a Tichu with this action. Ignored when pass_=True and combination=False
        """
        # check params
        assert_(isinstance(player, TichuPlayer), msg="Player must be instance of TichuPlayer, but was {}".format(player.__class__))
        assert_(combination or pass_)
        assert_(pass_ or isinstance(combination, Combination))

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

        assert self._type is PlayerActionType.PASS or combination is not None, "comb: {}".format(combination)

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
        return "Action[{}](player: {}, tichu:{}, comb:{})".format(self._type, self._player.name, self._tichu, self._comb)

    def is_combination(self):
        return self._type is PlayerActionType.COMBINATION or self._type is PlayerActionType.COMBINATION_TICHU

    def is_tichu(self):
        return self._type is PlayerActionType.COMBINATION_TICHU

    def is_pass(self):
        return self._type is PlayerActionType.PASS

    def is_bomb(self):
        return not self.is_pass() and isinstance(self.combination, Bomb)

    def check(self, played_on=False, has_cards=None, not_pass=False, is_bomb=False, raise_exception=False):
        """
        Checks the following propperties when the argument is not False:
        :param played_on: Combination, wheter the action can be played on the combination
        :param has_cards: Player, whether the player has the cards to play this action
        :param not_pass: bool, whether the action can be pass or not. (not_pass = True, -> action must not be pass action)
        :param is_bomb: bool, whether the action must be a bomb or not.
        :param raise_exception: if true, raises an IllegalActionException instead of returning False.
        :return: True if all checks succeed, False otherwise
        """
        def return_or_raise(check):
            if raise_exception:
                raise IllegalActionException("Action Check ('{}') failed on {}".format(check, repr(self)))
            else:
                return None
        # fed

        if played_on and not self.can_be_played_on(played_on, raise_exception=False):
            return return_or_raise("played on "+str(played_on))
        if has_cards and not self.does_player_have_cards(has_cards, raise_exception=False):
            return return_or_raise("has cards: "+str(has_cards))
        if not_pass and self.is_pass():
            return return_or_raise("not pass, but was Pass")
        if is_bomb and not self.is_bomb():
            return return_or_raise("must be bomb")
        return True

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
            if not res and raise_exception:
                raise IllegalActionException("{} can not be played on {}".format(self._comb, comb))
        except ValueError as ve:
            res = False
        except TypeError as te:
            res = False

        return res

    def does_player_have_cards(self, player=None, raise_exception=False):
        """
        :param player: TichuPlayer (default None); the players whose hand_cards are to be tested. If is None, then the players playing the Action is taken.
        :param raise_exception: boolean (default False); if True, instead of returning False, raises an IllegalActionError.
        :return: True iff the Actions combination is a subset of the players hand_cards. False otherwise.
        """
        if player is None:
            player = self.player
        res = self._type is PlayerActionType.PASS or self._comb.issubset(player.hand_cards)
        if not res and raise_exception:
            raise IllegalActionException("Player {} does not have the right cards for {}".format(player, self._comb))
        return res



