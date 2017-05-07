from collections import namedtuple, Set, OrderedDict
from typing import Collection, Optional, Union, Iterable, Tuple, Generator

import logging
import itertools
from .actions import pass_actions, tichu_actions, no_tichu_actions, play_dog_actions, all_wish_actions_gen
from .actions import (PlayerAction, PlayCombination, PlayFirst, PlayBomb, TichuAction, WishAction, PassAction,
                      WinTrickAction, GiveDragonAwayAction, CardTrade)
from .cards import CardSet, Card, Trick, CardRank, Deck, DOG_COMBINATION
from .error import TichuEnvValueError, LogicError

__all__ = ('TichuState', )


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


class History(object):

    def __init__(self, _wished: bool=False, _odict=OrderedDict()):
        self._wished: bool = _wished
        self._state_to_action: OrderedDict = _odict

    def wished(self)->bool:
        """
        :return: True iff at some point a wish was made, false otherwise
        """
        return self._wished

    def new_state_action(self, state: 'TichuState', action: PlayerAction)->'History':
        assert isinstance(state, TichuState)
        assert isinstance(action, PlayerAction)
        assert state not in self._state_to_action

        new_dict = OrderedDict(self._state_to_action)
        new_dict[state] = action
        return History(_wished=self._wished or isinstance(action, WishAction), _odict=new_dict)


class TichuState(namedtuple("TichuState", [
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

    def __new__(cls, *args, allow_tichu=True, **kwargs):
        return super().__new__(cls, *args, **kwargs)

    def __init__(self, player_pos: int, handcards: HandCards, won_tricks: WonTricks,
                 trick_on_table: Trick, wish: Optional[CardRank], ranking: tuple,
                 announced_tichu: frozenset, announced_grand_tichu: frozenset,
                 history: History, allow_tichu: bool=True):
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
        self._possible_actions_set = None
        self._possible_actions_tuple = None

    @classmethod
    def initial(cls):
        """
        
        :return: TichuState without any cards distributed yet
        """
        return TichuState(
                player_pos=0,
                handcards=HandCards(),
                won_tricks=WonTricks(),
                trick_on_table=Trick(),
                wish=None,
                ranking=(),
                announced_tichu=frozenset(),
                announced_grand_tichu=frozenset(),
                history=History()
        )

    @classmethod
    def distributed_8_cards(cls, allow_tichu: bool=True):
        """

        :return: TichuState with 8 cards distributed to all 4 players
        """
        piles_of_8 = [p[:8] for p in Deck(full=True).split(nbr_piles=4, random_=True)]
        assert len(piles_of_8) == 4
        assert all(len(p) == 8 for p in piles_of_8)

        handcards = HandCards(*piles_of_8)
        return TichuState(
                player_pos=0,
                handcards=handcards,
                won_tricks=WonTricks(),
                trick_on_table=Trick(),
                wish=None,
                ranking=(),
                announced_tichu=frozenset(),
                announced_grand_tichu=frozenset(),
                history=History(),
                allow_tichu=allow_tichu
        )

    def distribute_14_cards(self)->'TichuState':
        """
        Distributes the remaining cards. 
        :return: 
        :raises: ValueError when not all players have exactly 8 cards. And won_tricks is not empty.
        """
        remaining_cards = set(Deck(full=True)) - set(self.handcards.iter_all_cards())
        piles = Deck(full=False, cards=remaining_cards).split(nbr_piles=4, random_=True)
        assert len(piles) == 4
        assert all(len(p) == 6 for p in piles), str(piles)
        new_handcards = HandCards(*[itertools.chain(crds, piles[k]) for k, crds in enumerate(self.handcards)])
        return self.change(handcards=new_handcards)

    @property
    def _current_player_handcards(self) -> CardSet:
        return self.handcards[self.player_pos]

    @property
    def possible_actions_set(self):
        if self._possible_actions_set is None:
            self._possible_actions_set = frozenset(self.possible_actions())
        return self._possible_actions_set

    def possible_actions(self)->Generator[PlayerAction, None, None]:
        """
        :return: Generator yielding all possible actions in this state
        """
        # tichu? (ie. player just played the first time (next_action keeps the player the same in this case))
        if self._allow_tichu:
            # last acting player has to decide on announcing a tichu
            last_act = self.trick_on_table.last_action
            if isinstance(last_act, PlayCombination) and 14 - len(last_act.combination) == len(self.handcards[last_act.player_pos]):
                yield tichu_actions[last_act.player_pos]
                yield no_tichu_actions[last_act.player_pos]
                return  # player has to decide whether to announce a tichu or not

        # wish?
        if (not self.history.wished()) and (not self.trick_on_table.is_empty()) and Card.MAHJONG in self.trick_on_table.last_combination:
            # Note that self.player_pos is not equal to the wishing player pos.
            yield all_wish_actions_gen(self.trick_on_table.last_combination_action.player_pos)
            return  # Player must wish something, no other actions allowed

        # trick ended?
        if self.trick_on_table.is_finished():
            # dragon away?
            if Card.DRAGON in self.trick_on_table.last_combination:
                yield GiveDragonAwayAction(self.player_pos, (self.player_pos + 1) % 4, trick=self.trick_on_table)
                yield GiveDragonAwayAction(self.player_pos, (self.player_pos - 1) % 4, trick=self.trick_on_table)
            else:
                yield WinTrickAction(player_pos=self.player_pos, trick=self.trick_on_table)
            return  # Player must give the dragon away, no other actions allowed

        # possible combinations and wish fulfilling.
        can_fulfill_wish = False
        # initialise possible combinations ignoring the wish
        possible_combinations = self._current_player_handcards.possible_combinations(played_on=self.trick_on_table.last_combination)
        if self.wish and self._current_player_handcards.contains_cardrank(self.wish):
            # player may have to fulfill the wish
            possible_combinations_wish = list(self._current_player_handcards.possible_combinations(played_on=self.trick_on_table.last_combination, contains_rank=self.wish))
            if len(possible_combinations_wish) > 0:
                # player can and therefore has to fulfill the wish
                can_fulfill_wish = True
                possible_combinations = possible_combinations_wish

        # pass?
        can_pass = not (self.trick_on_table.is_empty() or can_fulfill_wish)
        if can_pass:
            yield pass_actions[self.player_pos]

        # combinations ? -> which combs
        PlayactionClass = PlayFirst if self.trick_on_table.is_empty() else PlayCombination  # Determine FirstPlay or PlayCombination
        for comb in possible_combinations:
            if comb == DOG_COMBINATION:
                yield play_dog_actions[self.player_pos]
            else:
                yield PlayactionClass(player_pos=self.player_pos, combination=comb)

        # TODO bombs ?
        # TODO win trick action ?

    def next_state(self, action: PlayerAction)->'TichuState':
        assert action in self.possible_actions()  # TODO raise illegal move if not?
        # tichu (ie. player just played the first time (next_action keeps the player the same in this case))
        if isinstance(action, TichuAction):
            return self._next_state_on_tichu(action)

        # wish
        if isinstance(action, WishAction):
            return self._next_state_on_wish(action)

        # win trick (includes dragon away)?
        if isinstance(action, WinTrickAction):
            return self._next_state_on_win_trick(action)

        # pass
        if isinstance(action, PassAction):
            return self._next_state_on_pass(action)

        # combinations (includes playfirst, playdog, playbomb)
        if isinstance(action, PlayCombination):
            return self._next_state_on_combination(action)

        raise LogicError("An unknown action has been played")

    def _next_state_on_wish(self, wish_action: WishAction)->'TichuState':
        return self.change(
                wish=wish_action.wish,
                history=self.history.new_state_action(self, wish_action)
        )

    def _next_state_on_tichu(self, tichu_action: TichuAction)->'TichuState':
        # TODO (check allow tichu? probably not)
        h = self.history.new_state_action(self, tichu_action)
        if tichu_action.announce and tichu_action.player_pos not in self.announced_grand_tichu:
            return self.change(
                    announced_tichu=self.announced_tichu.union({tichu_action.player_pos}),
                    history=h
            )
        else:
            return self.change(history=h)

    def _next_state_on_win_trick(self, win_trick_action: WinTrickAction)->'TichuState':
        winner = win_trick_action.player_pos
        assert self.player_pos == winner
        trick_to = winner
        if isinstance(win_trick_action, GiveDragonAwayAction):
            trick_to = win_trick_action.to

        return self.change(
            player_pos=winner,
            won_tricks=self.won_tricks.add_trick(player=trick_to, trick=win_trick_action.trick),
            trick_on_table=Trick(),
            history=self.history.new_state_action(self, win_trick_action)
        )

    def _next_state_on_pass(self, pass_action: PassAction)->'TichuState':
        assert pass_action.player_pos == self.player_pos
        leading_player = self.trick_on_table.last_combination_action.player_pos
        next_player_pos = self._next_player_turn()
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
            next_player_pos = next((ppos % 4 for ppos in range(self.player_pos+2, self.player_pos+3+2)
                                    if len(self.handcards[ppos % 4]) > 0))
            next_trick_on_table = Trick()

        else:
            # next players turn
            next_player_pos = self._next_player_turn()

        # create state
        return self.change(
                player_pos=next_player_pos,
                handcards=next_handcards,
                next_trick_on_table=next_trick_on_table,
                wish=None if played_comb.contains_cardrank(self.wish) else self.wish,
                ranking=next_ranking,
                history=self.history.new_state_action(self, comb_action)
        )

    def _next_player_turn(self) -> int:
        """
        :return: the next player with non empty handcards
        """
        return next((ppos % 4 for ppos in range(self.player_pos + 1, self.player_pos + 4)
                     if len(self.handcards[ppos % 4]) > 0))

    def change(self, **attributes_to_change)->'TichuState':
        """
        
        :param attributes_to_change: kwargs with the name of TichuState Attributes
        :return: A copy ot this TichuState instance with the given attributes replaced
        """
        if len(attributes_to_change) == 0:
            return self

        # TODO speed, maybe?
        return TichuState(*self._replace(**attributes_to_change), allow_tichu=self._allow_tichu)

    def announce_grand_tichus(self, player_positions: Collection)->'TichuState':
        """
        
        :param player_positions: 
        :return: TichuState with the player_positions that announced a grand Tichu.
        """
        assert all(len(hc) == 8 for hc in self.handcards)
        if len(player_positions) == 0:
            return self
        else:
            return self.change(announced_grand_tichu=self.announced_grand_tichu.union(player_positions))

    def announce_tichus(self, player_positions: Collection) -> 'TichuState':
        """

        :param player_positions: 
        :return: TichuState with the player_positions that announced a Tichu.
        """
        player_positions -= self.announced_grand_tichu
        if len(player_positions) == 0:
            return self
        else:
            return self.change(announced_tichu=self.announced_tichu.union(player_positions))

    def trade_cards(self, trades: Collection[CardTrade])->'TichuState':
        """
        
        :param trades: must have length of 4*3 = 12 and contain only legal trades
        :return: The state after the given cards have been traded.
        """
        assert len(trades) == 4*3
        new_handcards = self.handcards.as_list_of_lists()
        for from_, to, card in trades:
            assert card in new_handcards[from_]
            new_handcards[from_].remove(card)
            assert card not in new_handcards[from_]
            new_handcards[to].append(card)
            assert card in new_handcards[to]

        return self.change(handcards=HandCards(*new_handcards))

    def has_cards(self, player: int, cards: Collection[Card])->bool:
        """
        
        :param player: 
        :param cards: 
        :return: True if the player has the given card, False otherwise
        """
        return self.handcards.has_cards(player=player, cards=cards)

    def is_terminal(self):
        return len(self.ranking) >= 3 or self.is_double_win()

    def is_double_win(self)->bool:
        return len(self.ranking) >= 2 and self.ranking[0] == (self.ranking[1] + 2) % 4

    def count_points(self) -> tuple:
        """
        Only correct if the state is terminal
        :return: tuple of length 4 with the points of each player at the corresponding index.
        """
        # TODO Test

        if not self.is_terminal():
            logging.warning("Calculating points of a NON terminal state! Result may be incorrect.")

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
            # double win (200 for winner team, -200 for loosers)
            points[final_ranking[0]] += 100
            points[final_ranking[1]] += 100
            points[final_ranking[2]] -= 100
            points[final_ranking[3]] -= 100
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
        assert points[0] == points[2] and points[1] == points[3], str(points)
        return tuple(points)

    def __str__(self):
        return (
        """
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

