import warnings
from pprint import pformat
from collections import namedtuple

import abc
from tichu.cards.card import Card, CardValue
from tichu.cards.cards import Combination, ImmutableCards, Cards
from tichu.cards.cards import Single
from tichu.exceptions import IllegalActionException
from tichu.players.tichuplayers import TichuPlayer
from tichu.typedcollections import TypedList, TypedTuple

# --------------- Trick ------------------------
from tichu.utils import check_param, check_isinstance, check_all_isinstance


class CombinationList(TypedList):
    """ List only accepting Combination instances
    >>> CombinationList([Single(Card.PHOENIX)])
    [SINGLE(PHOENIX)]
    >>> CombinationList((1, 3, 4))
    Traceback (most recent call last):
    ...
    TypeError: All elements must be instance of <class 'tichu.cards.cards.Combination'>
    >>> cl = CombinationList([Single(Card.PHOENIX)])
    >>> cl.append(Single(Card.DRAGON))
    >>> cl
    [SINGLE(PHOENIX), SINGLE(DRAGON)]
    >>> CombinationList([Single(Card.PHOENIX), Single(Card.DRAGON)]).append('a')
    Traceback (most recent call last):
    ...
    TypeError: elem must be of type <class 'tichu.cards.cards.Combination'>

    >>> CombinationList([Single(Card.PHOENIX), Single(Card.DRAGON)])[0]
    SINGLE(PHOENIX)
    >>> cl = CombinationList([Single(Card.PHOENIX), Single(Card.DRAGON)])
    >>> cl[0] = Single(Card.DOG)
    >>> cl[0].card == Card.DOG
    True
    >>> cl = CombinationList([Single(Card.PHOENIX), Single(Card.DRAGON)])
    >>> cl[0] = 'a'
    Traceback (most recent call last):
    ...
    TypeError: value must be of type <class 'tichu.cards.cards.Combination'>
    """
    __slots__ = ()

    def __init__(self, iterable):
        super().__init__(Combination, iterable)


class CombinationTuple(TypedTuple):
    __slots__ = ()

    def __new__(cls, iterable):
        return TypedTuple.__new__(cls, Combination, iterable)


class UnfinishedTrick(CombinationList):
    """Mutable Trick (list of combinations) instance
    >>> UnfinishedTrick()
    []
    """
    __slots__ = ()

    def __init__(self, combinations=list()):
        super().__init__(combinations)

    @classmethod
    def from_trick(cls, trick):
        return cls(list(trick))

    @property
    def last_combination(self):
        return self[-1] if len(self) > 0 else None

    def is_empty(self):
        return len(self) == 0

    def copy(self):
        return UnfinishedTrick(list(self))

    def finish(self):
        """
        :return: An (immutable) Trick
        """
        return Trick(combinations=list(self))


class Trick(CombinationTuple):
    """ (Immutable) List of Combinations """
    __slots__ = ()

    def __init__(self, combinations):
        """
        :param combinations: a sequence of combinations.
        """
        super().__init__(combinations)

    @property
    def combinations(self):
        return list(self)

    @property
    def points(self):
        return self.count_points()

    @property
    def last_combination(self):
        """
        :return: The last combination of this trick
        """
        return self[-1]

    def is_dragon_trick(self):
        return Card.DRAGON in self[-1]

    def count_points(self):
        return sum([comb.points for comb in self])

    def pretty_string(self, indent=0):
        ind_str = "".join("\t" for _ in range(1))
        return f"{ind_str}Trick[{self[-1].player_pos}]: {' -> '.join([comb.pretty_string() for comb in self])}"

    def __repr__(self):
        return "{}({})".format(self.__class__.__name__, ' -> '.join([repr(com) for com in self]))


# -------------- Events and Actions -------------------


class GameEvent(object, metaclass=abc.ABCMeta):
    """ abstract parent class for all game events possible in the game """

    __slots__ = ("_player_pos",)

    def __init__(self, player_pos):
        check_param(player_pos in range(4))
        self._player_pos = player_pos

    @property
    def player_pos(self):
        return self._player_pos

    def __repr__(self):
        return f"{self.__class__.__name__}({self._player_pos})"

    def __str__(self):
        return self.__repr__()

    def __eq__(self, other):
        return self.__class__ == other.__class__ and self.player_pos == other.player_pos

    def __hash__(self):
        return hash(self.__class__) + self._player_pos


class FinishEvent(GameEvent):
    """ A player finished action"""
    __slots__ = ()

    def __str__(self):
        return f"Finish({self._player_pos})"


class WinTrickEvent(GameEvent):
    """ Win a trick """

    __slots__ = ("_trick",)

    def __init__(self, player_pos, trick):
        check_isinstance(trick, Trick)
        super().__init__(player_pos=player_pos)
        self._trick = trick

    @property
    def trick(self):
        return self._trick

    def __repr__(self):
        return f"{self.__class__.__name__}({self._player_pos}, {str(self._trick)})"

    def __eq__(self, other):
        return super().__eq__(other) and self.trick == other.trick

    def __hash__(self):
        return hash((self._player_pos, self._trick))


class PlayerAction(GameEvent, metaclass=abc.ABCMeta):
    """
    An action instigated by a player
    """
    pass


class PassAction(PlayerAction):
    """ The pass action"""

    __slots__ = ()

    def __str__(self):
        return f"Pass({self._player_pos})"


class TichuAction(PlayerAction):
    """ Announce a tichu action """
    __slots__ = ()

    def __str__(self):
        return f"Tichu({self._player_pos})"


class GrandTichuAction(PlayerAction):
    """ Announce a grand tichu action """
    __slots__ = ()

    def __str__(self):
        return f"GrandTichu({self._player_pos})"


class GiveDragonAwayAction(PlayerAction):
    """ Give dragon trick away action"""

    __slots__ = ("_trick", "_to")

    def __init__(self, player_from, player_to, trick):
        check_param(player_to in range(4) and abs(player_from - player_to) == 1)
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

    def __eq__(self, other):
        return super().__eq__(other) and self.trick == other.trick and self.to == other.to

    def __hash__(self):
        return hash((self._player_pos, self._trick, self._to))

    def __repr__(self):
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

    def __eq__(self, other):
        return super().__eq__(other) and self.card == other.card and self.to == other.to

    def __hash__(self):
        return hash((self._player_pos, self._card, self._to))

    def __repr__(self):
        return f"{self.__class__.__name__}({self._player_pos} -> {self._to}: {str(self._card)})"


class WishAction(PlayerAction):
    """ wish a CardValue action """

    __slots__ = ("_cardval",)

    def __init__(self, player_from, cardvalue):
        check_isinstance(cardvalue, CardValue)
        super().__init__(player_pos=player_from)
        self._cardval = cardvalue

    @property
    def card_value(self):
        return self._cardval

    def __eq__(self, other):
        return super().__eq__(other) and self.card_value == other.card_value

    def __hash__(self):
        return hash((self._player_pos, self._cardval))

    def __repr__(self):
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

    def __repr__(self):
        return f"{self.__class__.__name__}({self._player_pos}, {str(self._comb)})"

    def __eq__(self, other):
        return super().__eq__(other) and self.combination == other.combination

    def __hash__(self):
        return hash((self._player_pos, self._comb))


# ----------------- Immutable Game State and History -----------------


class GameState(namedtuple("GS", [])):
    pass  # TODO


class RoundState(namedtuple("RS", ["current_pos", "hand_cards", "won_tricks", "trick_on_table", "wish", "ranking",
                                   "nbr_passed", "announced_tichu", "announced_grand_tichu"])):
    def __init__(self, current_pos, hand_cards, won_tricks, trick_on_table, wish, ranking, nbr_passed,
                 announced_tichu, announced_grand_tichu):
        # some paranoid checks
        assert current_pos in range(4)
        assert isinstance(hand_cards, tuple)
        assert all(isinstance(hc, HandCardSnapshot) for hc in hand_cards)

        assert isinstance(won_tricks, tuple)
        assert all(isinstance(tricks, tuple) for tricks in won_tricks)
        assert all(all(isinstance(t, Trick) for t in tricks) for tricks in won_tricks)

        assert wish is None or isinstance(wish, CardValue)

        assert isinstance(ranking, tuple)
        assert all(r in range(4) for r in ranking)

        assert nbr_passed in range(3)  # must not be 3

        assert isinstance(announced_tichu, frozenset)
        assert isinstance(announced_grand_tichu, frozenset)
        assert all(r in range(4) for r in announced_tichu)
        assert all(r in range(4) for r in announced_grand_tichu)
        super().__init__()

    def next_player_turn(self):
        return next((ppos % 4 for ppos in range(self.current_pos + 1, self.current_pos + 4) if
                     len(self.hand_cards[ppos % 4]) > 0))

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
        final_ranking = self.ranking + [ppos for ppos in range(4) if ppos not in self.ranking]
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

    def pretty_string(self, indent=0):
        # TODO use pformat
        ind_str = "".join(" " for _ in range(indent))
        rounds_str = ("\n" + ind_str).join(r.pretty_string(indent=1) for r in self.rounds)
        s = (
        "{ind_str}game result: {gh.points[0]}:{gh.points[1]}\n{ind_str}number of rounds: {nbr_rounds}\n{ind_str}----------- Rounds  -----------------\n{ind_str}{rrs}"
        .format(gh=self, nbr_rounds=len(self.rounds), rrs=rounds_str, ind_str=ind_str))
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

        check_isinstance(card_swaps, frozenset)
        check_all_isinstance(card_swaps, SwapCardAction)
        check_param(len(card_swaps) == 12)
        check_param(len({sca.player_pos for sca in card_swaps}) == 4)
        check_param(len({sca.player_to for sca in card_swaps}) == 4)

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

    def pretty_string(self, indent=0):
        # TODO use pformat
        ind_str = "".join("\t" for _ in range(1))
        tricks_str = ("\n" + ind_str).join(t.pretty_string(indent=2) for t in self.tricks)
        s = (
        "{ind_str}round result: {rh.points[0]}:{rh.points[1]}\n{ind_str}number of Tricks: {nbr_tricks}\n{ind_str}ranking: {rh.ranking}\n{ind_str}handcards:{rh.complete_hands}\n{ind_str}--- Tricks ---\n{ind_str}{ts}"
        .format(rh=self, nbr_tricks=len(self.tricks), ts=tricks_str, ind_str=ind_str))
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

    def build(self):
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

    def add_round(self, round_history):
        check_isinstance(round_history, RoundHistory)
        self._rounds.append(round_history)


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
    def tricks(self):
        return tuple(self._tricks)

    @property
    def last_combination(self):
        if len(self._current_trick) == 0:
            return self._tricks[-1].last_combination if len(self._tricks) > 0 else None
        else:
            return self._current_trick.last_combination

    @property
    def last_finished_trick(self):
        return self._tricks[-1] if len(self._tricks) > 0 else None

    @property
    def last_finished_trick(self):
        return self._tricks[-1] if len(self._tricks) > 0 else None

    # ########## Card Swap ############

    def add_cardswap(self, swap_card_action):
        check_isinstance(swap_card_action, SwapCardAction)
        self._swap_actions.add(swap_card_action)
        assert len({(sw.player_pos, sw.player_to) for sw in self._swap_actions}) == len(self._swap_actions)

    # ###### Tichus #######

    def announce_grand_tichu(self, player_id):
        self._announced_grand_tichus.add(player_id)

    def announce_tichu(self, player_id):
        if player_id in self._announced_grand_tichus:
            raise IllegalActionException( "Player({}) can't announce normal Tichu when already announced grand Tichu.".format(player_id))
        self._announced_tichus.add(player_id)

    # ###### Trick #######

    def finish_trick(self, handcards):
        check_isinstance(handcards, HandCardSnapshot)
        self._tricks.append(self._current_trick.finish())
        self._handcards.append(handcards)
        self._current_trick = UnfinishedTrick()

    # ###### Ranking ######

    def ranking_append_player(self, player_pos):
        check_param(player_pos in range(4) and player_pos not in self._ranking)
        self._ranking.append(player_pos)

    def rank_of(self, player_pos):
        return self._ranking.index(player_pos) + 1 if player_pos in self._ranking else None

        # ###### Build #######

    def build(self):
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
                tricks=tuple(self._tricks),
                handcards=tuple(self._handcards),
                ranking=tuple(self._ranking),
                events=tuple(self._events),
        )


# ----------------- Others ---------------------


class Team(namedtuple("T", ["player1", "player2"])):
    def __init__(self, player1, player2):
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
        return "HCS:\n\t0:{}\n\t1:{}\n\t2:{}\n\t3:{}".format(self.handcards0.pretty_string(),
                                                             self.handcards1.pretty_string(),
                                                             self.handcards2.pretty_string(),
                                                             self.handcards3.pretty_string())
