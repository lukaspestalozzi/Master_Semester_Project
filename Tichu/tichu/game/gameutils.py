from collections import namedtuple

from tichu.cards.card import Card
from tichu.cards.cards import ImmutableCards, Cards
from tichu.exceptions import IllegalActionException
from tichu.players.tichuplayers import PlayerAction, TichuPlayer
from tichu.utils import assert_, raiser


class Team(namedtuple("T", ["player1", "player2"])):

    def __init__(self, player1, player2):
        assert_(isinstance(player1, TichuPlayer) and isinstance(player2, TichuPlayer))
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
        assert_(isinstance(team1, Team) and isinstance(team2, Team))
        assert_(isinstance(target_points, int) and target_points > 0)

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
        assert_(isinstance(t, Team) and t in self._teams)
        self._winner_team = t

    @property
    def rounds(self):
        return list(self._rounds)

    @property
    def current_round(self):
        return self._current_round

    def start_new_round(self):
        if self._current_round:
            self.append_round(self._current_round.build())
        self._current_round = RoundState(initial_points=self.points)
        return self._current_round

    def append_round(self, tichu_round):
        assert_(isinstance(tichu_round, TichuRoundHistory))
        self._rounds.append(tichu_round)

    def last_combination(self):
        return self._current_round.last_combination if self._current_round else None

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
        assert_(all([isinstance(cs, ImmutableCards) for cs in [handcards0, handcards1, handcards2, handcards3]]),
                TypeError("handcards must be ImmutableCards, but were: "+str([type(handcards0), type(handcards1), type(handcards2), type(handcards3)])))
        super().__init__()

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


class TichuGameHistory(namedtuple("TGH", ["team1", "team2", "winner_team", "points", "target_points", "rounds"])):

    def __init__(self, team1, team2, winner_team, points, target_points, rounds):
        assert_(isinstance(team1, Team) and isinstance(team2, Team) and isinstance(winner_team, Team))
        assert_(isinstance(points, tuple) and len(points) == 2)
        assert_(isinstance(target_points, int))
        assert_(all([isinstance(r, TichuRoundHistory) for r in rounds]))
        super().__init__()

    @property
    def points_team1(self):
        return self.points[0]

    @property
    def points_team2(self):
        return self.points[1]

    def last_combination(self):
        return self.rounds[-1].last_combination()


class TrickHandcards(namedtuple("AH", ["trick", "handcards"])):
    """
    Stores an (Trick, HandCardSnapshot) tuple
    """
    def __init__(self, trick, handcards):
        assert_(isinstance(trick, Trick))
        assert_(isinstance(handcards, HandCardSnapshot))
        super().__init__()


class RoundState(object):
    """
    Mutable Round state
    """

    def __init__(self, initial_points):
        assert_(len(initial_points) == 2 and isinstance(initial_points, tuple))

        self._initial_points = initial_points

        # hands
        self._grand_tichu_hands = None  # A HandCardSnapshot
        self._before_swap_hands = None  # A HandCardSnapshot
        self._swaps = None  # tuple of 4 SwapCards instances
        self._complete_hands = None  # A HandCardSnapshot

        # tichus
        self._announced_grand_tichus = set()  # set of player_pos that announced grand tichu
        self._announced_tichus = set()  # set of player_pos that announced normal tichu

        # tricks & actions
        self._tricks_handcards = list()
        self._current_trick = UnfinishedTrick()

        # ranking
        self._ranking = list()

        # points
        self._points = None

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
        assert_(isinstance(points, tuple))
        assert_(len(points) == 2)
        assert_(all([isinstance(p, int) for p in points]))
        self._points = points

    @property
    def grand_tichu_hands(self):
        return self._grand_tichu_hands

    @grand_tichu_hands.setter
    def grand_tichu_hands(self, hands):
        assert_(isinstance(hands, HandCardSnapshot))
        self._grand_tichu_hands = hands

    @property
    def before_swap_hands(self):
        return self._before_swap_hands

    @before_swap_hands.setter
    def before_swap_hands(self, hands):
        assert_(isinstance(hands, HandCardSnapshot))
        self._before_swap_hands = hands

    @property
    def card_swaps(self):
        return self._swaps

    @card_swaps.setter
    def card_swaps(self, swaps):
        assert_(all([isinstance(swap, SwapCards) for swap in swaps]), TypeError("Must be SwapCards, but were: "+str(swaps)))
        self._swaps = swaps

    @property
    def complete_hands(self):
        return self._complete_hands

    @complete_hands.setter
    def complete_hands(self, hands):
        assert_(isinstance(hands, HandCardSnapshot))
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
        if len(self._current_trick) > 0 and len(self._tricks_handcards) > 0:
            last_checkpoint = tuple([Cards(hc) for hc in self._tricks_handcards[-1].handcards])
            for action in self._current_trick:
                if action.is_combination():
                    last_checkpoint[action.player.position].remove(action.combination)
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
    def last_combination(self):
        if len(self._current_trick) == 0:
            return self._tricks_handcards[-1].trick.last_combination() if len(self._tricks_handcards) > 0 else None
        else:
            return self._current_trick.last_combination()

    # ###### Tichus #######
    def announce_grand_tichu(self, player_id):
        self._announced_grand_tichus.add(player_id)

    def announce_tichu(self, player_id):
        if player_id in self._announced_grand_tichus:
            raise IllegalActionException("Player({}) can't announce normal Tichu when already announced grand Tichu.".format(player_id))
        self._announced_tichus.add(player_id)

    # ###### Trick #######
    def finish_trick(self, handcards):
        assert_(isinstance(handcards, HandCardSnapshot))
        self._tricks_handcards.append(TrickHandcards(self._current_trick.finish(), handcards))
        self._current_trick = UnfinishedTrick()

        # ###### Ranking #######

    # ###### Ranking ######
    def ranking_append_player(self, player_pos):
        assert_(player_pos in range(4) and player_pos not in self._ranking)
        self._ranking.append(player_pos)

    def is_double_win(self):
        return len(self._ranking) >= 2 and self._ranking[0] == (self._ranking[1] + 2) % 4

    def rank_of(self, player_pos):
        return self._ranking.index(player_pos) + 1 if player_pos in self._ranking else None

    # ###### Copy & Build #######
    def copy(self, save=False):
        """
        Makes a copy of this instance
        :param save: (default False)
         - an integer (in range(4)) then the copy will only contain information as seen by the player at this position.
         - False, it is a complete copy.

        :return: a copy of this instance
        """

        if (save is not True and save in range(4)) or save is False:
            rs = RoundState(self.initial_points)
            rs._grand_tichu_hands = self.grand_tichu_hands.copy(save=save) if self.grand_tichu_hands else None
            rs._before_swap_hands = self.before_swap_hands.copy(save=save) if self.before_swap_hands else None
            rs._card_swaps = (self._swaps if save is False or self._swaps is None
                              else tuple([(cs if save == i else None) for i, cs in enumerate(self._swaps)]))
            rs._complete_hands = self.complete_hands.copy(save=save) if self.complete_hands else None
            rs._announced_grand_tichus = self.announced_grand_tichus if self.announced_grand_tichus else None
            rs._announced_tichus = self.announced_tichus
            rs._tricks_handcards = [TrickHandcards(trick=t_h.trick, handcards=t_h.handcards.copy(save=save))
                                    for t_h in self._tricks_handcards]
            rs._ranking = self.ranking
            rs._points = self._points
        else:
            raise ValueError("save must be one of [False, 0, 1, 2, 3] but was: "+str(save))

    def build(self):
        return TichuRoundHistory(initial_points=self.initial_points,
                                 final_points=self.final_points,
                                 points=self.points,
                                 grand_tichu_hands=self.grand_tichu_hands,
                                 before_swap_hands=self.before_swap_hands,
                                 card_swaps=self.card_swaps,
                                 complete_hands=self.complete_hands,
                                 announced_grand_tichus=self.announced_grand_tichus,
                                 announced_tichus=self.announced_tichus,
                                 tricks=tuple([t_h.trick for t_h in self._tricks_handcards]),
                                 handcards=tuple([t_h.handcards for t_h in self._tricks_handcards]),
                                 ranking=self.ranking)


class TichuRoundHistory(namedtuple("RoundHistory", ["initial_points", "final_points", "points",
                                                    "grand_tichu_hands", "before_swap_hands",
                                                    "card_swaps", "complete_hands",
                                                    "announced_grand_tichus", "announced_tichus",
                                                    "tricks", "handcards", "ranking"])):

    def __init__(self, initial_points, final_points, points, grand_tichu_hands, before_swap_hands,
                 card_swaps, complete_hands, announced_grand_tichus, announced_tichus, tricks, handcards, ranking):
        assert_(isinstance(initial_points, tuple) and isinstance(final_points, tuple) and isinstance(points, tuple)
                and len(initial_points) == len(final_points) == len(points) == 2)
        assert_(all([isinstance(hds, HandCardSnapshot) for hds in [grand_tichu_hands, before_swap_hands, complete_hands]]))
        assert_(isinstance(card_swaps, tuple))
        assert_(len(card_swaps) == 4)
        assert_(all([isinstance(cs, SwapCards) or cs is None for cs in card_swaps]))
        assert_(isinstance(announced_grand_tichus, set) and isinstance(announced_tichus, set))
        assert_(all([isinstance(t, Trick) for t in tricks]))
        assert_(all([isinstance(hc, HandCardSnapshot) for hc in handcards]))
        assert_(isinstance(ranking, list), len(ranking) <= 4)

        super().__init__()

    def last_combination(self):
        k = len(self.actions) - 1
        ac = self.actions[k]
        while ac.is_pass() and k >= 0:
            k -= 1
            ac = self.actions[k]
        return ac

    def copy(self, save=False):
        """
        Makes a copy of this instance
        :param save: (default False)
         - an integer (in range(4)) then the copy will only contain information as seen by the player at this position.
         - False, it is a complete copy.

        :return: a copy of this instance
        """
        if save is False:
            return TichuRoundHistory(self.initial_points, self.final_points, self.points, self.grand_tichu_hands,
                                     self.before_swap_hands, self.card_swaps, self.complete_hands,
                                     self.announced_grand_tichus, self.announced_tichus, self.tricks, self.handcards, self.ranking)
        else:
            return TichuRoundHistory(self.initial_points, self.final_points, self.points, self.grand_tichu_hands.copy(save=save),
                                     self.before_swap_hands.copy(save=save),
                                     tuple([(cs if save == i else None) for i, cs in enumerate(self.card_swaps)]),
                                     self.complete_hands.copy(save=save), self.announced_grand_tichus, self.announced_tichus, self.tricks,
                                     tuple([hc.copy(save=save) for hc in self.handcards]), self.ranking)

class Trick(object):
    """ List of PlayerActions """

    def __init__(self, actions):
        assert_(all([isinstance(a, PlayerAction) for a in actions]))
        if len(actions) > 0:
            assert_(not actions[0].is_pass())
        self._actions = tuple(actions)

    @property
    def combinations(self):
        return [a.combination for a in self._actions if not a.is_pass()]

    def is_dragon_trick(self):
        return Card.DRAGON in self.last_combination()

    def last_combination(self):
        return self.combinations[-1] if len(self._actions) > 0 else None

    def last_action(self):
        return self._actions[-1] if len(self._actions) > 0 else None

    def sum_points(self):
        return sum([comb.count_points() for comb in self.combinations])

    def copy(self):
        return Trick(self._actions)

    def __len__(self):
        return len(self._actions)

    def __repr__(self):
        return "Trick({})".format(' -> '.join([repr(com) for com in self._actions]))

    def __iter__(self):
        return self._actions.__iter__()


class UnfinishedTrick(Trick):
    """
    Mutable Trick instance
    """

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

        assert_(isinstance(action, PlayerAction), ValueError("action must be a PlayerAction"))
        if check_validity:
            assert_(not (self.is_empty() and action.is_pass()),
                    ValueError("Cant add a pass action on an empty trick. ({}) -> ({})".format(action, self.__repr__())))
            assert_(self.is_empty() or action.can_be_played_on(self.last_combination()),
                    ValueError("Cant play {} on {}.".format(action, self.__repr__())))
        self._actions.append(action)
        return self

    def finish(self):
        """
        :return: An (immutable) Trick
        """
        return Trick(actions=self._actions)


Card_To = namedtuple("Card_To", ["card", "to"])
SwapCard = namedtuple("SwapCard", ["card", "from_", "to"])


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