import abc

import logging
import numpy as np

import random

from game.tichu.tichu_actions import PlayerAction
from game.tichu.states import RoundState
from game.utils import GameTree, GameTreeNode, check_isinstance, check_all_isinstance


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


class MonteCarloTree(GameTree, metaclass=abc.ABCMeta):

    @abc.abstractmethod
    def actions_to_expand(self, state, possible_actions):
        """
        Overwrite this method to customize the expanding of the Tree.

        :param state: The state to be expanded
        :param possible_actions: actions that can be expanded
        :return: a collection of (state, action) tuples into which the tree expands to.
        """
        pass

    @abc.abstractmethod
    def node_value(self, node):
        """
        This value is used to compare nodes and to choose the best child.

        Overwrite this method to customize the value of nodes.

        :param node:
        :return: a numeric value.
        """
        pass

    def is_fully_expanded(self, state):
        """
        :param state: the game-state
        :return: True if all possible actions in this state are already present as children in this tree.
        """
        return self._node(state).is_fully_expanded()

    def expand(self, state):
        """
        Expands the node corresponding to the state and returns a list of tuples (state, action) of newly added states with the corresponding action.

        :param state: the state to expand
        :return: list of tuples (state, action) of newly added states with the corresponding action.
        """
        expanding_node = self._node(state)
        s_a = self.actions_to_expand(state, expanding_node.remaining_actions)
        for child_state, action in s_a:
            expanding_node.expand_node(action)
            self.add_child(parent=state, child=child_state)
        return list(s_a)

    def backup(self, leaf_state, rollout_result):
        """
        Backs the rollout_result through the Tree.

        :param leaf_state: the state from which to back up the rollout_result.
        :param rollout_result: A tuple of length 4 containing the value for each player at the corresponding index.
        :return: self
        """
        node = self._node(leaf_state)
        while node is not None:
            node.backup(rollout_result=rollout_result)
            node = node.parent_node
        return self

    def best_child_of(self, state):
        """
        Returns a Tuple(state, action) with the state and action corresponding to the highest value of the monte-carlo-node.
        Overwrite the function 'node_value' to customize the value of a node.

        :param state:
        :return: Tuple(state, action) with the best action (child with the highest value) for the given state
        """
        child_nodes = self._node(state).children_nodes
        val, max_node = max(((self.node_value(cn), cn) for cn in child_nodes), key=lambda tup: tup[0])
        return (max_node.data, max_node.data.action_leading_here)

    def main_line(self, hand_cards=False):
        """
        Traverses the Tree from the root, always taking the 'best child' from each node.

        :param hand_cards: If True, returns tripple (game_state, action, handcards)
        :return: The best Path from the root. Path is a sequence of tuples (game_state, action) with the root at position 0.
        """
        if hand_cards:
            path = [(self._root_node.data, None, self._root_node.data.hand_cards)]
        else:
            path = [(self._root_node.data, None)]
        curr_node = self._root_node
        while not curr_node.is_leaf():
            ch_state, action = self.best_child_of(curr_node.data)
            curr_node = self._node(ch_state)
            if hand_cards:
                path.append((ch_state, action, ch_state.hand_cards))
            else:
                path.append((ch_state, action))
        return path

    def _create_node(self, parent, data):
        return MonteCarloTreeNode(parent, data)


class MonteCarloTreeNode(GameTreeNode):

    def __init__(self, parent, state=None, initial_reward_ratio=float("inf")):
        """

        :param parent: MonteCarloTreeNode; The parent node of this None
        :param state: MctsState of this none
        :param initial_reward_ratio: The initial reward ratio (when the node was not yet visited)
        """
        check_isinstance(state, MctsState)
        parent is None or check_isinstance(parent, MonteCarloTreeNode)
        super().__init__(parent=parent, data=state)

        self._visited_count = 0
        self._reward_count = 0
        self._reward_ratio = self._reward_count / self._visited_count if self._visited_count != 0 else initial_reward_ratio

        self._possible_actions = set(state.possible_actions())
        assert check_all_isinstance(self._possible_actions, PlayerAction)
        self._expanded_actions = set()
        self._remaining_actions = list(self._possible_actions)

    @property
    def remaining_actions(self):
        return self._remaining_actions

    @property
    def visited_count(self):
        return self._visited_count

    @property
    def reward_count(self):
        return self._reward_count

    @property
    def reward_ratio(self):
        return self._reward_ratio

    def update_reward_count(self, amount):
        """
        Increases visited_count by 1 and adds the amount to the reward_count

        :param amount:
        :return: self
        """
        self._reward_count += amount
        self._visited_count += 1
        self._reward_ratio = self._reward_count / self._visited_count
        return self

    def is_fully_expanded(self):
        """ :returns True iff the state is terminal or all actions are already expanded as children"""
        res = self.data.is_terminal() or len(self._remaining_actions) == 0
        assert len(self._children) == len(self._expanded_actions)
        return res

    def backup(self, rollout_result):
        """
        Updates the nodes visited_count and reward_count.

        :param rollout_result: A sequence of length 4 containing the value for each player at the corresponding index.
        :return: self
        """
        if self.parent_node is not None:
            self.update_reward_count(rollout_result[self.parent_node.data.current_pos])
        return self

    def expand_node(self, action):
        """
        Removes the action from the remaining_actions and adds it to the remaining_actions.

        :param action:
        :return: self
        """
        self._remaining_actions.remove(action)

        # sanity checks
        assert action not in self._expanded_actions
        assert action not in self._remaining_actions

        self._expanded_actions.add(action)

        return self

    def _short_label(self):
        s = ''
        if self.is_root():
            s += 'Root'
        s += f'{hash(self.data)} {self.data.action_leading_here} ratio:{self.reward_ratio:.2f} (visited:{self._visited_count}, reward:{self.reward_count})'
        return s


class BaseMonteCarloTreeSearch(MonteCarloTree, metaclass=abc.ABCMeta):
    """
    Implements the standard MonteCarloTreeSearch algorithm.

    Overwrite following Functions to customize the search:

    - **is_end_search:** To end the search
    - **next_child:** Next node in the tree-strategy phase.
    - **next_rollout_state:** Next state in the rollout-strategy phase
    - **evaluate_state:** Generate the result of the rollout

    """

    def __init__(self, nbr_rollouts=1):
        super().__init__()
        check_isinstance(nbr_rollouts, int)
        self._nbr_rollouts = nbr_rollouts

    def search(self, start_state):
        check_isinstance(start_state, MctsState)
        if start_state not in self:
            _ = self.clear()
            self.add_root(start_state)

        iteration = 0
        while not self.is_end_search(iteration):
            iteration += 1
            leaf_states = self._tree_policy(start_state)
            for ls in leaf_states*self._nbr_rollouts:
                rollout_result, final_state = self._rollout_policy(ls)
                self.backup(ls, rollout_result)
        action = self.best_action(start_state)
        return action

    @abc.abstractmethod
    def is_end_search(self, iteration):
        """
        :return: [boolean] whether the search should be ended
        """
        pass

    @abc.abstractmethod
    def next_rollout_state(self, state):
        """
        Overwrite this action to customize the rollout strategy.

        :param state: game state
        :return: A state that can be reached from the given state by a legal action.
        """
        pass

    @abc.abstractmethod
    def evaluate_state(self, state):
        """

        :param state:
        :return: A tuple of length 4 containing the value for each player at the corresponding index. ie (player0_result, player1_result, ..., ...)
        """
        pass

    @abc.abstractmethod
    def next_child(self, state):
        """
        Overwrite this action to customize the tree policy.

        :param state: current state
        :return: The next child to be visited in the tree traversal in tree-policy.
        """
        pass

    @abc.abstractmethod
    def best_action(self, state):
        """
        :param state:
        :return: the best action from the given state according to the current search-tree.
        """
        pass

    def _tree_policy(self, state):
        """
        Traverses the Tree and selects a leaf-node to be expanded (and expands it).

        :param state: The starting state of the search
        :return: state: A list of leaf-states that have been expanded into
        """
        curr_state = state
        while not curr_state.is_terminal():
            if not self.is_fully_expanded(curr_state):
                expanded_s_a = self.expand(curr_state)
                return [s for s, a in expanded_s_a]
            else:
                curr_state = self.next_child(curr_state)
        return [curr_state]

    def _rollout_policy(self, state):
        """
        Simulates a rollout from the given state.
        Calls and returns the 'evaluate_state' function with the final state.

        :param state: state to start the rollout
        :return: Tuple of the result of the rollout and the terminal state.
        """
        rollout_state = state
        while not rollout_state.is_terminal():
            rollout_state = self.next_rollout_state(rollout_state)
        return (self.evaluate_state(rollout_state), rollout_state)


# ----------------------------- Rollout Strategies --------------------------------- #

class MCTSRolloutStrategy(BaseMonteCarloTreeSearch, metaclass=abc.ABCMeta):
    """

    """
    @abc.abstractmethod
    def next_rollout_state(self, state):
        pass


class MCTSEvaluateStrategy(BaseMonteCarloTreeSearch, metaclass=abc.ABCMeta):
    """

    """
    @abc.abstractmethod
    def evaluate_state(self, state):
        pass


class MCTSTreeStrategy(BaseMonteCarloTreeSearch, metaclass=abc.ABCMeta):
    """

    """
    @abc.abstractmethod
    def next_child(self, state):
        pass


class MCTSBestActionStrategy(BaseMonteCarloTreeSearch, metaclass=abc.ABCMeta):
    """

    """
    @abc.abstractmethod
    def best_action(self, state):
        pass


class MCTSExpandStrategy(BaseMonteCarloTreeSearch, metaclass=abc.ABCMeta):
    """

    """
    @abc.abstractmethod
    def actions_to_expand(self, state, possible_actions):
        pass


class MCTSNodeValueStrategy(BaseMonteCarloTreeSearch, metaclass=abc.ABCMeta):
    """

    """
    @abc.abstractmethod
    def node_value(self, node):
        pass

# ----------------------------- Concrete Rollout Strategies --------------------------------- #


# Expand
class RandomExpandStrategy(MCTSExpandStrategy, metaclass=abc.ABCMeta):

    def actions_to_expand(self, state, possible_actions):
        action = random.choice(possible_actions)
        new_state = state.state_for_action(action)
        return [(new_state, action)]


class AllExpandStrategy(MCTSExpandStrategy, metaclass=abc.ABCMeta):
    """
    Expands all possible actions at once
    """

    def actions_to_expand(self, state, possible_actions):
        return [(state.state_for_action(action), action) for action in possible_actions]


# NodeValue
class UCTNodeValueStrategy(MCTSNodeValueStrategy, metaclass=abc.ABCMeta):

    def node_value(self, node):
        if node.visited_count == 0 or node.parent_node.visited_count == 0:
            return float("inf")
        C = 0.707106781186  # 1.0 / np.sqrt(2)  # value may be improved, proposed on p.9 in "A Survey of Monte Carlo Tree Search Methods"
        return node.reward_ratio + C * np.sqrt(2 * np.log(node.parent_node.visited_count) / node.visited_count)


# Rollout
class RandomRolloutStrategy(MCTSRolloutStrategy, metaclass=abc.ABCMeta):
    """

    """
    def next_rollout_state(self, state):
        return state.random_action()[1]


# Evaluate Final State
class RankBasedEvaluateStrategy(MCTSEvaluateStrategy, metaclass=abc.ABCMeta):
    """

    """
    def evaluate_state(self, state):
        res = [0, 0, 0, 0]
        for rank, pos in enumerate(state.ranking):
            res[pos] = (4 - rank) ** 2
        return tuple(res)


class PointsEvaluateStrategy(MCTSEvaluateStrategy, metaclass=abc.ABCMeta):
    """

    """
    def evaluate_state(self, state):
        return state.calculate_points()


# Tree
class HighestValueTreeStrategy(MCTSTreeStrategy, metaclass=abc.ABCMeta):
    """

    """
    def next_child(self, state):
        child = self.best_child_of(state)[0]
        return child


# Beest Action
class HighestValueBestActionStrategy(MCTSBestActionStrategy, metaclass=abc.ABCMeta):
    """

    """
    def best_action(self, state):
        child, action = self.best_child_of(state)
        return action


# ------------------------- Concrete MonteCarlo Classes -------------------------------------- #

class DefaultMonteCarloTreeSearch(AllExpandStrategy,  # RandomExpandStrategy
                                  UCTNodeValueStrategy,
                                  RandomRolloutStrategy,
                                  PointsEvaluateStrategy,
                                  HighestValueTreeStrategy,
                                  HighestValueBestActionStrategy):

    def __init__(self, search_iterations=50, nbr_rollouts=5):
        super().__init__(nbr_rollouts=nbr_rollouts)
        self._search_iterations = search_iterations

    def is_end_search(self, iteration):
        return iteration > self._search_iterations

