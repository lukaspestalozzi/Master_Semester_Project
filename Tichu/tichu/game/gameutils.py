import logging

import warnings
from pprint import pformat
from collections import namedtuple

import abc
from tichu.cards.card import Card, CardValue
from tichu.cards.cards import Combination, ImmutableCards, Cards, Bomb
from tichu.cards.cards import Pair
from tichu.exceptions import IllegalActionException
from tichu.typedcollections import TypedList, TypedTuple
from tichu.utils import check_param, check_isinstance, check_all_isinstance, check_true, indent

# --------------- Trick ------------------------


class CombinationActionList(TypedList):
    """ List only accepting Combination instances
    """
    __slots__ = ()

    def __init__(self, iterable):
        super().__init__(CombinationAction, iterable)


class CombinationActionTuple(TypedTuple):
    __slots__ = ()

    def __new__(cls, iterable):
        return TypedTuple.__new__(cls, CombinationAction, iterable)


class BaseTrick(metaclass=abc.ABCMeta):

    @property
    def last_combination(self):
        return self[-1].combination if len(self) > 0 else None

    @property
    def last_combination_action(self):
        return self[-1] if len(self) > 0 else None

    @property
    def points(self):
        return self.count_points()

    def count_points(self):
        return sum([comb.combination.points for comb in self])

    def is_empty(self):
        return len(self) == 0

    def pretty_string(self, indent_=0):
        ind_str = indent(indent_, s=" ")
        if self.is_empty():
            return f"{self.__class__.__name__}(empty)"
        else:
            return f"{ind_str}{self.__class__.__name__}[{self[-1].player_pos}]: {' -> '.join([comb.pretty_string() for comb in self])}"

    def __str__(self):
        return self.pretty_string()


class UnfinishedTrick(CombinationActionList, BaseTrick):
    """Mutable Trick (list of combinations) instance
    >>> UnfinishedTrick()
    []
    >>> UnfinishedTrick().is_empty()
    True
    >>> UnfinishedTrick().count_points()
    0
    >>> UnfinishedTrick().last_combination_action

    >>> UnfinishedTrick().last_combination

    """
    __slots__ = ()

    def __init__(self, comb_actions=list()):
        super().__init__(comb_actions)

    @classmethod
    def from_trick(cls, trick):
        return cls(list(trick))

    def copy(self):
        return UnfinishedTrick(list(self))

    def finish(self):
        """
        :return: An (immutable) Trick
        """
        return Trick(list(self))


class Trick(CombinationActionTuple, BaseTrick):
    """ (Immutable) List of Combinations
    >>> Trick([])
    Trick()
    >>> Trick([]).is_empty()
    True
    >>> Trick([]).count_points()
    0
    >>> Trick([]).last_combination_action

    >>> Trick([]).last_combination

    >>> Trick([CombinationAction(1, Pair(Card.A_HOUSE, Card.A_JADE))])
    Trick(CombinationAction(1, PAIR(A♣,A♦)))
    >>> Trick([CombinationAction(1, Pair(Card.A_HOUSE, Card.A_JADE))]).is_empty()
    False
    >>> Trick([CombinationAction(1, Pair(Card.K_HOUSE, Card.K_JADE))]).count_points()
    20
    >>> Trick([CombinationAction(1, Pair(Card.A_HOUSE, Card.A_JADE))]).last_combination_action
    CombinationAction(1, PAIR(A♣,A♦))
    >>> Trick([CombinationAction(1, Pair(Card.A_HOUSE, Card.A_JADE))]).last_combination
    PAIR(A♣,A♦)
    """
    __slots__ = ()

    def __init__(self, comb_actions):
        """
        :param comb_actions: a sequence of combinations.
        """
        super().__init__()

    @property
    def combinations(self):
        return list(self)

    @property
    def last_combination_action(self):
        return self[-1] if len(self) > 0 else None

    def add_combination_action(self, combination_action):
        ut = UnfinishedTrick.from_trick(self)
        ut.append(combination_action)
        return ut.finish()

    def is_dragon_trick(self):
        return Card.DRAGON in self.last_combination

    def __repr__(self):
        return "{}({})".format(self.__class__.__name__, ' -> '.join([repr(com) for com in self]))


# -------------- Events and Actions -------------------
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


class WinTrickEvent(PlayerGameEvent):
    """ Win a trick """

    __slots__ = ("_hand_cards")

    def __init__(self, player_pos, trick, hand_cards):
        """
        :param player_pos:
        :param hand_cards: The HandCardSnapshot of the players when the trick finished
        """
        check_isinstance(hand_cards, HandCardSnapshot)
        check_isinstance(trick, Trick)
        super().__init__(player_pos=player_pos)
        self._hand_cards = hand_cards
        self._trick = trick

    @property
    def hand_cards(self):
        return self._hand_cards

    @property
    def trick(self):
        return self._trick

    def pretty_string(self, indent_=0):
        return f"{indent(indent_, s=' ')}{self.__class__.__name__}(winner:{self._player_pos})"

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

        if isinstance(played_on, Combination):
            check_true(self.can_be_played_on_combination(played_on), ex=IllegalActionException,
                       msg=f"{self} can't be played on {played_on}")

        from tichu.players.tichuplayers import TichuPlayer  # TODO import on top?
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
            check_true(self.is_bomb(), ex=IllegalActionException, msg=f"Action must not be Bomb, but was {self}")
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
            check_param(cardvalue not in {CardValue.PHOENIX, CardValue.DRAGON, CardValue.DOG, CardValue.MAHJONG}, msg="Wish can't be a special card.")
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

# ----------------- Immutable Game State and History -----------------


class GameState(namedtuple("GS", [])):
    pass  # TODO


class RoundState(namedtuple("RS", ["current_pos", "hand_cards", "won_tricks", "trick_on_table", "wish", "ranking",
                                   "nbr_passed", "announced_tichu", "announced_grand_tichu"])):
    def __init__(self, current_pos, hand_cards, won_tricks, trick_on_table, wish, ranking, nbr_passed,
                 announced_tichu, announced_grand_tichu):
        super().__init__()
        # some paranoid checks
        assert current_pos in range(4)
        assert isinstance(hand_cards, HandCardSnapshot)

        assert isinstance(won_tricks, tuple)
        assert all(isinstance(tricks, tuple) for tricks in won_tricks)
        assert all(all(isinstance(t, Trick) for t in tricks) for tricks in won_tricks)

        assert wish is None or isinstance(wish, CardValue)

        assert isinstance(ranking, tuple)
        assert all(r in range(4) for r in ranking)

        assert nbr_passed in range(4-len(ranking)), f"nbr pass: {nbr_passed}, ranking: {self.ranking}, possible: {[range(4-len(self.ranking)-1)]}"  # the players not in ranking can pass, not more

        assert isinstance(announced_tichu, frozenset)
        assert isinstance(announced_grand_tichu, frozenset)
        assert all(r in range(4) for r in announced_tichu)
        assert all(r in range(4) for r in announced_grand_tichu)

        self._action_state_transitions = dict()
        self._possible_actions = None
        self._possible_combs = None
        self._satisfy_wish = None
        self._can_pass = None

        # end __init__

    def next_player_turn(self):
        return next((ppos % 4 for ppos in range(self.current_pos + 1, self.current_pos + 4) if len(self.hand_cards[ppos % 4]) > 0))

    def is_double_win(self):
        return len(self.ranking) >= 2 and self.ranking[0] == (self.ranking[1] + 2) % 4

    def is_terminal(self):
        return (len(self.ranking) >= 3
                or sum([len(hc) > 0 for hc in self.hand_cards]) <= 1  # equivalent to previous one TODO remove?
                or self.is_double_win())

    def calculate_points(self):
        """
        Only correct if the state is terminal
        :return: tuple of length 4 with the points of each player at the corresponding index.
        """
        # TODO Test
        def calc_tichu_points():
            tichu_points = [0, 0, 0, 0]
            for gt_pos in self.announced_grand_tichu:
                tichu_points[gt_pos] += 200 if gt_pos == self.ranking[0] else -200
            for t_pos in self.announced_tichu:
                tichu_points[t_pos] += 100 if t_pos == self.ranking[0] else -100
            return tichu_points

        if not self.is_terminal():
            warnings.warn("Calculating points of a NON terminal state! Result may be incorrect.")

        points = calc_tichu_points()
        final_ranking = list(self.ranking) + [ppos for ppos in range(4) if ppos not in self.ranking]
        assert len(final_ranking) == 4, "{} -> {}".format(self.ranking, final_ranking)

        if self.is_double_win():
            # double win
            points[final_ranking[0]] += 100
            points[final_ranking[1]] += 100
            points[final_ranking[2]] -= 100
            points[final_ranking[3]] -= 100
        else:
            # not double win
            for p in range(3):  # first 3 players get the points in their won tricks
                points[final_ranking[p]] += sum(t.points for t in self.won_tricks[final_ranking[p]])

            # first player gets the points of the last players tricks
            winner = final_ranking[0]
            looser = final_ranking[3]
            points[winner] += sum(t.points for t in self.won_tricks[looser])

            # the handcards of the last player go to the enemy team
            points[(looser + 1) % 4] += sum(t.points for t in self.hand_cards[looser])
        # fi

        # sum the points of each team
        for pos in range(4):
            points[pos] += points[(pos + 2) % 4]

        assert len(points) == 4
        return tuple(points)

    def possible_actions(self):
        """
        :return: frozenset of all possible actions in this state
        """
        if self._possible_actions is not None:
            return frozenset(self._possible_actions)
        poss_combs, _ = self._possible_combinations()
        poss_acs = {CombinationAction(player_pos=self.current_pos, combination=comb) for comb in poss_combs}
        if self._can_pass:
            poss_acs.add(PassAction(self.current_pos))
        assert self._possible_actions is None  # sanity check
        self._possible_actions = frozenset(poss_acs)
        return frozenset(poss_acs)

    def state_for_action(self, action):
        """
        :param action: CombinationAction or PassAction.
        :return: The new game state the action leads to.
        """
        if not action.player_pos == self.current_pos:
            raise IllegalActionException(f"Only player:{self.current_pos} can play in this case, but action was: {action}")
        if action in self._action_state_transitions:
            return self._action_state_transitions[action]

        elif isinstance(action, PassAction):
            new_state = self._state_for_pass()

        elif isinstance(action, CombinationAction):
            assert action.combination.can_be_played_on(self.trick_on_table.last_combination)
            new_state = self._state_for_combination_action(action)

        else:
            raise ValueError("action must be PassActon or a CombinationAction")
        self._action_state_transitions[action] = new_state
        return new_state

    def _possible_combinations(self):
        """
        :return: a tuple of the possible combinations and whether the combinations satisfy the wish
        """
        if self._possible_combs is not None:
            # return already calculated combinations
            return (frozenset(self._possible_combs), self._satisfy_wish)
        comb_on_table = self.trick_on_table.last_combination
        possible_combs = set(self.hand_cards[self.current_pos].all_combinations(played_on=comb_on_table))
        # verify wish
        self._satisfy_wish = False
        if self.wish and self.wish in (c.card_value for c in self.hand_cards[self.current_pos]):
            pcombs = {comb for comb in possible_combs if comb.contains_cardval(self.wish)}
            if len(pcombs):
                self._satisfy_wish = True
                possible_combs = pcombs
        self._possible_combs = frozenset(possible_combs)
        self._can_pass = self.trick_on_table.last_combination is not None and not self._satisfy_wish
        return (frozenset(possible_combs), self._satisfy_wish)

    def _state_for_combination_action(self, combination_action):
        comb = combination_action.combination
        new_trick_on_table = self.trick_on_table.add_combination_action(combination_action)
        new_handcards = self.hand_cards.remove_cards(from_pos=self.current_pos, cards=comb.cards)
        assert len(new_handcards[self.current_pos]) < len(self.hand_cards[self.current_pos])
        assert new_handcards[self.current_pos].issubset(self.hand_cards[self.current_pos])

        # test ranking:
        new_ranking = list(self.ranking)
        if len(new_handcards[self.current_pos]) == 0:
            new_ranking.append(self.current_pos)
            assert len(set(new_ranking)) == len(new_ranking), "state:{}\ncomb:{}".format(self, comb)

        # handle dog
        next_player = self.next_player_turn()
        if Card.DOG in comb:
            next_player = next((ppos % 4 for ppos in range(self.current_pos+2, self.current_pos+3+2) if len(self.hand_cards[ppos % 4]) > 0))
            assert next_player is not None
            assert self.nbr_passed == 0  # just to be sure
            assert self.trick_on_table.is_empty()
            new_trick_on_table = Trick([])  # dog is removed instantly

        # create game-state
        gs = RoundState(current_pos=next_player,
                        hand_cards=new_handcards,
                        won_tricks=self.won_tricks,
                        trick_on_table=new_trick_on_table,
                        wish=None if comb.fulfills_wish(self.wish) else self.wish,
                        ranking=tuple(new_ranking),
                        nbr_passed=0,
                        announced_tichu=self.announced_tichu,
                        announced_grand_tichu=self.announced_grand_tichu)
        return gs

    def _state_for_pass(self):
        new_won_tricks = self.won_tricks  # tricks is a tuple (of len 4) containing tuple of tricks
        new_trick_on_table = self.trick_on_table
        new_passed_nr = self.nbr_passed + 1

        next_player_pos = self.next_player_turn()
        leading_player = self.trick_on_table.last_combination_action.player_pos

        if (leading_player == next_player_pos
                or self.current_pos < leading_player < next_player_pos
                or next_player_pos < self.current_pos < leading_player
                or leading_player < next_player_pos < self.current_pos):
            # trick ends with leading as winner
            trick_winner_pos = leading_player
            # TODO handle Dragon, who give to? return 2 states?
            # give the trick to the trick_winner_pos TODO create TrickSnapshots
            winner_tricks = list(self.won_tricks[trick_winner_pos])
            winner_tricks.append(self.trick_on_table)
            new_won_tricks = list(self.won_tricks)
            new_won_tricks[trick_winner_pos] = tuple(winner_tricks)
            new_won_tricks = tuple(new_won_tricks)
            new_trick_on_table = Trick([])  # There is a new trick on the table
            new_passed_nr = 0

        gs = RoundState(current_pos=next_player_pos,
                        hand_cards=self.hand_cards,
                        won_tricks=new_won_tricks,
                        trick_on_table=new_trick_on_table,
                        wish=self.wish,
                        ranking=tuple(self.ranking),
                        nbr_passed=new_passed_nr,
                        announced_tichu=self.announced_tichu,
                        announced_grand_tichu=self.announced_grand_tichu)

        assert 0 <= gs.nbr_passed < 3
        assert ((gs.trick_on_table.is_empty() and gs.nbr_passed == 0) or ((not gs.trick_on_table.is_empty()) and gs.nbr_passed > 0))
        return gs

    def __hash__(self):
        # return hash((self.__class__, self.current_pos, self.hand_cards, self.trick_on_table, self.wish, self.nbr_passed))
        return super().__hash__()

    def __eq__(self, other):
        """return (self.__class__ == other.__class__
                and self.current_pos == other.current_pos
                and self.hand_cards == other.hand_cards
                and self.trick_on_table == other.trick_on_table
                and self.wish == other.wish
                and self.nbr_passed == other.nbr_passed)"""
        return super().__eq__(other)


class GameHistory(namedtuple("GH", ["team1", "team2", "winner_team", "points", "target_points", "rounds"])):
    def __init__(self, team1, team2, winner_team, points, target_points, rounds):
        check_isinstance(team1, Team)
        check_isinstance(team2, Team)
        check_isinstance(winner_team, Team)
        check_isinstance(points, tuple)
        check_param(len(points) == 2)
        check_isinstance(target_points, int)
        check_all_isinstance(rounds, RoundHistory)
        check_param(len(rounds) > 0)
        super().__init__()

    @property
    def points_team1(self):
        return self.points[0]

    @property
    def points_team2(self):
        return self.points[1]

    def pretty_string_old(self, indent=0):
        # TODO use pformat
        ind_str = "".join(" " for _ in range(indent))
        rounds_str = ("\n" + ind_str).join(r.pretty_string(indent=1) for r in self.rounds)
        s = (
        "{ind_str}game result: {gh.points[0]}:{gh.points[1]}\n{ind_str}number of rounds: {nbr_rounds}\n{ind_str}----------- Rounds  -----------------\n{ind_str}{rrs}"
        .format(gh=self, nbr_rounds=len(self.rounds), rrs=rounds_str, ind_str=ind_str))
        return s

    def pretty_string(self, indent_=0):
        ind = indent(indent_, s=" ")
        s =  f"{ind}Game Result: {self.points}\n"
        s += f"{ind}Number of Rounds: {len(self.rounds)}\n"
        s += "----------- Rounds -----------------\n"
        rind = indent_+4
        rind_str = indent(rind, s=" ")
        for k, round_ in enumerate(self.rounds):
            s += f"{rind_str}----------- Round {k} -----------------\n"
            s += round_.pretty_string(rind)
            s += "\n"
        return s


class RoundHistory(namedtuple("RH", ["initial_points", "final_points", "points", "grand_tichu_hands", "before_swap_hands", "card_swaps", "complete_hands", "announced_grand_tichus", "announced_tichus", "tricks", "handcards", "ranking", "events"])):
    def __init__(self, initial_points, final_points, points, grand_tichu_hands, before_swap_hands,
                 card_swaps, complete_hands, announced_grand_tichus, announced_tichus, tricks, handcards, ranking,
                 events):
        check_isinstance(initial_points, tuple)
        check_isinstance(final_points, tuple)
        check_isinstance(points, tuple)
        check_param(len(initial_points) == len(final_points) == len(points) == 2)

        check_all_isinstance([grand_tichu_hands, before_swap_hands, complete_hands], HandCardSnapshot)

        if card_swaps != frozenset():
            check_isinstance(card_swaps, frozenset)
            check_all_isinstance(card_swaps, SwapCardAction)
            check_param(len(card_swaps) == 12, param=card_swaps)
            check_param(len({sca.player_pos for sca in card_swaps}) == 4)
            check_param(len({sca.to for sca in card_swaps}) == 4)

        check_isinstance(announced_grand_tichus, frozenset)
        check_isinstance(announced_tichus, frozenset)

        check_all_isinstance(tricks, Trick)

        check_all_isinstance(handcards, HandCardSnapshot)
        check_param(len(tricks) == len(handcards))

        check_isinstance(ranking, tuple)
        check_param(len(ranking) <= 4)

        check_isinstance(events, tuple)
        check_all_isinstance(events, GameEvent)

        super().__init__()

    @property
    def last_combination(self):
        return self.tricks[-1].last_combination if len(self.tricks) > 0 else None

    @property
    def combination_on_table(self):
        return self.last_combination

    @property
    def last_handcards(self):
        if len(self.handcards) > 0:
            return self.handcards[-1]
        for hnds in [self.complete_hands, self.before_swap_hands, self.grand_tichu_hands]:
            if hnds is not None:
                return hnds
        return None

    def nbr_passed(self):
        if len(self.tricks) == 0 or self.tricks[-1].is_empty():
            return 0
        else:
            nbr_passed = 0
            k = -1
            last_event = self.events[k]
            while not isinstance(last_event, (CombinationAction, WinTrickEvent)):
                if isinstance(last_event, PassAction):
                    nbr_passed += 1
                k -= 1
                last_event = self.events[k]
            return nbr_passed

    def pretty_string(self, indent_=0):
        ind = indent(indent_, s=" ")
        s =  f"{ind}Round Result: {self.points}\n"
        s += f"{ind}Game Points after Round: {self.final_points}\n"
        s += f"{ind}ranking: {self.ranking}\n"
        s += f"{ind}Number of Tricks: {len(self.tricks)}\n"
        ind4 = indent(indent_+4, s=' ')
        s += f"{ind4}---------- Tricks ----------\n"
        for k, trick in enumerate(self.tricks):
            s += trick.pretty_string(indent_+4)
            s += "\n"
        s += f"{ind4}---------- Events ----------\n"
        s += ind4
        s += ("\n"+ind4).join(ev.pretty_string() for ev in self.events)
        return s

# ----------------- Mutable Game State and History -----------------


class GameStateBuilder(object):
    pass  # TODO


class RoundStateBuilder(object):
    """
    Mutable Round state
    """

    def __init__(self, roundstate=None):
        if roundstate is None:
            self._current_pos = None
            self._hand_cards = (Cards(), Cards(), Cards(), Cards())
            self._won_tricks = [list(), list(), list(), list()]
            self._trick_on_table = UnfinishedTrick()
            self._wish = None
            self._ranking = list()
            self._nbr_passed = None
            self._announced_tichu = set()
            self._announced_grand_tichu = set()
        else:
            self._current_pos = roundstate.current_pos
            self._hand_cards = [Cards(cards) for cards in roundstate.hand_cards]
            self._won_tricks = [list(wt) for wt in roundstate.won_tricks]
            self._trick_on_table = UnfinishedTrick.from_trick(roundstate.trick_on_table)
            self._wish = roundstate.wish
            self._ranking = list(roundstate.ranking)
            self._nbr_passed = roundstate.nbr_passed
            self._announced_tichu = set(roundstate.announced_tichu)
            self._announced_grand_tichu = set(roundstate.announced_grand_tichu)

    def build(self, save=False):
        assert save is False, "save=True is not implemented"
        return RoundState(current_pos=self._current_pos,
                          hand_cards=HandCardSnapshot(*[ImmutableCards(cards) for cards in self._hand_cards]),
                          won_tricks=tuple([tuple(tks) for tks in self._won_tricks]),
                          trick_on_table=self._trick_on_table.finish(),
                          wish=self._wish,
                          ranking=tuple(self._ranking),
                          nbr_passed=self._nbr_passed,
                          announced_tichu=frozenset(self._announced_tichu),
                          announced_grand_tichu=frozenset(self._announced_grand_tichu)
                          )

    @property
    def current_pos(self):
        return self._current_pos

    @current_pos.setter
    def current_pos(self, val):
        check_param(val in range(4))
        self._current_pos = val

    @property
    def hand_cards(self):
        return self._hand_cards

    @hand_cards.setter
    def hand_cards(self, val):
        check_isinstance(val, HandCardSnapshot)
        self._hand_cards = val

    @property
    def won_tricks(self):
        return self._won_tricks

    def add_won_trick(self, pos, trick):
        check_isinstance(trick, Trick)
        self._won_tricks[pos].append(trick)

    @property
    def wish(self):
        return self._wish

    @wish.setter
    def wish(self, val):
        check_isinstance(val, CardValue)
        self._wish = val

    @property
    def trick_on_table(self):
        return self._trick_on_table

    @trick_on_table.setter
    def trick_on_table(self, val):
        if isinstance(val, Trick):
            self._trick_on_table = UnfinishedTrick.from_trick(val)
        else:
            check_isinstance(val, UnfinishedTrick)
            self._trick_on_table = val.copy()

    @property
    def ranking(self):
        return self._ranking

    @ranking.setter
    def ranking(self, val):
        check_param(v in range(4) for v in val)
        self._ranking = val

    @property
    def nbr_passed(self):
        return self._nbr_passed

    @nbr_passed.setter
    def nbr_passed(self, val):
        check_param(val in range(3))
        self._nbr_passed = val

    @property
    def announced_tichu(self):
        return self._announced_tichu

    @announced_tichu.setter
    def announced_tichu(self, val):
        check_param(v in range(4) for v in val)
        self._announced_tichu = set(val)

    def add_tichu(self, pos):
        check_param(pos in range(4))
        self._announced_tichu.add(pos)

    @property
    def announced_grand_tichu(self):
        return self._announced_grand_tichu

    @announced_grand_tichu.setter
    def announced_grand_tichu(self, val):
        check_param(v in range(4) for v in val)
        self._announced_grand_tichu = set(val)

    def add_grand_tichu(self, pos):
        check_param(pos in range(4))
        self._announced_grand_tichu.add(pos)


class GameHistoryBuilder(object):

    def __init__(self, team1=None, team2=None, winner_team=None, points=(0, 0), target_points=1000, rounds=list()):
        self._team1 = team1
        self._team2 = team2
        self._winner_team = winner_team
        self._points = points
        self.target_points = target_points
        self._current_round = None
        self._rounds = list(rounds)

    @classmethod
    def from_gamehistory(cls, game_history):
        return cls(team1=game_history.team1, team2=game_history.team2, winner_team=game_history.winner_team,
                   points=game_history.points, target_points=game_history.target_points, rounds=list(game_history.rounds))

    def build(self):
        return GameHistory(team1=self._team1, team2=self._team2,
                           winner_team=self._winner_team, points=self._points,
                           target_points=self.target_points, rounds=tuple(self._rounds))

    @property
    def team1(self):
        return self._team1

    @team1.setter
    def team1(self, team):
        check_isinstance(team, Team)
        self._team1 = team

    @property
    def team2(self):
        return self._team2

    @team2.setter
    def team2(self, team):
        check_isinstance(team, Team)
        self._team2 = team

    @property
    def winner_team(self):
        return self._team2

    @winner_team.setter
    def winner_team(self, team):
        check_isinstance(team, Team)
        self._winner_team = team

    @property
    def points(self):
        return self._points

    @points.setter
    def points(self, points):
        check_isinstance(points, tuple)
        check_all_isinstance(points, int)
        check_param(len(points) == 2)
        self._points = points

    @property
    def current_round(self):
        return self._current_round

    def _append_round(self, round_history):
        check_isinstance(round_history, RoundHistory)
        self._rounds.append(round_history)

    def finish_round(self):
        if self._current_round:
            # if there is a current round
            self._current_round.append_event(RoundEndEvent(self._current_round.ranking))
            self.points = self._current_round.final_points
            self._append_round(self._current_round.build())
        self._current_round = None

    def start_new_round(self):
        assert self._current_round is None
        self._current_round = RoundHistoryBuilder(initial_points=self.points)
        self._current_round.append_event(RoundStartEvent())
        return self._current_round

    def __repr__(self):
        return f"{self.__class__.__name__}\n\tpoints:{self._points}\n\tteam1:{self._team1}\n\tteam2:{self._team2}\n\tcurrent_round:{self._current_round}"


class RoundHistoryBuilder(object):

    def __init__(self, initial_points):
        check_param(len(initial_points) == 2)
        check_isinstance(initial_points, tuple)

        self._initial_points = initial_points
        self._points = initial_points
        empty_hcs = HandCardSnapshot(ImmutableCards([]), ImmutableCards([]), ImmutableCards([]), ImmutableCards([]))
        self._grand_tichu_hands = empty_hcs  # A HandCardSnapshot (initially all hands are empty)
        self._before_swap_hands = empty_hcs  # A HandCardSnapshot (initially all hands are empty)
        self._swap_actions = set()
        self._complete_hands = empty_hcs  # A HandCardSnapshot (initially all hands are empty)
        self._announced_grand_tichus = set()
        self._announced_tichus = set()
        self._tricks = list()
        self._current_trick = UnfinishedTrick()
        self._handcards = list()
        self._ranking = list()
        self._events = list()

    def __repr__(self):
        return f"{self.__class__.__name__}\n\tcurr trick:{self._current_trick}\n\tranking:{self._ranking}\n\ttricks:{self._tricks}\n\tevents:{self._events}"

    @property
    def initial_points(self):
        return self._initial_points

    @property
    def final_points(self):
        return (self._initial_points[0] + self._points[0], self._initial_points[1] + self._points[1])

    @property
    def points(self):
        return self._points

    @points.setter
    def points(self, points):
        check_isinstance(points, tuple)
        check_param(len(points) == 2)
        check_all_isinstance(points, int)
        self._points = points

    @property
    def grand_tichu_hands(self):
        return self._grand_tichu_hands

    @grand_tichu_hands.setter
    def grand_tichu_hands(self, hands):
        check_isinstance(hands, HandCardSnapshot)
        self._grand_tichu_hands = hands

    @property
    def before_swap_hands(self):
        return self._before_swap_hands

    @before_swap_hands.setter
    def before_swap_hands(self, hands):
        check_isinstance(hands, HandCardSnapshot)
        self._before_swap_hands = hands

    @property
    def complete_hands(self):
        return self._complete_hands

    @complete_hands.setter
    def complete_hands(self, hands):
        check_isinstance(hands, HandCardSnapshot)
        self._complete_hands = hands

    @property
    def announced_tichus(self):
        return set(self._announced_tichus)

    @property
    def announced_grand_tichus(self):
        return set(self._announced_grand_tichus)

    @property
    def ranking(self):
        return tuple(self._ranking)

    @property
    def tricks(self):
        return tuple(self._tricks)

    @property
    def last_combination(self):
        if len(self._current_trick) == 0:
            return self._tricks[-1].last_combination if len(self._tricks) > 0 else None
        else:
            return self._current_trick.last_combination

    @property
    def last_combination_action(self):
        if len(self._current_trick) == 0:
            return self._tricks[-1].last_combination_action if len(self._tricks) > 0 else None
        else:
            return self._current_trick.last_combination_action

    @property
    def current_handcards(self):
        if len(self._current_trick) > 0:
            last_hc = self._handcards[-1] if len(self._handcards) > 0 else self._complete_hands
            last_checkpoint = tuple([Cards(hc) for hc in last_hc])
            for comb_action in self._current_trick:
                last_checkpoint[comb_action.player_pos].remove_all(comb_action.combination)
            return HandCardSnapshot(*[ImmutableCards(hc) for hc in last_checkpoint])

        if len(self._handcards) > 0:
            return self._handcards[-1]
        if self._complete_hands:
            return self.complete_hands
        if self._before_swap_hands:
            return self.before_swap_hands
        else:
            return self.grand_tichu_hands

    @property
    def last_finished_trick(self):
        return self._tricks[-1] if len(self._tricks) > 0 else None

    @property
    def curr_trick_finished(self):
        """
        :return: Immutable Trick instance of the current trick
        """
        return self._current_trick.finish()

    # ---------- Swap Cards ---------- #

    def _add_swap_actions(self, event):
        self._swap_actions.add(event)
        check_true(len({(sw.player_pos, sw.to) for sw in self._swap_actions}) == len(self._swap_actions))

    # ---------- Tichus ---------- #

    def _announce_grand_tichu(self, player_pos):
        self._announced_grand_tichus.add(player_pos)

    def _announce_tichu(self, player_pos):
        check_true(player_pos not in self._announced_grand_tichus, ex=IllegalActionException,
                   msg=f"Player({player_pos}) can't announce normal Tichu when already announced grand Tichu.")
        self._announced_tichus.add(player_pos)

    # ---------- Trick ---------- #
    def current_trick_is_empty(self):
        return self._current_trick.is_empty()

    def current_trick_is_dragon_trick(self):
        return Card.DRAGON in self._current_trick.last_combination if self._current_trick.last_combination is not None else False

    def _finish_trick(self, event):
        assert self._current_trick.finish() == event.trick, f"There might be a LogicProblem, {self._current_trick.finish()} must be equals {event.trick}, but was not!"
        self._tricks.append(event.trick)
        self._handcards.append(event.hand_cards)
        self._current_trick = UnfinishedTrick()

    # ---------- Ranking ---------- #

    def _ranking_append_player(self, player_pos):
        check_param(player_pos in range(4) and player_pos not in self._ranking)
        self._ranking.append(player_pos)

    def is_double_win(self):
        return len(self.ranking) >= 2 and self.ranking[0] == (self.ranking[1] + 2) % 4

    def round_ended(self):
        return len(self._ranking) >= 3 or self.is_double_win()

    # ---------- Events ------------- #
    def append_all_events(self, events):
        for event in events:
            self.append_event(event)

    def append_event(self, event):
        check_isinstance(event, GameEvent)
        self._handle_event(event)
        self._events.append(event)

    def _handle_event(self, event):
        if isinstance(event, FinishEvent):
            self._ranking_append_player(event.player_pos)

        if isinstance(event, WinTrickEvent):
            self._finish_trick(event)

        if isinstance(event, PassAction):
            pass

        if isinstance(event, TichuAction):
            self._announce_tichu(event.player_pos)

        if isinstance(event, GrandTichuAction):
            self._announce_grand_tichu(event.player_pos)

        if isinstance(event, GiveDragonAwayAction):
            pass

        if isinstance(event, SwapCardAction):
            self._add_swap_actions(event)

        if isinstance(event, WishAction):
            pass

        if isinstance(event, CombinationAction):
            self._current_trick.append(event)

    def build(self, save=False):
        assert save is False, "save=True is not implemented"
        tks = list(self._tricks)
        additional_hcrds = []
        # print("tks before", tks, "current trick", self._current_trick)
        # print("additional_hcrds before", additional_hcrds)
        if len(self._current_trick) > 0:
            tks += [self._current_trick.finish()]
            # calculate updated handards
            additional_hcrds = [self.current_handcards]
        # print("tks", tks)
        # print("additional_hcrds", additional_hcrds)
        return RoundHistory(
                initial_points=self._initial_points,
                final_points=self.final_points,
                points=self.points,
                grand_tichu_hands=self.grand_tichu_hands,
                before_swap_hands=self.before_swap_hands,
                card_swaps=frozenset(self._swap_actions),
                complete_hands=self.complete_hands,
                announced_grand_tichus=frozenset(self.announced_grand_tichus),
                announced_tichus=frozenset(self.announced_tichus),
                tricks=tuple(tks),
                handcards=tuple(self._handcards + additional_hcrds),
                ranking=tuple(self._ranking),
                events=tuple(self._events),
        )


# ----------------- Others ---------------------


class Team(namedtuple("T", ["player1", "player2"])):
    def __init__(self, player1, player2):
        from tichu.players.tichuplayers import TichuPlayer  # TODO import on top?
        check_isinstance(player1, TichuPlayer)
        check_isinstance(player2, TichuPlayer)
        super(Team, self).__init__()

    @property
    def second_player(self):
        return self.player2

    @property
    def first_player(self):
        return self.player1

    def __contains__(self, player):
        return player == self.player1 or player == self.player2

    def __str__(self):
        return "Team(player1:{}, player2:{})".format(self.player1, self.player2)


class HandCardSnapshot(namedtuple("HCS", ["handcards0", "handcards1", "handcards2", "handcards3"])):
    """
    Contains 4 ImmutableCards instances representing the handcards of the 4 players.
    """

    def __init__(self, handcards0, handcards1, handcards2, handcards3):
        check_all_isinstance([handcards0, handcards1, handcards2, handcards3], ImmutableCards)
        super().__init__()

    def remove_cards(self, from_pos, cards):
        """

        :param from_pos:
        :param cards:
        :return: a new HandCardSnapshot instance with the cards removed from the given position
        """
        cards_at_pos = Cards(self[from_pos])
        cards_at_pos.remove_all(cards)
        new_cards_at_pos = cards_at_pos.to_immutable()
        new_l = list(self)
        new_l[from_pos] = new_cards_at_pos
        return HandCardSnapshot(*new_l)

    def copy(self, save=False):
        """
        Makes a copy of this instance
        :param save: (default False)
         - an integer (in range(4)) then the copy will only contain information as seen by the player at this position.
         - False, it is a complete copy.

        :return: a copy of this instance
        """
        if save is False:
            return HandCardSnapshot(self.handcards0, self.handcards1, self.handcards2, self.handcards3)
        elif save is not True and save in range(4):
            empty_hc = [ImmutableCards(list()) for _ in range(4)]
            empty_hc[save] = [self.handcards0, self.handcards1, self.handcards2, self.handcards3][save]
            return HandCardSnapshot(*empty_hc)
        else:
            raise ValueError("save must be one of [False, 0, 1, 2, 3] but was: " + str(save))

    def __str__(self):
        return "HandCardSnapshot:\n\t0:{}\n\t1:{}\n\t2:{}\n\t3:{}".format(self.handcards0.pretty_string(),
                                                                          self.handcards1.pretty_string(),
                                                                          self.handcards2.pretty_string(),
                                                                          self.handcards3.pretty_string())
