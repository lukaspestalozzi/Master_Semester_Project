import abc
from collections import namedtuple, OrderedDict
from typing import Collection, Optional, Union, Iterable, Tuple, Generator, Set, Dict, List, Any


from profilehooks import timecall

import logging
import itertools
import random

from .actions import pass_actions, tichu_actions, no_tichu_actions, play_dog_actions, all_wish_actions_gen, TradeAction
from .actions import (PlayerAction, PlayCombination, PlayFirst, PlayBomb, TichuAction, WishAction, PassAction,
                      WinTrickAction, GiveDragonAwayAction, CardTrade, Trick)
from .cards import CardSet, Card, CardRank, Deck, DOG_COMBINATION
from .error import TichuEnvValueError, LogicError, IllegalActionError
from .utils import check_param, check_isinstance, check_all_isinstance, check_true

__all__ = ('TichuState', 'HandCards', 'History', 'BaseTichuState',
           'InitialState', 'FullCardsState', 'BeforeTrading', 'AfterTrading')

logger = logging.getLogger(__name__)


class HandCards(object):

    def __init__(self, cards0: Iterable=(), cards1: Iterable=(), cards2: Iterable=(), cards3: Iterable=()):
        self._cards: Tuple[CardSet, CardSet, CardSet, CardSet] = (CardSet(cards0),
                                                                  CardSet(cards1),
                                                                  CardSet(cards2),
                                                                  CardSet(cards3))

    def has_cards(self, player: int, cards: Union[Collection[Card], Card]):
        assert player in range(4)
        try:
            res = set(cards).issubset(self._cards[player])
            assert all(isinstance(c, Card) for c in cards)
            return res
        except TypeError:
            # cards is only 1 single card
            assert isinstance(cards, Card)
            return cards in self._cards[player]

    def remove_cards(self, player: int, cards: Collection[Card], raise_on_uncomplete=True):
        """
        :param player: 
        :param cards: 
        :param raise_on_uncomplete: If True, Raises an ValueError when the player does not have all the cards
        :return: 
        
        >>> hc = HandCards((Card.DOG, Card.TWO_HOUSE), (Card.PHOENIX, Card.DRAGON), (Card.FIVE_HOUSE,), (Card.SIX_HOUSE,))
        >>> hc.remove_cards(0, (Card.DOG,))
        
        """
        # make sure cards is a set
        if not isinstance(cards, Set):
            cards = set(cards)

        assert all(isinstance(c, Card) for c in cards)
        new_cards = list((c for c in self._cards[player] if c not in cards))

        if raise_on_uncomplete and len(new_cards) + len(cards) != len(self._cards[player]):
            raise TichuEnvValueError("Not all cards can be removed.")

        return HandCards(
                *[new_cards if player == k else self._cards[k] for k in range(4)]
        )

    def iter_all_cards(self, player: int=None):
        """
        :param player: If specified, iterates only over the cards of this player. 
        :return: Iterator over all single cards in all hands if 'player' is not specified
        """
        if player is None:
            return itertools.chain(*self._cards)
        else:
            return iter(self._cards[player])

    def as_list_of_lists(self):
        return [list(cards) for cards in self._cards]

    def __iter__(self):
        return self._cards.__iter__()

    def __getitem__(self, item):
        return self._cards[item]

    def __hash__(self):
        return hash(self._cards)

    def __eq__(self, other):
        return (other.__class__ == self.__class__
                and all(sc == oc for sc, oc in itertools.zip_longest(self.iter_all_cards(),
                                                                     other.iter_all_cards())))

    def __str__(self):
        return(
        """
            0: {}
            1: {}
            2: {}
            3: {}
        """
        ).format(*[str(crds) for crds in self._cards])


class WonTricks(object):

    def __init__(self, tricks0: Iterable[Trick]=(), tricks1: Iterable[Trick]=(), tricks2: Iterable[Trick]=(), tricks3: Iterable[Trick]=()):
        self._tricks: Tuple[Tuple[Trick, ...]] = (tuple(tricks0), tuple(tricks1), tuple(tricks2), tuple(tricks3))
        assert all(isinstance(t, Trick) for t in itertools.chain(*self._tricks))

    def add_trick(self, player: int, trick: Trick):
        """
        :param player: 
        :param trick: 
        :return: New WonTrick instance with the trick appended to the players won tricks
        """
        return WonTricks(*[(tricks + (trick,) if k == player else tricks) for k, tricks in enumerate(self._tricks)])

    def iter_all_tricks(self, player: int=None):
        """
        :param player: If specified, iterates only over the tricks won by this player. 
        :return: Iterator over all tricks that have been won if 'player' is not specified.
        """
        if player is None:
            return itertools.chain(*self._tricks)
        else:
            iter(self._tricks[player])

    def __iter__(self):
        return self._tricks.__iter__()

    def __getitem__(self, item):
        return self._tricks.__getitem__(item)

    def __hash__(self):
        return hash(self._tricks)

    def __eq__(self, other):
        return (other.__class__ == self.__class__
                and all(st == ot for st, ot in itertools.zip_longest(self.iter_all_tricks(),
                                                                     other.iter_all_tricks())))

    def __str__(self):
        return (
        """
            0 won {} tricks
            1 won {} tricks
            2 won {} tricks
            3 won {} tricks
        """
        ).format(*[str(len(wt)) for wt in self._tricks])


class History(object):

    def __init__(self, _wished: bool=False, _tup=tuple()):
        self._wished: bool = _wished
        self._state_action_tuple: Tuple[Union[TichuState, PlayerAction]] = _tup

    def last_state(self)->Optional['BaseTichuState']:
        for elem in reversed(self._state_action_tuple):
            if isinstance(elem, BaseTichuState):
                return elem
        return None

    def wished(self)->bool:
        """
        :return: True iff at some point a wish was made, false otherwise
        """
        return self._wished

    def new_state_actions(self, state: 'BaseTichuState', actions: Iterable[PlayerAction])->'History':
        """
        
        :param state: 
        :param actions: 
        :return: copy of this History instance with the state and actions appended to it.
        """
        actions = tuple(actions)
        assert isinstance(state, BaseTichuState)
        assert all(isinstance(action, PlayerAction) for action in actions)
        _wished = self._wished or any(isinstance(action, WishAction) for action in actions)
        return History(_wished=_wished, _tup=self._state_action_tuple + (state, *actions))

    def new_state_action(self, state: 'BaseTichuState', action: PlayerAction)->'History':
        """
        
        :param state: 
        :param action: 
        :return: copy of this History instance with the state and action appended to it.
        """
        assert isinstance(state, TichuState)
        assert isinstance(action, PlayerAction)

        new_tuple = self._state_action_tuple + (state, action)
        return History(_wished=self._wished or isinstance(action, WishAction), _tup=new_tuple)

    def add_last_state(self, state: 'BaseTichuState'):
        assert isinstance(state, TichuState)
        new_tuple = self._state_action_tuple + (state, )
        return History(_wished=self._wished, _tup=new_tuple)

    def actions(self):
        yield from (a for a in self._state_action_tuple if isinstance(a, PlayerAction))

    def __repr__(self):
        return "{me.__class__.__name__}(length: {l})".format(me=self, l=len(self._state_action_tuple))

    def __str__(self):
        last_state = self.last_state()
        try:
            ranking = last_state.ranking
        except AttributeError:
            ranking = "No ranking"
        try:
            points = last_state.count_points() if last_state.is_terminal() else "State is not Terminal"
        except AttributeError:
            points = "No points"

        actions = list(self.actions())
        actions_str = "    " if len(actions) else "EMPTY"
        for action in actions:
            actions_str += " -> "+str(action)
            if isinstance(action, WinTrickAction):
                actions_str += "\n    "
        return (
"""
{me.__class__.__name__}
length: {length}
last ranking: {ranking}
last points: {points}
actions: 
{actions}        
""".format(me=self, length=len(self._state_action_tuple), ranking=ranking, points=points,
           actions=actions_str)
        )


class BaseTichuState(object, metaclass=abc.ABCMeta):

    
    @abc.abstractmethod
    def next_state(self, action: Any)->'BaseTichuState':
        """
        
        :param action: 
        :return: The next state for this action
        """
        pass

    @abc.abstractmethod
    def is_terminal(self):
        """
        
        :return: True iff the state is terminal. False otherwise
        """


class TichuState(BaseTichuState, namedtuple("TichuState", [
            "player_pos",
            "handcards",
            "won_tricks",
            "trick_on_table",
            "wish",
            "ranking",
            "announced_tichu",
            "announced_grand_tichu",
            "history"
        ])):

    def __new__(cls, *args, allow_tichu=True, allow_wish=True, **kwargs):
        return super().__new__(cls, *args, **kwargs)

    def __init__(self, player_pos: int, handcards: HandCards, won_tricks: WonTricks,
                 trick_on_table: Trick, wish: Optional[CardRank], ranking: tuple,
                 announced_tichu: frozenset, announced_grand_tichu: frozenset,
                 history: History, allow_tichu: bool=True, allow_wish: bool=True):
        super().__init__()

        # some paranoid checks
        assert player_pos in range(4)
        assert isinstance(handcards, HandCards)

        assert isinstance(won_tricks, WonTricks)

        assert wish is None or isinstance(wish, CardRank)

        assert isinstance(ranking, tuple)
        assert all(r in range(4) for r in ranking)

        assert isinstance(announced_tichu, frozenset)
        assert isinstance(announced_grand_tichu, frozenset)
        assert all(r in range(4) for r in announced_tichu)
        assert all(r in range(4) for r in announced_grand_tichu)

        assert isinstance(trick_on_table, Trick)
        assert isinstance(history, History)

        self._allow_tichu = allow_tichu
        self._allow_wish = allow_wish
        self._possible_actions_set: Set[PlayerAction] = None
        self._possible_actions_list: List[PlayerAction] = None
        self._state_transitions: Dict[PlayerAction, TichuState] = dict()

    @property
    def _current_player_handcards(self) -> CardSet:
        return self.handcards[self.player_pos]

    @timecall(immediate=False)
    def __init_possible_actions_list_and_set(self):
        self._possible_actions_list = list(self.possible_actions_gen())
        self._possible_actions_set = frozenset(self._possible_actions_list)

    @property
    def possible_actions_set(self)->Set[PlayerAction]:
        if self._possible_actions_set is None or self._possible_actions_list is None:
            self.__init_possible_actions_list_and_set()
        return self._possible_actions_set

    @property
    def possible_actions_list(self)->List[PlayerAction]:
        if self._possible_actions_set is None or self._possible_actions_list is None:
            self.__init_possible_actions_list_and_set()
        return self._possible_actions_list

    def possible_actions(self)->Set[PlayerAction]:
        return self.possible_actions_set

    def possible_actions_gen(self)->Generator[PlayerAction, None, None]:
        """
        :return: Generator yielding all possible actions in this state
        """

        # ######### tichu? ######### (ie. player just played the first time (next_action keeps the player the same in this case))
        if self._allow_tichu:
            # last acting player has to decide on announcing a tichu
            last_act = self.trick_on_table.last_action
            if (isinstance(last_act, PlayCombination)
                    and last_act.player_pos not in self.announced_tichu
                    and last_act.player_pos not in self.announced_grand_tichu
                    and 14 - len(last_act.combination) == len(self.handcards[last_act.player_pos])):
                yield tichu_actions[last_act.player_pos]
                yield no_tichu_actions[last_act.player_pos]
                return  # player has to decide whether to announce a tichu or not

        # ######### Round Ends with double win? #########
        if self.is_double_win():
            assert self.is_terminal()  # -> No action possible
            return

        # store last played combination (action)
        last_combination_action = self.trick_on_table.last_combination_action
        last_combination = self.trick_on_table.last_combination

        # ######### Round ends with the 3rd player finishing? #########
        if len(self.ranking) >= 3:  # Round ends -> terminal
            if self.trick_on_table.is_empty():
                assert self.is_terminal()  # -> No action possible
                return
            else:
                # give the remaining trick on table to leader
                yield WinTrickAction(player_pos=last_combination_action.player_pos, trick=self.trick_on_table)
            return  # Round ends

        # ######### wish? #########
        if (self._allow_wish and not self.history.wished()) and (not self.trick_on_table.is_empty()) and Card.MAHJONG in last_combination:
            # Note that self.player_pos is not equal to the wishing player pos.
            yield from all_wish_actions_gen(self.trick_on_table.last_combination_action.player_pos)
            return  # Player must wish something, no other actions allowed

        # ######### trick ended? #########
        if self.trick_on_table.is_finished():
            # dragon away?
            if Card.DRAGON in last_combination:
                yield GiveDragonAwayAction(self.player_pos, (self.player_pos + 1) % 4, trick=self.trick_on_table)
                yield GiveDragonAwayAction(self.player_pos, (self.player_pos - 1) % 4, trick=self.trick_on_table)
            # Normal Trick
            else:
                yield WinTrickAction(player_pos=self.player_pos, trick=self.trick_on_table)
            return  # No more actions allowed

        # ######### DOG? #########
        if DOG_COMBINATION == last_combination:  # Dog was played
            # logger.debug("Dog was played -> Win trick action")
            yield WinTrickAction(player_pos=(last_combination_action.player_pos + 2) % 4, trick=self.trick_on_table)
            return  # No more actions allowed

        # ######### possible combinations and wish fulfilling. #########
        can_fulfill_wish = False
        # initialise possible combinations ignoring the wish
        possible_combinations = list(self._current_player_handcards.possible_combinations(played_on=last_combination))
        if self.wish and self._current_player_handcards.contains_cardrank(self.wish):
            # player may have to fulfill the wish
            possible_combinations_wish = list(self._current_player_handcards.possible_combinations(played_on=last_combination, contains_rank=self.wish))
            if len(possible_combinations_wish) > 0:
                # player can and therefore has to fulfill the wish
                can_fulfill_wish = True
                possible_combinations = possible_combinations_wish

        # ######### pass? #########
        can_pass = not (self.trick_on_table.is_empty() or can_fulfill_wish)
        if can_pass:
            yield pass_actions[self.player_pos]

        # ######### combinations ? #########  -> which combs
        PlayactionClass = PlayFirst if self.trick_on_table.is_empty() else PlayCombination  # Determine FirstPlay or PlayCombination
        for comb in possible_combinations:
            if comb == DOG_COMBINATION:
                yield play_dog_actions[self.player_pos]
            else:
                yield PlayactionClass(player_pos=self.player_pos, combination=comb)

        # TODO bombs ?

    @timecall(immediate=False)
    def next_state(self, action: PlayerAction)->'TichuState':
        if action not in self.possible_actions():
            raise IllegalActionError("{} is not a legal action in state: {}".format(action, self))

        # cache the state transitions
        if action in self._state_transitions:
            return self._state_transitions[action]

        # tichu (ie. player just played the first time (next_action keeps the player the same in this case))
        elif isinstance(action, TichuAction):
            next_s = self._next_state_on_tichu(action)

        # wish
        elif isinstance(action, WishAction):
            next_s = self._next_state_on_wish(action)

        # win trick (includes dragon away)?
        elif isinstance(action, WinTrickAction):
            next_s = self._next_state_on_win_trick(action)

        # pass
        elif isinstance(action, PassAction):
            next_s = self._next_state_on_pass(action)

        # combinations (includes playfirst, playdog, playbomb)
        elif isinstance(action, PlayCombination):
            next_s = self._next_state_on_combination(action)
        else:
            raise LogicError("An unknown action has been played")

        self._state_transitions[action] = next_s
        return next_s

    @timecall(immediate=False)
    def random_action(self)->PlayerAction:
        return random.choice(self.possible_actions_list)

    @timecall(immediate=False)
    def _next_state_on_wish(self, wish_action: WishAction)->'TichuState':
        return self.change(
                wish=wish_action.wish,
                trick_on_table=self.trick_on_table + wish_action,
                history=self.history.new_state_action(self, wish_action)
        )

    @timecall(immediate=False)
    def _next_state_on_tichu(self, tichu_action: TichuAction)->'TichuState':
        h = self.history.new_state_action(self, tichu_action)
        tot = self.trick_on_table + tichu_action
        if DOG_COMBINATION == self.trick_on_table.last_combination:
            tot = tot.finish()
        if tichu_action.announce:
            assert tichu_action.player_pos not in self.announced_grand_tichu
            return self.change(
                    announced_tichu=self.announced_tichu.union({tichu_action.player_pos}),
                    trick_on_table=tot,
                    history=h
            )
        else:
            return self.change(
                    trick_on_table=tot,
                    history=h
            )

    @timecall(immediate=False)
    def _next_state_on_win_trick(self, win_trick_action: WinTrickAction)->'TichuState':
        winner = win_trick_action.player_pos
        assert self.player_pos == winner or len(self.ranking) >= 3, "action: {act}, winner:{winner}, state:{state}".format(act=win_trick_action, winner=winner, state=self)

        # give trick to correct player
        trick_to = winner
        if isinstance(win_trick_action, GiveDragonAwayAction):
            trick_to = win_trick_action.to

        # determine next player
        try:
            next_player = winner if len(self.handcards[winner]) else self._next_player_turn()
        except StopIteration:
            # happens only right before the game ends
            next_player = winner
            assert self.is_double_win() or len(self.ranking) >= 3
        return self.change(
            player_pos=next_player,
            won_tricks=self.won_tricks.add_trick(player=trick_to, trick=win_trick_action.trick),
            trick_on_table=Trick(),
            history=self.history.new_state_action(self, win_trick_action)
        )

    @timecall(immediate=False)
    def _next_state_on_pass(self, pass_action: PassAction)->'TichuState':
        assert pass_action.player_pos == self.player_pos
        leading_player = self.trick_on_table.last_combination_action.player_pos
        # try:
        next_player_pos = self._next_player_turn()
        # except StopIteration:
        #     # happens only right before the game ends
        #     next_player_pos = leading_player
        if (leading_player == next_player_pos
                or self.player_pos < leading_player < next_player_pos
                or next_player_pos < self.player_pos < leading_player
                or leading_player < next_player_pos < self.player_pos):
            # trick ends with leading as winner
            return self.change(
                    player_pos=leading_player,
                    trick_on_table=self.trick_on_table.finish(last_action=pass_action),
                    history=self.history.new_state_action(self, pass_action)
            )
        else:
            return self.change(
                    player_pos=next_player_pos,
                    trick_on_table=self.trick_on_table + pass_action,
                    history=self.history.new_state_action(self, pass_action)
            )

    @timecall(immediate=False)
    def _next_state_on_combination(self, comb_action: PlayCombination)->'TichuState':
        played_comb = comb_action.combination
        assert comb_action.player_pos == self.player_pos

        # remove from handcards and add to trick on table
        next_trick_on_table = self.trick_on_table + comb_action
        next_handcards = self.handcards.remove_cards(player=self.player_pos, cards=played_comb.cards)

        assert len(next_handcards[self.player_pos]) < len(self.handcards[self.player_pos])
        assert next_handcards[self.player_pos].issubset(self.handcards[self.player_pos])

        # ranking
        next_ranking = self.ranking
        if len(next_handcards[self.player_pos]) == 0:
            # player finished
            next_ranking = self.ranking + (self.player_pos,)
            assert self.player_pos not in self.ranking
            assert len(self.ranking) == len(set(self.ranking))

        # dog
        if played_comb == DOG_COMBINATION:
            assert self.trick_on_table.is_empty()
            next_player_pos = (self.player_pos+2) % 4  # Teammate

        else:
            # next players turn
            # try:
            next_player_pos = self._next_player_turn()
            # except StopIteration:
            #     # happens only right before the game ends
            #     next_player_pos = (comb_action.player_pos + 1) % 4

        # create state
        return self.change(
                player_pos=next_player_pos,
                handcards=next_handcards,
                trick_on_table=next_trick_on_table,
                wish=None if played_comb.contains_cardrank(self.wish) else self.wish,
                ranking=next_ranking,
                history=self.history.new_state_action(self, comb_action)
        )

    def _next_player_turn(self) -> int:
        """
        :return: the next player with non empty handcards
        """

        return next((ppos % 4 for ppos in range(self.player_pos + 1, self.player_pos + 4) if len(self.handcards[ppos % 4]) > 0))

    @timecall(immediate=False)
    def change(self, **attributes_to_change)->'TichuState':
        """
        
        :param attributes_to_change: kwargs with the name of TichuState Attributes
        :return: A copy ot this TichuState instance with the given attributes replaced
        """
        if len(attributes_to_change) == 0:
            return self

        return TichuState(*self._replace(**attributes_to_change), allow_tichu=self._allow_tichu, allow_wish=self._allow_wish)

    def has_cards(self, player: int, cards: Collection[Card])->bool:
        """
        
        :param player: 
        :param cards: 
        :return: True if the player has the given card, False otherwise
        """
        return self.handcards.has_cards(player=player, cards=cards)

    def is_terminal(self):
        return self.is_double_win() or (self.trick_on_table.is_empty() and len(self.ranking) >= 3)

    def is_double_win(self)->bool:
        return len(self.ranking) >= 2 and self.ranking[0] == (self.ranking[1] + 2) % 4

    def count_points(self) -> Tuple[int, int, int, int]:
        """
        Only correct if the state is terminal
        :return: tuple of length 4 with the points of each player at the corresponding index.
        """
        # TODO Test

        if not self.is_terminal():
            logger.warning("Calculating points of a NON terminal state! Result may be incorrect.")

        # calculate tichu points
        tichu_points = [0, 0, 0, 0]
        for gt_pos in self.announced_grand_tichu:
            tichu_points[gt_pos] += 200 if gt_pos == self.ranking[0] else -200
        for t_pos in self.announced_tichu:
            tichu_points[t_pos] += 100 if t_pos == self.ranking[0] else -100
        points = tichu_points

        # fill the ranking to 4
        final_ranking = list(self.ranking) + [ppos for ppos in range(4) if ppos not in self.ranking]
        assert len(final_ranking) == 4, "{} -> {}".format(self.ranking, final_ranking)

        if self.is_double_win():
            # double win (200 for winner team)
            points[final_ranking[0]] += 100
            points[final_ranking[1]] += 100
        else:
            # not double win
            for rank in range(3):  # first 3 players get the points in their won tricks
                player_pos = final_ranking[rank]
                points[player_pos] += sum(t.points for t in self.won_tricks[player_pos])

            # first player gets the points of the last players tricks
            winner = final_ranking[0]
            looser = final_ranking[3]
            points[winner] += sum(t.points for t in self.won_tricks[looser])

            # the handcards of the last player go to the enemy team
            points[(looser + 1) % 4] += sum(t.points for t in self.handcards[looser])
        # fi

        # sum the points of each team
        t1 = points[0] + points[2]
        t2 = points[1] + points[3]
        points[0] = t1
        points[2] = t1
        points[1] = t2
        points[3] = t2

        assert len(points) == 4
        assert points[0] == points[2] and points[1] == points[3]

        return tuple(points)

    def __str__(self):
        return (
        """
        {me.__class__.__name__}
        player: {me.player_pos}
        handcards: {me.handcards}
        won tricks: {me.won_tricks}
        trick on table: {me.trick_on_table}
        wish: {me.wish}
        ranking: {me.ranking}
        tichus: {me.announced_tichu}
        grand tichus: {me.announced_grand_tichu}
        history: {me.history}
        """).format(me=self)


class InitialState(BaseTichuState):
    """
    State where all players have 8 cards (before announcing their grand tichus)
    """
    def __init__(self):  # TODO maybe add possibility to predetermine the handcards
        piles_of_8 = [p[:8] for p in Deck(full=True).split(nbr_piles=4, random_=True)]
        assert len(piles_of_8) == 4
        assert all(len(p) == 8 for p in piles_of_8)

        self.handcards = HandCards(*piles_of_8)
        self.history = History()

    def next_state(self, players: Iterable[int]) -> 'FullCardsState':
        players = frozenset(players)
        check_param(all(p in range(4) for p in players), msg="[InitialState.next_state]: All players must be in range(4).")
        return self.announce_grand_tichus(players)

    def announce_grand_tichus(self, players: Iterable[int])->'FullCardsState':
        return FullCardsState(self, players)

    def is_terminal(self):
        return False


class FullCardsState(BaseTichuState):
    """
    State where the players have 14 cards and announced their grand tichus.
    All players may announce a Tichu now
    """
    def __init__(self, initial_state: InitialState, players_announced_grand_tichu: Iterable[int]):
        players_announced_grand_tichu = frozenset(players_announced_grand_tichu)
        check_param(all(i in range(4) for i in players_announced_grand_tichu))

        remaining_cards = set(Deck(full=True)) - set(initial_state.handcards.iter_all_cards())
        piles = Deck(full=False, cards=remaining_cards).split(nbr_piles=4, random_=True)
        assert len(piles) == 4
        assert all(len(p) == 6 for p in piles), str(piles)

        self.handcards = HandCards(*(itertools.chain(crds, piles[k]) for k, crds in enumerate(initial_state.handcards)))
        self.announced_grand_tichu = players_announced_grand_tichu
        self.history = initial_state.history.new_state_actions(initial_state, (TichuAction(pp, announce_tichu=pp in players_announced_grand_tichu, grand=True) for pp in range(4)))

    def next_state(self, players: Iterable[int]) -> 'BeforeTrading':
        players = frozenset(players)
        check_param(all(p in range(4) for p in players), msg="[FullCardsState.next_state]: All players must be in range(4).")
        return self.announce_tichus(players)

    def announce_tichus(self, players: Iterable[int])->'BeforeTrading':
        return BeforeTrading(self, players)

    def is_terminal(self):
        return False


class BeforeTrading(BaseTichuState):
    """
    In this state all players have to trade 3 cards.
    """

    def __init__(self, prev_state: FullCardsState, players_announced_tichu: Iterable[int]):
        players_announced_tichu = frozenset(players_announced_tichu)
        check_param(all(i in range(4) for i in players_announced_tichu))
        check_isinstance(prev_state, FullCardsState)

        self.handcards = prev_state.handcards
        self.announced_grand_tichu = prev_state.announced_grand_tichu
        self.announced_tichu = players_announced_tichu
        self.history = prev_state.history.new_state_actions(prev_state, (TichuAction(pp, announce_tichu=pp in players_announced_tichu) for pp in range(4)))

    def next_state(self, trades: Collection[CardTrade]) -> 'AfterTrading':
        check_all_isinstance(trades, CardTrade)
        return self.trade_cards(trades)

    def trade_cards(self, trades: Collection[CardTrade]) -> 'AfterTrading':
        """
        Same as: AfterTrading.from_beforetrading(<this BeforeTrading instance>, trades=trades)

        :param trades: must have length of 4*3 = 12 and contain only legal trades
        :return: The state after the given cards have been traded.
        """
        return AfterTrading.from_beforetrading(self, trades=trades)

    def is_terminal(self):
        return False


class AfterTrading(TichuState):
    """
    All players have 14 cards and have already traded. From this state on the Round starts with the player having the MAHJONG. 
    
    This is a 
    """

    def __init__(self, *args, **kwargs):
        check_true(Card.MAHJONG in self.handcards[self.player_pos])
        check_true(all(len(hc) == 14 for hc in self.handcards))
        super().__init__(*args, **kwargs)

    @classmethod
    def from_beforetrading(cls, before_trading: BeforeTrading, trades: Collection[CardTrade]) -> 'AfterTrading':
        assert len(trades) == 0 or len(trades) == 12  # 4 players trade 3 cards each, an empty trades collection bypasses the trading phase

        new_handcards = before_trading.handcards.as_list_of_lists()
        trade_actions = []
        for from_, to, card in trades:
            trade_actions.append(TradeAction(from_=from_, to=to, card=card))
            assert card in new_handcards[from_]
            new_handcards[from_].remove(card)
            assert card not in new_handcards[from_]
            new_handcards[to].append(card)
            assert card in new_handcards[to]

        try:
            starting_player = next((ppos for ppos, hc in enumerate(new_handcards) if Card.MAHJONG in hc))
        except StopIteration as se:
            raise LogicError("No player seems to have the MAHJONG.") from se
        else:
            return cls(
                    player_pos=starting_player,
                    handcards=HandCards(*new_handcards),
                    won_tricks=WonTricks(),
                    trick_on_table=Trick(),
                    wish=None,
                    ranking=(),
                    announced_tichu=before_trading.announced_tichu,
                    announced_grand_tichu=before_trading.announced_grand_tichu,
                    history=before_trading.history.new_state_actions(before_trading, trade_actions),
                    allow_tichu=True
            )

    def is_terminal(self):
        return False


class MutableTichuState(object):
    pass
