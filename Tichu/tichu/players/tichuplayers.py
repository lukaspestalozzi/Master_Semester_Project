import abc
import logging
import uuid


from tichu.agents.baseagent import BaseAgent
from tichu.cards.card import CardValue
from tichu.cards.cards import Cards, ImmutableCards, Single
from tichu.exceptions import IllegalActionException
from tichu.utils import check_true, check_isinstance
from tichu.game import gameutils as gutils


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
        self._teammate_pos = teammate
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
        swap_cards = self._agent.swap_cards(self.hand_cards)
        check_true(len(swap_cards) == 3
                   and len({sw.player_pos for sw in swap_cards}) == 1
                   and len({sw.to for sw in swap_cards}) == 3,
                   ex=IllegalActionException, msg="swap cards were not correct")
        for sw in swap_cards:
            self._hand_cards.remove(sw.card)
        return swap_cards

    def announce_grand_tichu_or_not(self, announced_grand_tichu):
        """
        :param announced_grand_tichu: a list of integers (in range(0, 4)), denoting playerIDs that already have announced a grand Tichu.
        :return True if this players announces a grand Tichu, False otherwise.
        """
        gt = self._agent.announce_grand_tichu(announced_grand_tichu)
        return bool(gt)

    def announce_tichu_or_not(self, announced_tichu, announced_grand_tichu, game_history):
        """
        :param game_history:
        :param announced_tichu: a list of integers (in range(0, 4)), denoting playerIDs that already have announced a Tichu.
        :param announced_grand_tichu: a list of integers (in range(0, 4)), denoting playerIDs that already have announced a grand Tichu.
        :return True if this players announces a normal Tichu, False otherwise.
        """
        nt = self._agent.announce_tichu(announced_tichu, announced_grand_tichu,
                                        round_history=game_history.current_round.build(save=self._copy_savely))
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
                                      round_history=game_history.current_round.build(save=self._copy_savely),
                                      wish=wish)

        action = gutils.PlayerAction(self, combination=comb)
        action.check(has_cards=self, not_pass=True, raise_exception=True)
        TichuPlayer._check_wish(game_history.current_round.last_combination, action, self.hand_cards, wish)
        self._hand_cards.remove_all(action.combination.cards)
        self._log_remaining_handcards()
        return action

    def play_combination(self, game_history, wish):
        """
        Called by the the tichu manager to request a move.
        :param game_history: The history of the tichu game so far.
        :param wish: The CardValue beeing wished, None if no wish is present
        :return: pass, or the combination the players wants to play as PlayerAction.
        """
        assert len(self._hand_cards) > 0
        comb = self._agent.play_combination(wish=wish, hand_cards=self.hand_cards,
                                            round_history=game_history.current_round.build(save=self._copy_savely))
        if isinstance(comb, Single) and comb.is_phoenix():
            comb.set_phoenix_height(game_history.current_round.last_combination.height + 0.5)
        action = gutils.PlayerAction(self, combination=comb)
        action.check(played_on=game_history.current_round.last_combination, has_cards=self, raise_exception=True)
        TichuPlayer._check_wish(game_history.current_round.last_combination, action, self.hand_cards, wish)

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
                if wish in (c.card_value for c in hand_cards):  # player has wish in handcards
                    # look if the player could have fulfilled the wish
                    possible_combs = list(hand_cards.all_combinations(played_on, contains_value=wish))
                    if len(possible_combs) > 0:
                        raise IllegalActionException(
                                "Could have played the wish, but did not. wish: {}, played {}, handcards: {}, possible combs:{}, comb on table: {}"
                                .format(wish, action.combination, hand_cards, possible_combs, played_on))
        return True

    def play_bomb_or_not(self, game_history):
        """
        Called by the the tichu manager to allow the players to play a bomb.
        :param game_history:The history of the tichu so far.
        :return: the bomb (as PlayerAction) if the players wants to play a bomb. False or None otherwise
        """
        bomb_comb = self._agent.play_bomb(hand_cards=self.hand_cards, round_history=game_history.current_round.build(save=self._copy_savely))
        bomb_action = False
        if bomb_comb:
            bomb_action = gutils.PlayerAction(self, combination=bomb_comb)
            bomb_action.check(played_on=game_history.current_round.last_combination, has_cards=self, is_bomb=True, raise_exception=True)
            self._hand_cards.remove_all(bomb_action.combination.cards)
            self._log_remaining_handcards()
        return bomb_action

    def give_dragon_away(self, game_history):
        """
        :param game_history:The history of the tichu so far.
        :return: id of the players to give the trick to.
        """
        pos = self._agent.give_dragon_away(hand_cards=self.hand_cards, round_history=game_history.current_round.build(save=self._copy_savely))
        check_true(pos in range(4) and pos != self.position and pos != self.team_mate, ex=IllegalActionException, msg="Can't give the Dragon to teammate")
        return pos

    def wish(self, game_history):
        """
        :param game_history:The history of the tichu so far.
        :return: The CardValue to be wished
        """
        w = self._agent.wish(self.hand_cards, game_history.current_round.build(save=self._copy_savely))
        w is None or check_isinstance(w, CardValue)
        check_true(w not in {CardValue.PHOENIX, CardValue.DRAGON, CardValue.DOG, CardValue.MAHJONG}, ex=IllegalActionException, msg="The wish must be a CardValue and not a special card, but was "+repr(w))
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

