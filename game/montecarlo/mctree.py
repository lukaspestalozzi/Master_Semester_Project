import abc

from game.utils import GameTree, GameTreeNode


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
