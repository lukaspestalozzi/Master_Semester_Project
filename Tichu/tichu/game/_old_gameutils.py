import abc

from collections import namedtuple
from enum import Enum

from tichu.cards.card import Card
from tichu.cards.cards import ImmutableCards, Cards, Combination, Bomb
from tichu.exceptions import IllegalActionException, LogicError
from tichu.players.tichuplayers import TichuPlayer
from tichu.utils import check_param, check_isinstance, check_all_isinstance, check_true


def is_double_win(ranking):
    return len(ranking) >= 2 and ranking[0] == (ranking[1] + 2) % 4


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


class GameState(object):
    """
    Mutable Game state.
    """

    def __init__(self, team1, team2, target_points=1000):
        check_isinstance(team1, Team)
        check_isinstance(team2, Team)
        check_isinstance(target_points, int)
        check_param(target_points > 0)

        self._teams = (team1, team2)
        self._target_points = target_points
        self._winner_team = None

        # rounds
        self._rounds = []  # List of TichuRoundHistory instances
        self._current_round = None

    @property
    def teams(self):
        return self._teams

    @property
    def team1(self):
        return self._teams[0]

    @property
    def team2(self):
        return self._teams[1]

    @property
    def points(self):
        curr_p = self._current_round.points if self._current_round else (0, 0)
        return (sum([r.points[0] for r in self._rounds]) + curr_p[0],
                sum([r.points[1] for r in self._rounds]) + curr_p[1])

    @property
    def winner_team(self):
        return self._winner_team

    @winner_team.setter
    def winner_team(self, t):
        check_isinstance(t, Team)
        check_param(t in self._teams)
        self._winner_team = t

    @property
    def rounds(self):
        return list(self._rounds)

    @property
    def current_round(self):
        return self._current_round

    @property
    def last_combination(self):
        return self._current_round.last_combination if self._current_round else None

    def start_new_round(self):
        curr_p = self.points
        if self._current_round:
            self.append_round(self._current_round.build())
        self._current_round = RoundState(initial_points=curr_p)
        return self._current_round

    def append_round(self, tichu_round):
        check_isinstance(tichu_round, TichuRoundHistory)
        self._rounds.append(tichu_round)

    def copy(self, save=False):
        """
        Makes a copy of this instance
        :param save: (default False)
         - an integer (in range(4)) then the copy will only contain information as seen by the player at this position.
         - False, it is a complete copy.

        :return: a copy of this instance
        """
        gs = GameState(self.team1, self.team2, self._target_points)
        gs._winner_team = self._winner_team
        gs._rounds = [r.copy(save=save) for r in self._rounds]
        gs._current_round = self._current_round.copy(save=save) if self._current_round else None
        if save is False:
            return gs
        else:
            # TODO copy the teams and remove the handcards from the players
            gs._team1 = None
            gs._team2 = None
            gs._winner_team = None
            return gs

    def build(self):
        """
        :return: A TichuGameHistory instance (which is immutable)
        """
        return TichuGameHistory(team1=self._teams[0],
                                team2=self._teams[1],
                                winner_team=self._winner_team,
                                points=self.points,
                                target_points=self._target_points,
                                rounds=tuple(self._rounds + [self.current_round.build()]))


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


class TichuGameHistory(namedtuple("TGH", ["team1", "team2", "winner_team", "points", "target_points", "rounds"])):

    def __init__(self, team1, team2, winner_team, points, target_points, rounds):
        check_isinstance(team1, Team)
        check_isinstance(team2, Team)
        check_isinstance(winner_team, Team)
        check_isinstance(points, tuple)
        check_param(len(points) == 2)
        check_isinstance(target_points, int)
        check_all_isinstance(rounds, TichuRoundHistory)
        super().__init__()

    @property
    def points_team1(self):
        return self.points[0]

    @property
    def points_team2(self):
        return self.points[1]

    def last_combination(self):
        return self.rounds[-1].last_combination

    def pretty_string(self, indent=0):
        ind_str = "".join(" " for _ in range(indent))
        rounds_str = ("\n"+ind_str).join(r.pretty_string(indent=1) for r in self.rounds)
        s = ("{ind_str}game result: {gh.points[0]}:{gh.points[1]}\n{ind_str}number of rounds: {nbr_rounds}\n{ind_str}----------- Rounds  -----------------\n{ind_str}{rrs}"
             .format(gh=self, nbr_rounds=len(self.rounds), rrs=rounds_str, ind_str=ind_str))
        return s


class TrickHandcards(namedtuple("AH", ["trick", "handcards"])):
    """
    Stores an (Trick, HandCardSnapshot) tuple
    """
    def __init__(self, trick, handcards):
        check_isinstance(trick, Trick)
        check_isinstance(handcards, HandCardSnapshot)
        super().__init__()


class RoundState(object):
    """
    Mutable Round state
    """

    def __init__(self, initial_points):
        check_param(len(initial_points) == 2)
        check_isinstance(initial_points, tuple)

        self._initial_points = initial_points

        # hands
        empty_hcs = HandCardSnapshot(ImmutableCards([]), ImmutableCards([]), ImmutableCards([]), ImmutableCards([]))
        self._grand_tichu_hands = empty_hcs  # A HandCardSnapshot (initially all hands are empty)
        self._before_swap_hands = empty_hcs  # A HandCardSnapshot (initially all hands are empty)
        self._swaps = None  # tuple of 4 SwapCards instances (initially empty)
        self._complete_hands = empty_hcs  # A HandCardSnapshot (initially all hands are empty)

        # tichus
        self._announced_grand_tichus = set()  # set of player_pos that announced grand tichu
        self._announced_tichus = set()  # set of player_pos that announced normal tichu

        # tricks & actions
        self._tricks_handcards = list()
        self._current_trick = UnfinishedTrick()

        # ranking
        self._ranking = list()

        # points
        self._points = (0, 0)

    # ###### Properties #######
    @property
    def initial_points(self):
        return self._initial_points

    @property
    def final_points(self):
        return (self.initial_points[0] + self._points[0], self.initial_points[1] + self._points[1])

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
    def card_swaps(self):
        return self._swaps

    @card_swaps.setter
    def card_swaps(self, swaps):
        check_all_isinstance(swaps, SwapCards)
        self._swaps = swaps

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
        return tuple([th.trick for th in self._tricks_handcards])

    @property
    def current_trick(self):
        return self._current_trick

    @property
    def ranking(self):
        return list(self._ranking)

    @property
    def current_handcards(self):
        # TODO speed
        if len(self._current_trick) > 0:
            last_hc = self._tricks_handcards[-1].handcards if len(self._tricks_handcards) > 0 else self._complete_hands
            last_checkpoint = tuple([Cards(hc) for hc in last_hc])
            for action in self._current_trick:
                if action.is_combination():
                    last_checkpoint[action.player.position].remove_all(action.combination)
            return HandCardSnapshot(*[ImmutableCards(hc) for hc in last_checkpoint])

        if len(self._tricks_handcards) > 0:
            return self._tricks_handcards[-1].handcards
        if self._complete_hands:
            return self.complete_hands
        if self._before_swap_hands:
            return self.before_swap_hands
        else:
            return self.grand_tichu_hands

    @property
    def combination_on_table(self):
        if self._current_trick is None:
            return self._tricks_handcards[-1].trick.last_combination if len(self._tricks_handcards) > 0 else None
        else:
            return self._current_trick.last_combination

    @property
    def last_combination(self):
        if len(self._current_trick) == 0:
            return self._tricks_handcards[-1].trick.last_combination if len(self._tricks_handcards) > 0 else None
        else:
            return self._current_trick.last_combination

    @property
    def last_finished_trick(self):
        return self._tricks_handcards[-1].trick if len(self._tricks_handcards) > 0 else None

    # ###### Tichus #######
    def announce_grand_tichu(self, player_id):
        self._announced_grand_tichus.add(player_id)

    def announce_tichu(self, player_id):
        if player_id in self._announced_grand_tichus:
            raise IllegalActionException("Player({}) can't announce normal Tichu when already announced grand Tichu.".format(player_id))
        self._announced_tichus.add(player_id)

    # ###### Trick #######
    def finish_trick(self, handcards):
        check_isinstance(handcards, HandCardSnapshot)
        self._tricks_handcards.append(TrickHandcards(self._current_trick.finish(), handcards))
        self._current_trick = UnfinishedTrick()

        # ###### Ranking #######

    # ###### Ranking ######
    def ranking_append_player(self, player_pos):
        check_param(player_pos in range(4) and player_pos not in self._ranking)
        self._ranking.append(player_pos)

    def is_double_win(self):
        return len(self._ranking) >= 2 and self._ranking[0] == (self._ranking[1] + 2) % 4

    def rank_of(self, player_pos):
        return self._ranking.index(player_pos) + 1 if player_pos in self._ranking else None

    # ###### Build #######
    def build(self, save=False):
        tks = tuple([t_h.trick.copy(save=save) for t_h in self._tricks_handcards])
        additional_hcrds = []
        if len(self._current_trick) > 0:
            tks += (self._current_trick.finish(save=save),)
            # calculate updated handards
            additional_hcrds = [self.current_handcards]
        if save:
            return SaveTichuRoundHistory(
                points=self.points,
                announced_grand_tichus=self.announced_grand_tichus,
                announced_tichus=self.announced_tichus,
                tricks=tks,
                ranking=self.ranking
            )

        else:
            return TichuRoundHistory(initial_points=self.initial_points,
                                     final_points=self.final_points,
                                     points=self.points,
                                     grand_tichu_hands=self.grand_tichu_hands,
                                     before_swap_hands=self.before_swap_hands,
                                     card_swaps=self.card_swaps,
                                     complete_hands=self.complete_hands,
                                     announced_grand_tichus=self.announced_grand_tichus,
                                     announced_tichus=self.announced_tichus,
                                     tricks=tks,
                                     handcards=tuple([t_h.handcards for t_h in self._tricks_handcards] + additional_hcrds),
                                     ranking=self.ranking)


class SaveTichuRoundHistory(namedtuple("STRH", ["points", "announced_grand_tichus", "announced_tichus", "tricks", "ranking"])):

    def __init__(self, points, announced_grand_tichus, announced_tichus, tricks, ranking):
        super().__init__()

    @property
    def last_combination(self):
        return self.tricks[-1].last_combination if len(self.tricks) > 0 else None

    @property
    def combination_on_table(self):
        return self.last_combination

    def nice_string(self, indent=0):
        ind_str = "".join("\t" for _ in range(1))
        tricks_str = ("\n"+ind_str).join(t.pretty_string(indent=2) for t in self.tricks)
        s = ("{ind_str}round result: {rh.points[0]}:{rh.points[1]}\n{ind_str}number of Tricks: {nbr_tricks}\n{ind_str}ranking: {rh.ranking}\n{ind_str}--- Tricks ---\n{ind_str}{ts}"
             .format(rh=self, nbr_tricks=len(self.tricks), ts=tricks_str, ind_str=ind_str))
        return s


class TichuRoundHistory(namedtuple("RoundHistory", ["initial_points", "final_points", "points", "grand_tichu_hands", "before_swap_hands", "card_swaps", "complete_hands", "announced_grand_tichus", "announced_tichus", "tricks", "handcards", "ranking"])):

    def __init__(self, initial_points, final_points, points, grand_tichu_hands, before_swap_hands,
                 card_swaps, complete_hands, announced_grand_tichus, announced_tichus, tricks, handcards, ranking):
        check_isinstance(initial_points, tuple)
        check_isinstance(final_points, tuple)
        check_isinstance(points, tuple)
        check_param(len(initial_points) == len(final_points) == len(points) == 2)
        check_all_isinstance([grand_tichu_hands, before_swap_hands, complete_hands], HandCardSnapshot)
        if card_swaps is not None:
            check_isinstance(card_swaps, tuple)
            check_param(len(card_swaps) == 4)
            check_all_isinstance(card_swaps, SwapCards)
        check_isinstance(announced_grand_tichus, set)
        check_isinstance(announced_tichus, set)
        check_all_isinstance(tricks, Trick)
        check_all_isinstance(handcards, HandCardSnapshot)
        check_param(len(tricks) == len(handcards))
        check_isinstance(ranking, list)
        check_param(len(ranking) <= 4)

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

    def is_double_win(self):
        return len(self.ranking) >= 2 and self.ranking[0] == (self.ranking[1] + 2) % 4

    def round_ended(self):
        """
        :return True if the round ended (doublewin or only one player has handcards left), False otherwise
        """
        res = len(self.ranking) == 4 or self.is_double_win()
        return res

    def nbr_passed(self):
        if len(self.tricks) == 0 or self.tricks[-1] is None:
            return 0
        else:
            nbr_passed = 0
            for i in [-1, -2, -3, -4]:
                if self.tricks[-1][i].is_pass():
                    nbr_passed += 1
                else:
                    return nbr_passed
            raise LogicError("Something went wrong. nbr_passed: {}; last_trick: {}".format(nbr_passed, self.tricks[-1]))

    def copy(self, save=False):
        if save:
            return SaveTichuRoundHistory(
                    points=self.points,
                    announced_grand_tichus=self.announced_grand_tichus,
                    announced_tichus=self.announced_tichus,
                    tricks=tuple([t.copy(save=True) for t in self.tricks]),
                    ranking=self.ranking
                )
        else:
            return self

    def pretty_string(self, indent=0):
        ind_str = "".join("\t" for _ in range(1))
        tricks_str = ("\n"+ind_str).join(t.pretty_string(indent=2) for t in self.tricks)
        s = ("{ind_str}round result: {rh.points[0]}:{rh.points[1]}\n{ind_str}number of Tricks: {nbr_tricks}\n{ind_str}ranking: {rh.ranking}\n{ind_str}handcards:{rh.complete_hands}\n{ind_str}--- Tricks ---\n{ind_str}{ts}"
             .format(rh=self, nbr_tricks=len(self.tricks), ts=tricks_str, ind_str=ind_str))
        return s


class Trick(object):
    """ (Immutable) List of PlayerActions """
    __slots__ = ("_actions",)

    def __init__(self, actions):
        check_all_isinstance(actions, PlayerAction)
        if len(actions) > 0:
            check_true(not actions[0].is_pass())
        self._actions = tuple(actions)

    @property
    def combinations(self):
        return [a.combination for a in self._actions if not a.is_pass()]

    @property
    def points(self):
        return self.sum_points()

    @property
    def last_combination(self):
        return self.combinations[-1] if len(self._actions) > 0 else None

    def is_dragon_trick(self):
        return Card.DRAGON in self.last_combination

    def last_action(self):
        return self._actions[-1] if len(self._actions) > 0 else None

    def sum_points(self):
        return sum([comb.points for comb in self.combinations])

    def copy(self, save=False):
        if save:
            return SaveTrick(self._actions)
        else:
            return Trick(self._actions)

    def pretty_string(self, indent=0):
        ind_str = "".join("\t" for _ in range(1))
        return "{ind_str}Trick[{winner}]: {trickstr}".format(trickstr=' -> '.join([ac.pretty_string() for ac in self._actions]), ind_str=ind_str, winner=self._actions[-1].player_name)

    def __getitem__(self, item):
        return self._actions[item]

    def __len__(self):
        return len(self._actions)

    def __repr__(self):
        return self.__str__()

    def __str__(self):
        return "{}({})".format(self.__class__.__name__, ' -> '.join([repr(com) for com in self._actions]))

    def __iter__(self):
        return self._actions.__iter__()


class SaveTrick(Trick):
    """
    Immutable Trick containing only save PlayerActions (no information about the player except the name)
    """
    __slots__ = ()

    def __init__(self, actions):
        save_actions = [SavePlayerAction.from_playeraction(a) for a in actions]
        super().__init__(save_actions)


class UnfinishedTrick(Trick):
    """
    Mutable Trick instance
    """
    __slots__ = ("_actions",)

    def __init__(self):
        super().__init__([])
        self._actions = list()

    def is_empty(self):
        return len(self._actions) == 0

    def add(self, action, check_validity=True):
        """
        :param action: the PlayerAction to be added.
        :param check_validity: boolean (default True); If True, checks whether the action can be played on the given trick.
        :return: self
        :raise ValueError: if check_validity=True and the check fails.
        :raise ValueError: if the action is not a PlayerAction
        """

        check_isinstance(action, PlayerAction)
        if check_validity:
            check_param(not (self.is_empty() and action.is_pass()), msg="Cant add a pass action on an empty trick.")
            check_param(self.is_empty() or action.can_be_played_on(self.last_combination), param=(self, action))
        self._actions.append(action)
        return self

    def finish(self, save=False):
        """
        :return: An (immutable) Trick
        """
        if save:
            return SaveTrick(actions=self._actions)
        else:
            return Trick(actions=self._actions)


Card_To = namedtuple("Card_To", ["card", "to"])
SwapCard = namedtuple("SwapCard", ["card", "from_", "to"])


# ####################### old actions ##########################
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
        check_isinstance(player, TichuPlayer)
        check_param(combination or pass_)
        check_param(pass_ or isinstance(combination, Combination))

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
    def player_name(self):
        return self._player.name

    @property
    def combination(self):
        """
        :return: The combination of the Action. May be None
        """
        return self._comb

    def pretty_string(self):
        if self.is_pass():
            return "{}[PASS]".format(self.player_name)
        else:
            s = "{}: {comb}".format(self.player_name, comb=str(self._comb))
            if self._tichu:
                s += " and [TICHU]"
            return s

    def __str__(self):
        return ("Action[{}](player: {})".format(self._type, self._player.name)
                if self.is_pass()
                else "Action[{}](player: {}, tichu:{}, comb:{})".format(self._type, self._player.name, self._tichu, self._comb))

    def __repr__(self):
        return "Action[{}](playername: {}, tichu:{}, comb:{})".format(self._type, self.player_name, self._tichu, self._comb)

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

        if played_on and not self.can_be_played_on(played_on):
            return return_or_raise("played on "+str(played_on))
        if has_cards and not self.does_player_have_cards(player=has_cards, raise_exception=False):
            return return_or_raise("has cards check; handcards: "+str(has_cards.hand_cards))
        if not_pass and self.is_pass():
            return return_or_raise("not pass, but was Pass")
        if is_bomb and not self.is_bomb():
            return return_or_raise("must be bomb")
        return True

    def can_be_played_on(self, comb):
        """
        Checks whether this action can be played on the given combination.
        That means in particular:
        - if the Action is a Pass-action, check succeeds
        - else, the Actions combination must be playable on the given comb
        :param comb: the Combination
        :return: True iff this check succeeds, False otherwise
        """
        return self._type is PlayerActionType.PASS or self._comb.can_be_played_on(comb)

    def does_player_have_cards(self, player, raise_exception=False):
        """
        :param player: TichuPlayer; the players whose hand_cards are to be tested.
        :param raise_exception: boolean (default False); if True, instead of returning False, raises an IllegalActionError.
        :return: True iff the Actions combination is a subset of the players hand_cards. False otherwise.
        """
        res = self._type is PlayerActionType.PASS or self._comb.issubset(player.hand_cards)
        if not res and raise_exception:
            raise IllegalActionException("Player {} does not have the right cards for {}".format(player, self._comb))
        return res


class SavePlayerAction(PlayerAction):

    def __init__(self, player, combination=None, pass_=True, tichu=False):
        super().__init__(player, combination=combination, pass_=pass_, tichu=tichu)
        self._player = player.name
        self._playername = player.name

    @property
    def player_name(self):
        return self._playername

    @classmethod
    def from_playeraction(cls, playeraction):
        return cls(playeraction.player,
                   playeraction.combination,
                   playeraction.is_pass(),
                   playeraction.is_tichu())


class SwapCards(object):
    """
    Contains 3 CardSwap instances from a players.
    """

    def __init__(self, player, card_to1, card_to2, card_to3):
        swapcards = [card_to1, card_to2, card_to3]

        # validate input
        if not all([isinstance(ct, Card_To) and isinstance(ct.card, Card) and ct.to in range(4) for ct in swapcards]):
            raise ValueError("The card_toX must be instance of Card_To and card must be instance of Card and 'to' must be in range(4).")
        if not isinstance(player, TichuPlayer):
            raise ValueError("The players must be instance of TichuPlayer, but was {}".format(repr(player)))
        if player.position in [sc.to for sc in swapcards]:
            raise ValueError("can't swap a card to itself")
        if not len(set([sc.to for sc in swapcards])) == 3:
            raise ValueError("must have 3 different recipients")
        if not len(set([sc.card for sc in swapcards])) == 3:
            raise ValueError("must have 3 different cards")
        if not all([sc.card in player.hand_cards for sc in swapcards]):
            raise ValueError("the players must possess all 3 cards")

        self._swapcards = tuple([SwapCard(card=sc.card, from_=player.position, to=sc.to) for sc in swapcards])
        self._from = player.position

    @property
    def swapcards(self):
        return self._swapcards

    @property
    def from_id(self):
        return self._from

    def cards(self):
        return [sc.card for sc in self._swapcards]

    def __iter__(self):
        return self._swapcards.__iter__()

    def __contains__(self, item):
        return self._swapcards.__contains__(item)

    def __getitem__(self, item):
        return self._swapcards.__getitem__(item)

    def __str__(self):
        return "SwapCards({})".format(self.swapcards)
