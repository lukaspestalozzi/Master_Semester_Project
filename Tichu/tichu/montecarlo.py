from collections import namedtuple
from tichu.cards.card import Card
from tichu.cards.cards import Combination, Cards
from tichu.exceptions import IllegalActionException
from tichu.game.gameutils import HandCardSnapshot

from tichu.gametree import GameTree
import numpy as np


class MonteCarloTreeSearch(object):

    def __init__(self, root_state):
        self._tree = GameTree(root=root_state)
        self._const = 1.0 / np.sqrt(2)  # value may be improved. 1 / sqrt(2) proposed on p.9 in "A Survey of Monte Carlo Tree Search Methods"

    def search(self, start_state):
        iteration = 0
        while not self.end_search(iteration):
            iteration += 1
            leaf_state = self.tree_policy(start_state)
            rollout_result = self.default_policy(leaf_state)
            self.backup(leaf_state, rollout_result)
        return self.best_child(start_state).action

    def end_search(self, iteration):
        """
        :return: :boolean whether the search should be ended
        """
        return iteration > 10

    def tree_policy(self, state):
        """
        :param state: The starting state of the search
        :return: state: The state of the selected leaf node.
        """
        curr_state = state
        while not curr_state.is_leaf():
            if curr_state.can_be_expanded():
                return self._expand(curr_state)
            else:
                curr_state = self.best_child(curr_state)
        return curr_state

    def _expand(self, state):
        action, child_state = state.expand()
        self._tree.add_child(parent=state, action=action, child=child_state)
        return action, child_state

    def default_policy(self, state):
        """
        :param state: state to start the rollouts
        :return: the result of the rollouts
        """
        rollout_state = state
        while not rollout_state.is_terminal():
            ac, rollout_state = rollout_state.random_action()
        return rollout_state.evaluate()

    def backup(self, leaf_state, rollout_result):
        """
        Backs up the result of the rollout from the given leaf node.
        :param leaf_state:
        :param rollout_result:
        :return: None
        """
        # TODO may be adapded for multiple players (negmax)
        state = leaf_state
        while state is not None:
            state.increase_visited_count()
            state.update_reward_count(rollout_result)
            state = self._tree.parent(state)
        return None

    def best_child(self, state):
        """

        :param state:
        :return: The best child of the given state
        """
        children_states = self._tree.children(state)
        Np = state.visited_count
        scores = [c.reward_ratio + self._const*np.sqrt((2 * np.log(Np) / c.visited_count))
                  for c in children_states]
        return children_states[np.argmax(scores)]


class MctsState(namedtuple("GameState", ["player_pos", "hand_cards", "tricks", "combination_on_table", "wish", "ranking", "nbr_passed"])):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._visited_count = 0
        self._reward_count = 0
        pcombs, play_wish = self._possible_combinations()
        self._possible_actions = pcombs
        self._expanded_actions = []
        self._remaining_actions = list(self._possible_actions)
        self._can_pass = self.combination_on_table is not None and not play_wish


    @property
    def visited_count(self):
        return self._visited_count

    @property
    def reward_count(self):
        return self._reward_count

    @property
    def reward_ratio(self):
        return self._reward_count / self._visited_count if self._visited_count != 0 else float("inf")  # inf when visited count = 0

    def update_reward_count(self, amount):
        self._reward_count += amount

    def increase_visited_count(self):
        self._visited_count += 1

    def _possible_combinations(self):
        """
        :return: a tuple of the possible combinations and whether the combinations satisfy the wish
        """
        possible_combs = list(self.hand_cards.all_combinations(played_on=self.combination_on_table))
        # verify wish
        if self.wish and self.wish in (c.card_value for c in self.combination_on_table):
            pcombs = [comb for comb in possible_combs if comb.contains_cardval(self.wish)]
            if len(pcombs):
                return (pcombs, True)
        return (possible_combs, False)

    def _state_for_comb(self, comb):
        # TODO überprüfen
        new_comb_on_table = comb
        # remove comb from handcards:
        player_handcards = Cards(self.combination_on_table)
        assert len(player_handcards) > 0
        player_handcards.remove_all(comb)
        assert len(player_handcards) < len(self.combination_on_table)
        new_handcards_l = list(self.hand_cards)
        new_handcards_l[self.player_pos] = player_handcards.to_immutable()
        new_handcards = HandCardSnapshot(*new_handcards_l)
        assert new_handcards[self.player_pos].issubset(player_handcards), "new:{}; phc:{}".format(new_handcards[self.player_pos], player_handcards)
        assert len(player_handcards) == len(new_handcards[self.player_pos])
        # ranking:
        new_ranking = list(self.ranking)
        if len(player_handcards) == 0:
            new_ranking.append(self.player_pos)
            assert len(set(new_ranking)) == len(new_ranking), "state:{}\ncomb:{}".format(self, comb)

        # handle dog
        if Card.DOG in comb:
            next_player = next((ppos % 4 for ppos in range(self.player_pos+2, self.player_pos+3+2)
                                              if len(self.hand_cards[ppos % 4]) > 0))
            assert next_player is not None
            new_comb_on_table = None

        # create game-state
        gs = MctsState(player_pos=self.next_player_turn(),
                       hand_cards=new_handcards,
                       tricks=self.tricks,
                       combination_on_table=new_comb_on_table,
                       wish=None if comb.fulfills_wish(self.wish) else self.wish,
                       ranking=new_ranking,
                       nbr_passed=0)
        return gs

    def _state_for_action(self, action):
        """

        :param action: Combination or None (pass).
        :return: The new game state the action leads to.
        """
        if action is None:
            return self._state_for_pass()
        elif isinstance(action, Combination):
            assert action.can_be_played_on(self.combination_on_table)
            return self._state_for_comb(action)

        else:
            raise ValueError("action must be None or a Combination")

    def _state_for_pass(self):
        if not self._can_pass:
            raise IllegalActionException("Can't pass")
        else:
            # TODO überprüfen
            # give trick to player if this is 3rd passing
            new_tricks = self.tricks
            if self.nbr_passed == 2:
                trick_winner_pos = (self.player_pos + 1) % 4
                new_tricks = list(self.tricks)
                new_tricks[trick_winner_pos] = Cards(self.tricks[trick_winner_pos]).add_all(self.combination_on_table).to_immutable()
                new_tricks = tuple(new_tricks)
            gs = MctsState(player_pos=self.next_player_turn(),
                           hand_cards=self.hand_cards,
                           tricks=new_tricks,
                           combination_on_table=self.combination_on_table if self.nbr_passed < 2 else None,  # test if this pass action is the 3rd
                           wish=self.wish,
                           ranking=list(self.ranking),
                           nbr_passed=self.nbr_passed+1 if self.nbr_passed < 2 else 0)
            assert ((gs.combination_on_table is None and gs.nbr_passed == 0) or (gs.combination_on_table is not None and gs.nbr_passed > 0))
            return gs

    def next_player_turn(self):
        # TODO überprüfen
        return next((ppos % 4 for ppos in range(self.player_pos+1, self.player_pos+4) if len(self.hand_cards[ppos % 4]) > 0))

    def expand(self):
        pass  # TODO return action, new_state of not yet visited action

    def can_be_expanded(self):
        pass  # TODO not all actions have been returned by 'expand'

    def is_terminal(self):
        pass  # TODO

    def random_action(self):
        pass  # TODO return (action, new_state)

    def evaluate(self):
        pass  # TODO

    def __hash__(self):
        return hash((self.player_pos, self.hand_cards, self.combination_on_table, self.wish, self.nbr_passed))

    def __eq__(self, other):
        return (self.__class__ == other.__class__
                and self.player_pos == other.player_pos
                and self.hand_cards == other.hand_cards
                and self.combination_on_table == other.combination_on_table
                and self.wish == other.wish
                and self.nbr_passed == other.nbr_passed)




