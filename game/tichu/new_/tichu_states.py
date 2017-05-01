import random
from collections import Generator, namedtuple

import logging

import itertools
from typing import Tuple

from game.abstract import GameInfoSet, GameState
from game.tichu.cards import Card, CardValue
from game.tichu.exceptions import IllegalActionException
from game.tichu.handcardsnapshot import HandCardSnapshot
from game.tichu.tichu_actions import TichuAction, CombinationAction, PassAction, PlayerAction, PlayerGameEvent, \
    SimpleWinTrickEvent
from game.tichu.trick import Trick
from game.utils import flatten, check_param


class TichuState(GameState, namedtuple("S", [
            "player_id",
            "hand_cards",
            "won_tricks",
            "trick_on_table",
            "wish",
            "ranking",
            "announced_tichu",
            "announced_grand_tichu",
            "history"
        ])):
    def __init__(self, player_id: int, hand_cards: HandCardSnapshot, won_tricks: tuple,
                 trick_on_table: Trick, wish: CardValue, ranking: tuple,
                 announced_tichu: frozenset, announced_grand_tichu: frozenset,
                 history: Tuple[PlayerGameEvent]):
        super().__init__()

        # some paranoid checks
        assert player_id in range(4)
        assert isinstance(hand_cards, HandCardSnapshot)

        assert isinstance(won_tricks, tuple)
        assert all(isinstance(tricks, tuple) for tricks in won_tricks)
        assert all(all(isinstance(t, Trick) for t in tricks) for tricks in won_tricks)

        assert wish is None or isinstance(wish, CardValue)

        assert isinstance(ranking, tuple)
        assert all(r in range(4) for r in ranking)

        assert isinstance(announced_tichu, frozenset)
        assert isinstance(announced_grand_tichu, frozenset)
        assert all(r in range(4) for r in announced_tichu)
        assert all(r in range(4) for r in announced_grand_tichu)

        assert isinstance(trick_on_table, Trick)
        assert isinstance(history, tuple)
        assert all(isinstance(a, PlayerGameEvent) for a in history)

        self._action_state_transitions = dict()
        self._possible_actions = None
        self._satisfy_wish = None
        self._can_pass = None
        self._possible_combs = None
        self._possible_combinations()  # init possible combs

        self._infosets_ids = [None]*4

    def current_player_id(self) -> int:
        return self.player_id

    def next_state(self, action: TichuAction):
        """
        
        :param action: 
        :return: 
        """
        if action.player_pos != self.player_id:
            raise IllegalActionException(f"Only player:{self.player_id} can play in this case, but action was: {action}")
        if action in self._action_state_transitions:
            return self._action_state_transitions[action]

        if isinstance(action, PassAction):
            new_state = self._state_for_pass()

        elif isinstance(action, CombinationAction):
            assert action.combination.can_be_played_on(self.trick_on_table.last_combination), f'comb: {action.combination}, last_comb: {self.trick_on_table.last_combination}'
            new_state = self._state_for_combination_action(action)
        else:
            raise ValueError("action must be PassActon or a CombinationAction")
        self._action_state_transitions[action] = new_state
        return new_state

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
            points[(looser + 1) % 4] += sum(t.points for t in self.hand_cards[looser])
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

    def evaluate(self) -> tuple:
        return self.count_points()

    def is_terminal(self) -> bool:
        return len(self.ranking) >= 3 or self.is_double_win()

    def is_double_win(self)->bool:
        return len(self.ranking) >= 2 and self.ranking[0] == (self.ranking[1] + 2) % 4

    def possible_actions(self) -> frozenset:
        if self._possible_actions is not None:
            return frozenset(self._possible_actions)
        poss_combs, _ = self._possible_combinations()
        poss_acs = {CombinationAction(player_pos=self.player_id, combination=comb) for comb in poss_combs}
        if self._can_pass:
            poss_acs.add(PassAction(self.player_id))

        self._possible_actions = frozenset(poss_acs)
        return frozenset(poss_acs)

    def possible_actions_gen(self) -> Generator:
        yield from self.possible_actions()

    def random_action(self) -> TichuAction:
        """
        
        :return: A random legal action from this state
        """
        return random.choice(list(self.possible_actions()))

    def _possible_combinations(self) -> tuple:
        """
        :return: a tuple of the possible combinations and whether the combinations satisfy the wish
        """
        if self._possible_combs is not None:
            # return already calculated combinations
            return (frozenset(self._possible_combs), self._satisfy_wish)
        comb_on_table = self.trick_on_table.last_combination
        possible_combs = set(self.hand_cards[self.player_id].all_combinations(played_on=comb_on_table))
        # verify wish
        self._satisfy_wish = False
        if self.wish and self.wish in (c.card_value for c in self.hand_cards[self.player_id]):
            pcombs = [comb for comb in possible_combs if comb.contains_cardval(self.wish)]
            if len(pcombs):
                self._satisfy_wish = True
                possible_combs = pcombs
        self._possible_combs = frozenset(possible_combs)
        self._can_pass = self.trick_on_table.last_combination is not None and not self._satisfy_wish
        return (frozenset(possible_combs), self._satisfy_wish)

    def next_player_turn(self) -> int:
        return next((ppos % 4 for ppos in range(self.player_id + 1, self.player_id + 4) if len(self.hand_cards[ppos % 4]) > 0))

    def _state_for_combination_action(self, combination_action: CombinationAction):
        comb = combination_action.combination
        new_trick_on_table = self.trick_on_table.add_combination_action(combination_action)
        new_handcards = self.hand_cards.remove_cards(from_pos=self.player_id, cards=comb.cards)
        assert len(new_handcards[self.player_id]) < len(self.hand_cards[self.player_id])
        assert new_handcards[self.player_id].issubset(self.hand_cards[self.player_id])

        # ranking:
        new_ranking = list(self.ranking)
        if len(new_handcards[self.player_id]) == 0:
            new_ranking.append(self.player_id)
            assert len(set(new_ranking)) == len(new_ranking), "state:{}\ncomb:{}".format(self, comb)

        # handle dog
        next_player_pos = self.next_player_turn()
        if Card.DOG in comb:
            next_player_pos = next((ppos % 4 for ppos in range(self.player_id+2, self.player_id+3+2) if len(self.hand_cards[ppos % 4]) > 0))
            assert next_player_pos is not None
            assert self.trick_on_table.is_empty()
            new_trick_on_table = Trick()  # dog is removed instantly

        # create tichu-state
        ts = TichuState(player_id=next_player_pos,
                        hand_cards=new_handcards,
                        won_tricks=self.won_tricks,
                        trick_on_table=new_trick_on_table,
                        wish=None if comb.fulfills_wish(self.wish) else self.wish,
                        ranking=tuple(new_ranking),
                        announced_tichu=self.announced_tichu,
                        announced_grand_tichu=self.announced_grand_tichu,
                        history=self.history + (combination_action,))
        return ts

    def _state_for_pass(self):
        new_won_tricks = self.won_tricks  # tricks is a tuple (of len 4) containing tuple of tricks
        new_trick_on_table = self.trick_on_table
        new_history = self.history + (PassAction(self.player_id),)

        next_player_pos = self.next_player_turn()
        leading_player = self.trick_on_table.last_combination_action.player_pos

        if (leading_player == next_player_pos
                or self.player_id < leading_player < next_player_pos
                or next_player_pos < self.player_id < leading_player
                or leading_player < next_player_pos < self.player_id):
            # trick ends with leading as winner
            trick_winner_pos = leading_player
            # TODO handle Dragon, who give to? return 2 states?
            # give the trick to the trick_winner_pos TODO create TrickSnapshots
            winner_tricks = list(self.won_tricks[trick_winner_pos])
            winner_tricks.append(self.trick_on_table)
            new_won_tricks = list(self.won_tricks)
            new_won_tricks[trick_winner_pos] = tuple(winner_tricks)
            new_won_tricks = tuple(new_won_tricks)
            new_trick_on_table = Trick()  # There is a new trick on the table
            new_history += (SimpleWinTrickEvent(leading_player, self.trick_on_table),)  # add a WinTrickEvent

        ts = TichuState(player_id=next_player_pos,
                        hand_cards=self.hand_cards,
                        won_tricks=new_won_tricks,
                        trick_on_table=new_trick_on_table,
                        wish=self.wish,
                        ranking=self.ranking,
                        announced_tichu=self.announced_tichu,
                        announced_grand_tichu=self.announced_grand_tichu,
                        history=new_history)

        return ts

    def determinization(self, observer_id: int, cheat: bool=False):
        """
        :param observer_id:
        :param cheat: if True, returns self (the real state).
        :return: A uniform random determinization of this information set (as a TichuInfoSet class).
        """
        if cheat:
            return self
        else:
            unknown_cards = list(flatten((hc for idx, hc in enumerate(self.hand_cards) if idx != observer_id)))
            # logging.debug('unknown cards: '+str(unknown_cards))
            random.shuffle(unknown_cards)
            new_hc_list = [None]*4
            for idx in range(4):
                if idx == observer_id:
                    new_hc_list[idx] = self.hand_cards[idx]
                else:
                    l = len(self.hand_cards[idx])
                    det_cards = unknown_cards[:l]
                    unknown_cards = unknown_cards[l:]
                    new_hc_list[idx] = det_cards
            new_handcards = HandCardSnapshot.from_cards_lists(*new_hc_list)
            assert all(c is not None for c in new_hc_list)
            assert sum(len(hc) for hc in new_handcards) == sum(len(hc) for hc in self.hand_cards)
            ts = TichuState(player_id=self.player_id,
                            hand_cards=new_handcards,  # The only hidden Information are the others handcards
                            won_tricks=self.won_tricks,
                            trick_on_table=self.trick_on_table,
                            wish=self.wish,
                            ranking=self.ranking,
                            announced_tichu=self.announced_tichu,
                            announced_grand_tichu=self.announced_grand_tichu,
                            history=self.history)

            return ts

    def unique_infoset_id(self, observer_id: int)->str:
        """
        
        :param observer_id: 
        :return: Unique (deterministic) id for the information-set observed by the given observer_id
        """
        if self._infosets_ids[observer_id] is None:
            self._infosets_ids[observer_id] = '|'.join(
                    [str(e) for e in (
                        self.player_id,
                        self.wish.height if self.wish else 'NoWish',
                        self.ranking,
                        sorted(self.announced_tichu),
                        sorted(self.announced_grand_tichu),
                        self.trick_on_table.unique_id(),
                        *[t.unique_id() for t in itertools.chain.from_iterable(self.won_tricks)],
                        *[len(hc) for hc in self.hand_cards],  # length of handcards.
                        self.hand_cards[observer_id].unique_id()
                        )
                     ])
        return self._infosets_ids[observer_id]

    def position_in_episode(self)->str:
        """
        Position in episode is the history since the last 'first play' action
        :return: Unique identifier for the position in episode
        """
        # TODO try: - with/without passactions; - include/remove playerid; - use the trick and not history; use 'generic' actions (eg. pair(As) instead of Pair(As1, As2))
        # TODO cache

        # history is the current trick on the table
        if self.trick_on_table.is_empty():
            return "ROOT_"+str(self.player_id)
        else:
            return '->'.join(str(a) for a in self.trick_on_table)

"""
class TichuInfoSet(TichuState, GameInfoSet):

    def __new__(cls, observer_id, *args, **kwargs):
        return super().__new__(cls, *args, **kwargs)

    def __init__(self, observer_id, *args, **kwargs):
        super().__init__(*args, **kwargs)
        check_param(observer_id in range(4))
        self._observer_id = observer_id
        self.__hash_cache = None

    @property
    def observer_id(self):
        return self._observer_id

    @classmethod
    def from_tichustate(cls, state: TichuState, observer_id: int):
        if isinstance(state, TichuInfoSet) and state.observer_id == observer_id:
            logging.warning("from_tichustate called with a TichuInfoSet!!")
            return state
        infoset = TichuInfoSet(observer_id, *state)
        return infoset

    def determinization(self, observer_id: int, cheat: bool=False):
        
        :param observer_id:
        :param cheat: if True, returns self (the real state).
        :return: A uniform random determinization of this information set (as a TichuInfoSet class).
        
        if cheat:
            return self
        else:
            unknown_cards = list(flatten((hc for idx, hc in enumerate(self.hand_cards) if idx != observer_id)))
            # logging.debug('unknown cards: '+str(unknown_cards))
            random.shuffle(unknown_cards)
            new_hc_list = [None]*4
            for idx in range(4):
                if idx == observer_id:
                    new_hc_list[idx] = self.hand_cards[idx]
                else:
                    l = len(self.hand_cards[idx])
                    det_cards = unknown_cards[:l]
                    unknown_cards = unknown_cards[l:]
                    new_hc_list[idx] = det_cards
            new_handcards = HandCardSnapshot.from_cards_lists(*new_hc_list)
            assert all(c is not None for c in new_hc_list)
            assert sum(len(hc) for hc in new_handcards) == sum(len(hc) for hc in self.hand_cards)
            ts = TichuInfoSet(observer_id=observer_id,
                              player_id=self.player_id,
                              hand_cards=new_handcards,  # The only hidden Information are the others handcards
                              won_tricks=self.won_tricks,
                              trick_on_table=self.trick_on_table,
                              wish=self.wish,
                              ranking=self.ranking,
                              announced_tichu=self.announced_tichu,
                              announced_grand_tichu=self.announced_grand_tichu)

            assert ts == self  # just checking that the infoset is indistinguishable from the new.
            return ts

    def observer_handcards(self):
        return self.hand_cards[self._observer_id]

    __hash__ = None
    
    def __hash__(self):
        if self.__hash_cache is None:
            self.__hash_cache = hash((self.player_id,
                                     self.wish.height if self.wish is not None else 0,
                                     *self.ranking,
                                     *sorted(self.announced_tichu),
                                     *sorted(self.announced_grand_tichu),
                                     *[len(hc) for hc in self.hand_cards],
                                     self.observer_handcards(),  # observers handcards
                                     *self.won_tricks,
                                     self.trick_on_table))
        return self.__hash_cache
    
    def __eq__(self, other):

        return (self.player_id == other.player_id
                and self.wish == other.wish
                and self.ranking == other.ranking
                and self.announced_tichu == other.announced_tichu
                and self.announced_grand_tichu == other.announced_grand_tichu
                and self.observer_handcards() == other.observer_handcards()
                and all(len(shc) == len(ohc) for shc, ohc in zip(self.hand_cards, other.hand_cards))
                and self.won_tricks == other.won_tricks
                and self.trick_on_table == other.trick_on_table)
"""