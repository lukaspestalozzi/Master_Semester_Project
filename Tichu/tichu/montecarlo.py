import logging

import random
from tichu.game.gameutils import RoundState, PlayerAction

from tichu.gametree import GameTree, MultipleRootsError, GameTreeNode
import numpy as np

from tichu.utils import check_isinstance, check_all_isinstance


class MonteCarloTreeSearch(object):

    def __init__(self):
        self._tree = MonteCarloTree()
        self._const = 1.0 / np.sqrt(2)  # value may be improved. 1 / sqrt(2) proposed on p.9 in "A Survey of Monte Carlo Tree Search Methods"
        self._player_pos = None

    def search(self, start_state):
        check_isinstance(start_state, MctsState)
        logging.debug(f"Player {start_state.current_pos} started montecarlo search.")

        self._player_pos = start_state.current_pos
        if start_state not in self._tree:
            try:
                self._tree.add_root(start_state)
            except MultipleRootsError:
                self._tree = MonteCarloTree(root=start_state)
                logging.debug("[search] replaced the MonteCarloTree")

        iteration = 0
        while not self.is_end_search(iteration):
            iteration += 1
            leaf_state = self.tree_policy(start_state)
            rollout_result = self.default_policy(leaf_state)
            self.backup(leaf_state, rollout_result)
        child, action = self.best_child(start_state)
        logging.debug(f'tree after search: \n{self._tree.print_hierarchy()}')
        return action

    def is_end_search(self, iteration):
        """
        :return: :boolean whether the search should be ended
        """
        return iteration > 100

    def tree_policy(self, state):
        """
        :param state: The starting state of the search
        :return: state: The state of the selected leaf node.
        """
        curr_state = state
        while not curr_state.is_terminal():
            if not self._tree.is_fully_expanded(curr_state):
                action, child_state = self._tree.expand(curr_state, strategy="RANDOM")
                return child_state
            else:
                curr_state, _ = self.best_child(curr_state)
        return curr_state

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
        self._tree.backup(leaf_state, rollout_result)
        return None

    def best_child(self, state):
        """
        :param state:
        :return: The best child of the given state
        """
        return self._tree.best_child_of(state)


class MctsState(RoundState):

    def __new__(cls, *args, action_leading_here=None, **kwargs):
        return super().__new__(cls, *args, **kwargs)

    def __init__(self, *args, action_leading_here=None, **kwargs):
        super().__init__(*args, **kwargs)

        self._action_leading_here = action_leading_here

    @property
    def action_leading_here(self):
        return self._action_leading_here

    @classmethod
    def from_roundstate(cls, roundstate, action_leading_here):
        return cls(current_pos=roundstate.current_pos,
                   hand_cards=roundstate.hand_cards,
                   won_tricks=roundstate.won_tricks,
                   trick_on_table=roundstate.trick_on_table,
                   wish=roundstate.wish,
                   ranking=roundstate.ranking,
                   nbr_passed=roundstate.nbr_passed,
                   announced_tichu=roundstate.announced_tichu,
                   announced_grand_tichu=roundstate.announced_grand_tichu,
                   action_leading_here=action_leading_here)

    def state_for_action(self, action):
        round_state = super().state_for_action(action)
        return MctsState.from_roundstate(roundstate=round_state, action_leading_here=action)

    def random_action(self):
        """
        :return: tuple(action, new_state) of a random legal action in this state.
        """
        action = random.choice(list(self.possible_actions()))
        new_state = self.state_for_action(action)
        return (action, new_state)

    def evaluate(self):
        # return self.calculate_points()
        res = [0, 0, 0, 0]
        for rank, pos in enumerate(self.ranking):
            res[pos] = (4-rank)**2
        return tuple(res)

    # TODO hash & equals??

    def __str__(self):
        s = f"{self.__class__.__name__}\n"
        s += f"\tcurrent_pos: {self.current_pos}\n"
        s += f"\thand_cards: {str(self.hand_cards)}\n"
        s += f"\twon_tricks: {self.won_tricks}\n"
        s += f"\ttrick_on_table: {self.trick_on_table.pretty_string()}\n"
        s += f"\twish: {self.wish}\n"
        s += f"\tranking: {self.ranking}\n"
        s += f"\tnbr_passed: {self.nbr_passed}\n"
        s += f"\tannounced_tichu: {self.current_pos}, announced_grand_tichu: {self.announced_grand_tichu}\n"
        s += f"\tpossible_actions: {self._possible_actions}\n"
        s += f"\taction_state_transitions: {self._action_state_transitions}\n"
        s += f"\tcan_pass: {self._can_pass}\n"
        s += f"\taction_leading_here: {self._action_leading_here}\n"
        return s


class MonteCarloTree(GameTree):

    def _create_node(self, parent, data):
        return MonteCarloTreeNode(parent, data)

    def is_fully_expanded(self, state):
        return self._node(state).is_fully_expanded()

    def expand(self, state, strategy='RANDOM'):
        """
        Chooses an action from the given state, with the given strategy and adds a new child node corresponding to the new state
        :param state: the state to expand
        :param strategy: ['RANDOM', 'NEXT', 'LOWEST', 'HIGHEST'] how the action to expand is chosen.
            - RANDOM: a random action
            - NEXT: the next action in the list
            - LOWEST: the lowest combination (sorted by length and then height, None counting as the lowest of all possiblecombinations)
            - HIGHEST: the highest combination
        :return: tuple(action, new_state) of a not yet visited action
        """
        expanding_node = self._node(state)
        action, new_state = expanding_node.expand_node(strategy=strategy)
        self.add_child(parent=state, child=new_state)
        return (action, new_state)

    def backup(self, state, rollout_result):
        node = self._node(state)
        node.backup(rollout_result=rollout_result)

    def best_child_of(self, state):
        bc_node, action = self._node(state).best_child()
        return (bc_node.data, action)


class MonteCarloTreeNode(GameTreeNode):

    def __init__(self, parent, state=None):
        check_isinstance(state, MctsState)
        parent is None or check_isinstance(parent, MonteCarloTreeNode)
        super().__init__(parent=parent, data=state)

        self._visited_count = 0
        self._reward_count = 0

        self._possible_actions = set(state.possible_actions())
        assert check_all_isinstance(self._possible_actions, PlayerAction)
        self._expanded_actions = set()
        self._remaining_actions = list(self._possible_actions)

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

    def is_fully_expanded(self):
        """ :returns True iff the state is terminal or all actions are already expanded as children"""
        res = self.data.is_terminal() or len(self._remaining_actions) == 0
        # logging.debug(f"Fully expanded -> {res}, (is terminal:{self.data.is_terminal()}, len remaining action:{len(self._remaining_actions)}, expanded: {self._expanded_actions}, remaining: {self._remaining_actions})")
        assert len(self._children) == len(self._expanded_actions)
        return res

    def backup(self, rollout_result):
        """
        The backup method of the monte carlo tree search.
        :param rollout_result:
        :return: True
        """
        self.increase_visited_count()
        if self.parent_node is not None:
            self.update_reward_count(rollout_result[self.parent_node.data.current_pos])
            return self.parent_node.backup(rollout_result)
        else:
            return True

    def expand_node(self, strategy='RANDOM'):

        if strategy == 'RANDOM':
            action = random.choice(self._remaining_actions)
            self._remaining_actions.remove(action)
        elif strategy == 'NEXT':
            action = self._remaining_actions.pop()
        elif strategy == 'LOWEST':
            action = self._remaining_actions.sort(key=lambda c: 0 if c is None else (len(c), c.height)).pop()
        elif strategy == 'HIGHEST':
            action = self._remaining_actions.sort(reverse=True, key=lambda c: 0 if c is None else (len(c), c.height)).pop()
        else:
            raise ValueError("strategy must be one of ['RANDOM', 'NEXT', 'LOWEST', 'HIGHEST'], but was {}".format(strategy))

        # sanity checks
        assert action not in self._expanded_actions
        assert action not in self._remaining_actions

        self._expanded_actions.add(action)
        new_state = self.data.state_for_action(action)

        return action, new_state

    def best_child(self):
        """
        :param ret_action: If True, returns a tuple (child node, action to child)
        :return: The best child node of this node
        """
        assert len(self._children) > 0
        C = 0.707106781186  # 1.0 / np.sqrt(2)  # value may be improved, proposed on p.9 in "A Survey of Monte Carlo Tree Search Methods"

        scores = [(c, c.reward_ratio + C*np.sqrt((2 * np.log(self._visited_count) / max(c.visited_count, 1e-6))))
                  for c in self._children]
        best_child, score = max(scores, key=lambda t: t[1])
        action = best_child.data.action_leading_here
        return best_child, action

    def _short_label(self):
        if self.is_root():
            return 'Root'
        else:
            return f'{self.data.action_leading_here} ratio:{self.reward_ratio:.2f} (visited:{self._visited_count}, reward:{self.reward_count})'
