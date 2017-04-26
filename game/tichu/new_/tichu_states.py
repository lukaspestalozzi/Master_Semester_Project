import random
import base64 as b64
from collections import Generator, namedtuple

from game.abstract import GameInfoSet, GameState
from game.tichu.cards import Card, CardValue
from game.tichu.exceptions import IllegalActionException
from game.tichu.handcardsnapshot import HandCardSnapshot
from game.tichu.tichu_actions import TichuAction, CombinationAction, PassAction
from game.tichu.trick import Trick
from game.utils import check_param, flatten


class TichuState(GameState, namedtuple("S", [
            "player_id",
            "hand_cards",
            "won_tricks",
            "trick_on_table",
            "wish",
            "ranking",
            "announced_tichu",
            "announced_grand_tichu"
        ])):
    def __init__(self, player_id, hand_cards, won_tricks, trick_on_table, wish, ranking, announced_tichu, announced_grand_tichu):
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

        self._action_state_transitions = dict()
        self._possible_actions = None
        self._satisfy_wish = None
        self._can_pass = None
        self._possible_combs = None
        self._possible_combinations()  # init possible combs
        self._unique_id_cache = None

    def current_player_id(self) -> int:
        return self.player_id

    def next_state(self, action: TichuAction):
        if not action.player_pos == self.player_id:
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

    def evaluate(self) -> tuple:
        res = [0, 0, 0, 0]
        for rank, pos in enumerate(self.ranking):
            res[pos] = (4 - rank) ** 2
        return tuple(res)

    def is_terminal(self) -> bool:
        return len(self.ranking) >= 3 or self.is_double_win()

    def is_double_win(self):
        return len(self.ranking) >= 2 and self.ranking[0] == (self.ranking[1] + 2) % 4

    def possible_actions(self) -> frozenset:
        if self._possible_actions is not None:
            return frozenset(self._possible_actions)
        poss_combs, _ = self._possible_combinations()
        poss_acs = {CombinationAction(player_pos=self.player_id, combination=comb) for comb in poss_combs}
        if self._can_pass:
            poss_acs.add(PassAction(self.player_id))
        assert self._possible_actions is None  # sanity check
        self._possible_actions = frozenset(poss_acs)
        return frozenset(poss_acs)

    def possible_actions_gen(self) -> Generator:
        yield from self.possible_actions()

    def unique_id(self) -> str:
        """
        Guaranties to return different id's for different states in one game.
        Relies on the integrity of the game rules. Different States of different games may have the same unique_hash (by chance)
        - each card appears exactly once in the union of following attributes: hand_cards, won_tricks or trick_on_table
        - players is the same for all states in one particular game
        
        """
        if self._unique_id_cache is not None:
            return self._unique_id_cache

        def to64(s):
            return b64.b64encode(s.encode()).decode()

        def encode_collection(col):
            return ''.join([to64(str(e)) for e in sorted(col)])

        won_tricks = ''
        for tricks in self.won_tricks:
            won_tricks += ''.join([t.unique_id() for t in tricks])

        idstr = '.'.join([
            self.player_id,
            self.wish.height if self.wish is not None else '',
            encode_collection(self.ranking),
            encode_collection(self.announced_tichu),
            encode_collection(self.announced_grand_tichu),
            self.hand_cards.unique_id(),
            won_tricks,
            self.trick_on_table.unique_id()
        ])

        self._unique_id_cache = idstr
        return idstr

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
                        announced_grand_tichu=self.announced_grand_tichu)
        return ts

    def _state_for_pass(self):
        new_won_tricks = self.won_tricks  # tricks is a tuple (of len 4) containing tuple of tricks
        new_trick_on_table = self.trick_on_table

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

        ts = TichuState(player_id=next_player_pos,
                        hand_cards=self.hand_cards,
                        won_tricks=new_won_tricks,
                        trick_on_table=new_trick_on_table,
                        wish=self.wish,
                        ranking=self.ranking,
                        announced_tichu=self.announced_tichu,
                        announced_grand_tichu=self.announced_grand_tichu)

        return ts


class TichuInfoSet(GameInfoSet, TichuState):

    def __new__(cls, observer_id, *args, **kwargs):
        return super().__new__(cls, *args, **kwargs)

    def __init__(self, observer_id, *args, **kwargs):
        super().__init__(*args, **kwargs)
        check_param(observer_id in range(4))
        self._pid = observer_id
        self._unique_id_cache = None

    @property
    def observer_id(self):
        return self._pid

    def to_gamestate(self, handcards=None) -> TichuState:
        """
        
        :param handcards: If None, takes the handcards of this state, otherwise this are the handcards of the returned state
        :return: 
        """
        return TichuState(player_id=self.player_id,
                          hand_cards=self.hand_cards if handcards is not None else handcards,
                          won_tricks=self.won_tricks,
                          trick_on_table=self.trick_on_table,
                          wish=self.wish,
                          ranking=self.ranking,
                          announced_tichu=self.announced_tichu,
                          announced_grand_tichu=self.announced_grand_tichu)

    def determinization(self, cheat: bool=False) -> TichuState:
        """
        
        :param cheat: if True, returns the real state.
        :return: A uniform random determinization of this information set.
        """
        if cheat:
            return self.to_gamestate()
        else:
            unknown_cards = list(flatten((hc for idx, hc in enumerate(self.hand_cards) if idx != self.player_id)))
            random.shuffle(unknown_cards)
            new_hc_list = [None]*4
            for idx in range(4):
                if idx == self.player_id:
                    new_hc_list[idx] = self.hand_cards[idx]
                else:
                    l = len(self.hand_cards[idx])
                    det_cards = unknown_cards[:l]
                    unknown_cards = unknown_cards[l:]
                    new_hc_list[idx] = det_cards
            assert all(c is not None for c in new_hc_list)
            return self.to_gamestate(handcards=HandCardSnapshot.from_cards_lists(*new_hc_list))

    def unique_id(self) -> str:
        """
        Guaranties to return different id's for different states in one game.
        Relies on the integrity of the game rules. Different States of different games may have the same unique_hash (by chance)
        - each card appears exactly once in the union of following attributes: hand_cards, won_tricks or trick_on_table
        - players is the same for all states in one particular game

        """
        if self._unique_id_cache is not None:
            return self._unique_id_cache

        def to64(s):
            return b64.b64encode(s.encode()).decode()

        def encode_collection(col):
            return to64(''.join([str(e) for e in sorted(col)]))

        won_tricks = ''
        for tricks in self.won_tricks:
            won_tricks += ''.join([t.unique_id() for t in tricks])

        idstr = '.'.join([
            self.player_id,
            self.wish.height if self.wish is not None else '',
            encode_collection(self.ranking),
            encode_collection(self.announced_tichu),
            encode_collection(self.announced_grand_tichu),
            encode_collection([len(hc) for hc in self.hand_cards]),
            won_tricks,
            self.trick_on_table.unique_id()
        ])

        self._unique_id_cache = idstr
        return idstr