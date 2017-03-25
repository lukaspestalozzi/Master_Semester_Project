import random
from collections import namedtuple
from tichu.cards.card import Card
from tichu.cards.cards import Combination, Cards
from tichu.exceptions import IllegalActionException

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


class MctsState(namedtuple("GameState", ["player_pos", "hand_cards", "tricks", "combination_on_table", "wish", "ranking", "nbr_passed", "announced_tichu", "announced_grand_tichu"])):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._visited_count = 0
        self._reward_count = 0

        pcombs, play_wish = self._find_possible_combinations()
        self._possible_combinations = pcombs
        self._can_pass = self.combination_on_table is not None and not play_wish
        self._expanded_actions = set()
        self._remaining_actions = list(self._possible_combinations)
        self._action_state_transitions = dict()

        if self._can_pass:
            self._remaining_actions.append(None)



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

    def _find_possible_combinations(self):
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
        new_comb_on_table = comb
        new_handcards = self.hand_cards.remove_cards(from_pos=self.player_pos, cards=comb.cards)
        assert len(new_handcards[self.player_pos]) < len(self.hand_cards[self.player_pos])
        assert new_handcards[self.player_pos].issubset(self.hand_cards[self.player_pos])

        # test ranking:
        new_ranking = list(self.ranking)
        if len(new_handcards[self.player_pos]) == 0:
            new_ranking.append(self.player_pos)
            assert len(set(new_ranking)) == len(new_ranking), "state:{}\ncomb:{}".format(self, comb)

        # handle dog
        next_player = self.next_player_turn()
        if Card.DOG in comb:
            next_player = next((ppos % 4 for ppos in range(self.player_pos+2, self.player_pos+3+2) if len(self.hand_cards[ppos % 4]) > 0))
            assert next_player is not None
            assert self.nbr_passed == 0 # just to be sure
            new_comb_on_table = None  # dog is removed instantly

        # create game-state
        gs = MctsState(player_pos=next_player,
                       hand_cards=new_handcards,
                       tricks=self.tricks,
                       combination_on_table=new_comb_on_table,
                       wish=None if comb.fulfills_wish(self.wish) else self.wish,
                       ranking=new_ranking,
                       nbr_passed=0,
                       announced_tichu=self.announced_tichu,
                       announced_grand_tichu=self.announced_grand_tichu)
        return gs

    def _state_for_action(self, action):
        """
        :param action: Combination or None (pass).
        :return: The new game state the action leads to.
        """
        if action in self._action_state_transitions:
            return self._action_state_transitions[action]
        elif action is None:
            new_state = self._state_for_pass()
        elif isinstance(action, Combination):
            assert action.can_be_played_on(self.combination_on_table)
            new_state = self._state_for_comb(action)
        else:
            raise ValueError("action must be None or a Combination")
        self._action_state_transitions[action] = new_state
        return new_state

    def _state_for_pass(self):
        if not self._can_pass:
            raise IllegalActionException("Can't pass")
        else:
            # TODO überprüfen
            # give trick to player if this is 3rd passing
            new_tricks = self.tricks  # tricks is a tuple (of len 4) containing list of cards  # TODO change to list of Tricks (and unfinished tricks)
            if self.nbr_passed == 2:
                trick_winner_pos = (self.player_pos + 1) % 4  # 3 players passed, so it is the next player to this player
                new_tricks = list(self.tricks)
                new_tricks[trick_winner_pos] = Cards(self.tricks[trick_winner_pos]).add_all(self.combination_on_table).to_immutable()
                new_tricks = tuple(new_tricks)
            gs = MctsState(player_pos=self.next_player_turn(),
                           hand_cards=self.hand_cards,
                           tricks=new_tricks,
                           combination_on_table=self.combination_on_table if self.nbr_passed < 2 else None,  # test if this pass action is the 3rd
                           wish=self.wish,
                           ranking=list(self.ranking),
                           nbr_passed=self.nbr_passed+1 if self.nbr_passed < 2 else 0,
                           announced_tichu=self.announced_tichu,
                           announced_grand_tichu=self.announced_grand_tichu)
            assert ((gs.combination_on_table is None and gs.nbr_passed == 0) or (gs.combination_on_table is not None and gs.nbr_passed > 0))
            return gs

    def next_player_turn(self):
        return next((ppos % 4 for ppos in range(self.player_pos+1, self.player_pos+4) if len(self.hand_cards[ppos % 4]) > 0))

    def expand(self, strategy='RANDOM'):
        """

        :param strategy: ['RANDOM', 'NEXT', 'LOWEST', 'HIGHEST'] how the action to expand is chosen.
            - RANDOM: a random action
            - NEXT: the next action in the list
            - LOWEST: the lowest combination (sorted by length and then height, None counting as the lowest of all possiblecombinations)
            - HIGHEST: the highest combination
        :return: tuple(action, new_state) of a not yet visited action
        """
        if strategy == 'RANDOM':
            action = random.choice(self._remaining_actions)
            self._remaining_actions.remove(action)
        elif strategy == 'NEXT':
            action = self._remaining_actions.pop()
        elif strategy == 'LOWEST':
            action = sorted(self._remaining_actions, key=lambda c: 0 if c is None else (len(c), c.height)).pop()
        elif strategy == 'HIGHEST':
            action = sorted(self._remaining_actions, reversed=True, key=lambda c: 0 if c is None else (len(c), c.height)).pop()
        else:
            raise ValueError("strategy must be one of ['RANDOM', 'NEXT', 'LOWEST', 'HIGHEST'], but was {}".format(strategy))

        assert action not in self._expanded_actions
        self._expanded_actions.add(action)
        new_state = self._state_for_action(action)
        return (action, new_state)

    def can_be_expanded(self):
        return not self.is_terminal() and len(self._remaining_actions) > 0

    def random_action(self):
        """
        :return: tuple(action, new_state) of a random legal action in this state.
        """
        action = random.choice(self._possible_combinations)
        try:
            new_state = self._action_state_transitions[action]
        except KeyError:
            new_state = self._state_for_action(action)
        return (action, new_state)

    def is_double_win(self):
        return len(self.ranking) >= 2 and self.ranking[0] == (self.ranking[1] + 2) % 4

    def is_terminal(self):
        return (len(self.ranking) >= 3
                or sum([len(hc) > 0 for hc in self.hand_cards]) <= 1  # equivalent to previous one TODO remove?
                or self.is_double_win())

    def evaluate(self):
        """
        :return: tuple of length 4 with the points of each player at the corresponding index.
        """
        def calc_tichu_points():
            tichu_points = [0, 0, 0, 0]
            for gt_pos in self.announced_grand_tichu:
                tichu_points[gt_pos] += 200 if gt_pos == self.ranking[0] else -200
            for t_pos in self.announced_tichu:
                tichu_points[t_pos] += 100 if t_pos == self.ranking[0] else -100
            return tichu_points

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
                points[final_ranking[p]] += sum(t.points for t in self.tricks[final_ranking[p]])

            # first player gets the points of the last players tricks
            winner = final_ranking[0]
            looser = final_ranking[3]
            points[winner] += sum(t.points for t in self.tricks[looser])

            # the handcards of the last player go to the enemy team
            points[(looser+1) % 4] += sum(t.points for t in self.hand_cards[looser])
        # fi

        # sum the points of each team
        for pos in range(4):
            points[pos] += points[(pos+2) % 4]

        assert len(points) == 4
        return tuple(points)

    def __hash__(self):
        return hash((self.player_pos, self.hand_cards, self.combination_on_table, self.wish, self.nbr_passed))

    def __eq__(self, other):
        return (self.__class__ == other.__class__
                and self.player_pos == other.player_pos
                and self.hand_cards == other.hand_cards
                and self.combination_on_table == other.combination_on_table
                and self.wish == other.wish
                and self.nbr_passed == other.nbr_passed)




