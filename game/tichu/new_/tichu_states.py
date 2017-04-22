import random
from collections import Collection, Generator, namedtuple

from game.abstract import GameInfoSet, GameState, Player, Action
from game.tichu.cards import Card
from game.tichu.exceptions import IllegalActionException
from game.tichu.tichu_actions import TichuAction, CombinationAction, PassAction
from game.tichu.trick import Trick
from game.utils import check_param


class TichuState(GameState, namedtuple("S", [
            "player",  # TODO player_id ?
            "hand_cards",
            "won_tricks",
            "trick_on_table",
            "wish",
            "ranking",
            "announced_tichu",
            "announced_grand_tichu"
        ])):
    def __init__(self):
        super().__init__()

        # TODO add some paranoid checks

        self._action_state_transitions = dict()
        self._possible_actions = None
        self._satisfy_wish = None
        self._can_pass = None

    def current_player(self) -> Player:
        return self.player

    def next_state(self, action: TichuAction) -> TichuState:
        if not action.player_pos == self.player.id:
            raise IllegalActionException(f"Only player:{self.player.id} can play in this case, but action was: {action}")
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

    def evaluate(self) -> dict:
        pass

    def is_terminal(self) -> bool:
        return len(self.ranking) >= 3 or self.is_double_win()

    def is_double_win(self):
        return len(self.ranking) >= 2 and self.ranking[0] == (self.ranking[1] + 2) % 4

    def possible_actions(self) -> frozenset:
        if self._possible_actions is not None:
            return frozenset(self._possible_actions)
        poss_combs, _ = self._possible_combinations()
        poss_acs = {CombinationAction(player_pos=self.player.id, combination=comb) for comb in poss_combs}
        if self._can_pass:
            poss_acs.add(PassAction(self.player.id))
        assert self._possible_actions is None  # sanity check
        self._possible_actions = frozenset(poss_acs)
        return frozenset(poss_acs)

    def possible_actions_gen(self) -> Generator:
        pass

    def unique_hash(self) -> int:
        base = 13
        # TODO

    def random_action(self) -> TichuAction:
        """
        
        :return: A random legal action from this state
        """
        return random.choice(self.possible_actions())

    def _possible_combinations(self) -> tuple:
        """
        :return: a tuple of the possible combinations and whether the combinations satisfy the wish
        """
        if self._possible_combs is not None:
            # return already calculated combinations
            return (frozenset(self._possible_combs), self._satisfy_wish)
        comb_on_table = self.trick_on_table.last_combination
        possible_combs = set(self.hand_cards[self.player.id].all_combinations(played_on=comb_on_table))
        # verify wish
        self._satisfy_wish = False
        if self.wish and self.wish in (c.card_value for c in self.hand_cards[self.player.id]):
            pcombs = {comb for comb in possible_combs if comb.contains_cardval(self.wish)}
            if len(pcombs):
                self._satisfy_wish = True
                possible_combs = pcombs
        self._possible_combs = frozenset(possible_combs)
        self._can_pass = self.trick_on_table.last_combination is not None and not self._satisfy_wish
        return (frozenset(possible_combs), self._satisfy_wish)

    def next_player_turn(self):
        return next((ppos % 4 for ppos in range(self.player.id + 1, self.player.id + 4) if len(self.hand_cards[ppos % 4]) > 0))

    def _state_for_combination_action(self, combination_action: CombinationAction) -> TichuState:
        comb = combination_action.combination
        new_trick_on_table = self.trick_on_table.add_combination_action(combination_action)
        new_handcards = self.hand_cards.remove_cards(from_pos=self.player.id, cards=comb.cards)
        assert len(new_handcards[self.player.id]) < len(self.hand_cards[self.player.id])
        assert new_handcards[self.player.id].issubset(self.hand_cards[self.player.id])

        # test ranking:
        new_ranking = list(self.ranking)
        if len(new_handcards[self.player.id]) == 0:
            new_ranking.append(self.player.id)
            assert len(set(new_ranking)) == len(new_ranking), "state:{}\ncomb:{}".format(self, comb)

        # handle dog
        next_player = self.next_player_turn()
        if Card.DOG in comb:
            next_player = next((ppos % 4 for ppos in range(self.player.id+2, self.player.id+3+2) if len(self.hand_cards[ppos % 4]) > 0))
            assert next_player is not None
            assert self.trick_on_table.is_empty()
            new_trick_on_table = Trick([])  # dog is removed instantly

        # create game-state
        gs = TichuState(current_pos=next_player,
                        hand_cards=new_handcards,
                        won_tricks=self.won_tricks,
                        trick_on_table=new_trick_on_table,
                        wish=None if comb.fulfills_wish(self.wish) else self.wish,
                        ranking=tuple(new_ranking),
                        nbr_passed=0,
                        announced_tichu=self.announced_tichu,
                        announced_grand_tichu=self.announced_grand_tichu)
        return gs


class TichuInfoSet(GameInfoSet, TichuState):

    def __init__(self, player_id):
        super().__init__()
        check_param(player_id in range(4))
        self._pid = player_id

    @property
    def player_id(self):
        return self._pid

    def determinization(self, *args, **kwargs):
        pass