"""
Implementation of the ICARUS Framework described in the Paper:
Monte Carlo Tree Search for games with Hidden Information and Uncertainty, by Daniel Whitehouse
"""

import abc
import random
from collections import Sequence
from math import sqrt, log
from time import time

import logging
import networkx as nx
import matplotlib.pyplot as plt

from game.tichu.new_.tichu_states import TichuState
from game.tichu.tichu_actions import TichuAction


class FrozenActionHistory(object):
    def __init__(self, actions=()):
        super().__init__()
        self._actions = tuple(actions)
        self._unique_id_cache = None

    @property
    def last_action(self):
        try:
            return self._actions[-1]
        except IndexError:
            return None

    def action_iter(self):
        """

        :return: generator iterating over the actions in the history (starting from first to last)
        """
        yield from self._actions

    def appended(self, action):
        """
        
        :param action: 
        :return: A new FrozenActionHistory with the given action appended
        """
        return FrozenActionHistory(actions=self._actions+(action,))

    def unique_id(self) -> str:
        """
        A string that has following property: 
        
        - A.unique_id() == B.unique_id() implies A == B
        - A.unique_id() != B.unique_id() implies A != B
        
        :return: A unique string for this instance 
        """
        return '.'.join(a.unique_id() for a in self._actions)

    def __repr__(self):
        return '->'.join((str(e) for e in self._actions))

    def __len__(self):
        return len(self._actions)


class StateActionHistory(object):

    def __init__(self, states: list=list(), actions: list=list()):
        super().__init__()
        self._actions = states
        self._states = actions

    @property
    def last_state(self):
        try:
            return self._states[-1]
        except IndexError:
            return None

    @property
    def last_action(self):
        try:
            return self._actions[-1]
        except IndexError:
            return None

    def action_iter(self):
        """

        :return: generator iterating over the actions in the history (starting from first to last)
        """
        yield from self._actions

    def to_frozen_action_history(self, appended=None) -> FrozenActionHistory:
        """
        :param appended: If not none, returns the frozenActionHistory with the given action appended
        :return: 
        """
        accs = self._actions
        if appended is not None:
            accs = accs + [appended]
        return FrozenActionHistory(accs)

    def append(self, state, action):
        self._states.append(state)
        self._actions.append(action)

    def state_iter(self, from_=None):
        """
        :param from_: if not None, starts the iterator with the given state. Raises ValueError If the state is not in the history.
        :return: generator iterating over the states in the history (starting from first to last)
        """
        if from_ is None:
            yield from self._states
        else:
            yield from self._states[self._states.index(from_):]

    def state_action_iter(self, from_=None):
        """
        :param from_: if not None, starts the iterator with the given state. Raises ValueError If the state is not in the history.
        :return: generator yielding 2-tuples(state, action). Where the action is the action played in the state, or None (if it is the last state)
        """
        if from_ is None:
            yield from zip(self._states, self._actions)
        else:
            idx = self._states.index(from_)
            yield from zip(self._states[idx:], self._actions[idx:])

    def copy(self):
        return StateActionHistory(states=list(self._states), actions=list(self._actions))

    def __getitem__(self, index):
        return (self._states[index], self._actions[index])

    def __repr__(self):
        return '->'.join((str(e) for e in self.state_action_iter()))

    def __len__(self):
        return len(self._actions)


class Record(object):

    __slots__ = ('_info',)

    def __init__(self, info):
        self._info = info
        
    @property
    def info(self):
        return self._info

    @info.setter
    def info(self, new_info):
        self._info = new_info
    

class Icarus(object, metaclass=abc.ABCMeta):

    def __init__(self):
        self.records = self.init_records()

    def search(self, start_infoset: TichuState, iterations: int, cheat: bool=False) -> TichuAction:
        logging.debug(f"Starting Icarus search for {iterations} iterations; cheating: {cheat}")
        # initialisation
        base_history = self.search_init(start_infoset)

        for iteration in range(iterations):
            # playout
            history = base_history.copy()
            root_state = start_infoset.determinization(observer_id=start_infoset.player_id, cheat=cheat)
            state = root_state
            while not state.is_terminal():
                action = self.policy(history=history, state=state)
                history.append(state=state, action=action)
                next_state = state.next_state(action, infoset=True)
                state = next_state

            # state is now terminal
            history.append(state=state, action=None)
            reward_vector = state.reward_vector()

            # backpropagation
            for record, capture_context in self.capture(history, root_state):
                self.backpropagation(record, capture_context, reward_vector)

        return self.best_action(start_infoset)

    @abc.abstractmethod
    def search_init(self, infoset: TichuState) -> StateActionHistory:
        """
        Called before each search starts. The root-set of the search is the given infoset.
        
        Must return a StateActionHistory, which is then used as a 'base' history leading to the given infoset
        
        :param infoset:
        :return: The StateActionHistory leading to the infoset.
        """

    @abc.abstractmethod
    def init_records(self) -> set:
        """
        
        :return: 
        """

    @abc.abstractmethod
    def policy(self, history: StateActionHistory, state: TichuState) -> TichuAction:
        """
        
        :param history: 
        :param state: 
        :return: 
        """

    @abc.abstractmethod
    def capture(self, history: StateActionHistory, root_state: TichuState) -> Sequence:
        """
        
        :param history: 
        :param root_state: 
        :return: sequence of tuples(record, capture context) to be updated in the backpropagation function
        """

    @abc.abstractmethod
    def backpropagation(self, record: Record, capture_context, reward_vector: tuple) -> None:
        """
        Changes the record based on the given capture_context and reward_vector
        
        :param record: 
        :param capture_context: 
        :param reward_vector: 
        :return: None
        """

    @abc.abstractmethod
    def best_action(self, infoset: TichuState) -> TichuAction:
        """
        
        :param infoset: 
        :return: The best action from the given infoset.
        """


class BaseRecord(Record):
    """The Record used in the BaseIcarus Algorithm"""

    __slots__ = ("_utc_cache",)

    def __init__(self):
        init_reward_vector = [0, 0, 0, 0]  # 4 players
        super().__init__([init_reward_vector, 0, 0])  # triple (total reward vector, a number of visits, availability count)
        self._utc_cache = None

    @property
    def total_reward(self):
        return self._info[0]

    def add_reward(self, amounts):
        """
        
        :param amounts: sequence of length 4
        :return: 
        """
        self._utc_cache = None
        arr = self._info[0]
        assert len(arr) == len(amounts)
        for k in range(len(amounts)):
            arr[k] += amounts[k]

    @property
    def number_visits(self):
        return self._info[1]

    def increase_number_visits(self, amount=1):
        self._utc_cache = None
        self._info[1] += amount

    @property
    def availability_count(self):
        return self._info[2]

    def increase_availability_count(self, amount=1):
        self._utc_cache = None
        self._info[2] += amount

    def uct(self, p, c=0.7):
        """
        The UCT value is defined as:
        (r / n) + c * sqrt(log(m) / n)
        where r is the total reward, n the visit count of this record and m the availability count and c is a exploration/exploitation therm
        
        if either n or m are 0, the UCT value is infinity (float('inf'))
        :param p: The index of the player in the reward_vector
        :param c: 
        :return: The UCT value of this record
        """
        if self._utc_cache is not None:
            return self._utc_cache
        r = self.total_reward[p]
        n = self.number_visits
        m = self.availability_count
        if n == 0 or m == 0:
            res = float('inf')
        else:
            res = (r / n) + c * sqrt(log(m) / n)
        self._utc_cache = res
        return res


class BaseIcarus(Icarus):
    """
    Equivalent to UCT (perfect information) 
    and MO-ISMCTS with UCB1 selection policy in imperfect information
    using Icarus framework
    
    From the paper:
    The resulting algorithm is equivalent to UCT in the perfect information case and MO-
    ISMCTS with the UCB1 selection policy in the imperfect information case. The
    algorithm uses reward vectors and assumes that each player tries to maximise
    his own reward in a max^n fashion, thus the algorithm can handle
    games with κ > 2 players as well as single-player and two-player games.
    
    Description:
    Each history has its own record (Base-1), and the information associated
    with a record is a total reward, a number of visits and an availability count
    (Base-2, Base-3). 
    The policy is defined to use the subset-armed UCB1 algorithm (Base-4). 
    During expansion all unexpanded actions have n = 0 and thus
    UCB1 value ∞, and so the policy chooses between them uniformly. Similarly
    during simulation, all actions have UCB1 value ∞ and so the simulation policy is
    uniform random. The capture function specifies that the records to be updated
    during backpropagation are those that were selected, and those that were avail-
    able to be selected due to being compatible with the current determinization;
    this is restricted to the portion of the playout corresponding to selection and
    expansion, i.e. the first t_e actions (Base-6). 
    These two collections of records are labelled with contexts ψ_visit and ψ_avail 
    respectively (Base-5). Selected records have their rewards, visits and availabilities 
    updated in the natural way: the simulation reward is added to the record’s total reward, 
    and the visit and availability counts are incremented by 1. 
    Available records have their availability count incremented by 1, 
    with reward and visit count remaining unchanged (Base-7).
    
    """

    def __init__(self):
        super().__init__()
        self.graph = nx.DiGraph(name='BaseIcarus-GameGraph')
        self._expanded = False  # stores whether the tree was already expanded in this search round
        # stores the visited and possible records for backpropagation
        self._possible = set()
        self._visited = set()

    def policy(self, history: StateActionHistory, state: TichuState) -> TichuAction:
        if state in self.graph and not self._expanded:
            if self._must_expand(state=state):
                self._expanded = True
                self._expand_tree(leaf_state=state)
                logging.debug('expanding tree')

            return self._tree_policy(history, state)
        else:
            return self._rollout_policy(history, state)

    def _tree_policy(self, history: StateActionHistory, state: TichuState) -> TichuAction:
        """
        
        :param history: 
        :param state: Any Game-state in the game_graph, but may be a leaf
        :return: The selected action
        """

        self._visited.add(state)

        # find max (return uniformly at random from max utc)
        poss_actions = set(state.possible_actions())
        max_val = 0
        max_actions = list()
        for _, to_infoset, action in self.graph.out_edges_iter(nbunch=[state], data='action', default=None):
            if action in poss_actions:
                child_n = self.graph.node[to_infoset]
                self._possible.add(to_infoset)
                val = child_n['record'].uct(p=to_infoset.player_id)
                if max_val == val:
                    max_actions.append(action)
                elif max_val < val:
                    max_val = val
                    max_actions = [action]

        ret = random.choice(max_actions)
        # logging.debug(f"tree policy -> {ret}")
        return ret

    def _rollout_policy(self, history: StateActionHistory, state: TichuState) -> TichuAction:
        ret = state.random_action()
        # logging.debug(f"rollout policy -> {ret}")
        return ret

    def capture(self, history: StateActionHistory, root_state: TichuState) -> tuple:
        """
        Capture contexts can be either 'available' or 'visit'.
        'available' records have only their availability count increased, 
        while 'visit' also update their visit count and total reward.
        
        :param history: 
        :param root_state: 
        :return: generator yielding 2-tuples(record, bool (True if capture context is 'visit'))
        """
        for infoset in self._possible - self._visited:  # remove visited from possible.
            yield (self.graph.node[infoset]['record'], False)

        for infoset in self._visited:
            yield (self.graph.node[infoset]['record'], True)

        self._possible.clear()
        self._visited.clear()
        self._expanded = False

    def backpropagation(self, record: BaseRecord, capture_context, reward_vector: tuple) -> None:
        record.increase_availability_count()
        if capture_context:
            record.increase_number_visits()
            record.add_reward(reward_vector)
        if record not in self.records:
            self.records.add(record)

    def best_action(self, infoset: TichuState) -> TichuAction:
        val_action = [(self.graph.node[to]['record'].number_visits, action) for from_, to, action in self.graph.out_edges_iter(infoset, data='action', default=None)]
        return max(val_action)[1]

    def init_records(self) -> set:
        return set()

    def search_init(self, infoset: TichuState) -> StateActionHistory:
        self._expanded = False
        self._possible = set()
        self._visited = set()

        # Currently creates new graph for every search, TODO make graph available for the whole game
        self._draw_graph(f"./graphs/graph_{time()}.png")

        logging.debug(f"size of graph: {len(self.graph)}")
        nodes = [n for n in self.graph.nodes_iter() if n == infoset]

        if len(nodes):
            print(' Hit a node :) =================================================================================')
        else:
            self.graph.clear()
        self._add_new_node_if_not_yet_added(infoset=infoset)
        return StateActionHistory()

    def _add_new_node_if_not_yet_added(self, infoset: TichuState, **additional_node_attrs)->None:
        if infoset not in self.graph:
            self.graph.add_node(infoset, attr_dict={'record': BaseRecord(), **additional_node_attrs})

    def _add_new_edge(self, from_infoset: TichuState, to_infoset: TichuState, action: TichuAction)->None:
        # TODO if the edge is already in the graph, updates the attr_dict. Should not be a problem? -> check again later.
        self.graph.add_edge(u=from_infoset, v=to_infoset, attr_dict={'action': action})

    def _must_expand(self, state: TichuState):
        if self._expanded:
            return False
        poss_acs = set(state.possible_actions())
        existing_actions = {action for _, _, action in self.graph.out_edges_iter(nbunch=[state], data='action', default=None)}
        if len(existing_actions) < len(poss_acs):
            return True

        # if all possible actions already exist -> must not expand
        return not poss_acs.issubset(existing_actions)

    def _expand_tree(self, leaf_state: TichuState) -> None:
        """
        Expand all possible actions from the leaf_state
        
        :param history: The StateActionHistory up to the leaf_state. leaf_state not included. Following should hold: history.last_state.next_state(history.last_action) == leaf_state
        :param leaf_state: 
        :return: None
        """

        # logging.debug('expanding tree')
        leaf_infostate = TichuState.from_tichustate(leaf_state)

        for action in leaf_state.possible_actions_gen():
            to_infoset = TichuState.from_tichustate(leaf_state.next_state(action))
            self._add_new_node_if_not_yet_added(infoset=to_infoset)
            self._add_new_edge(from_infoset=leaf_infostate, to_infoset=to_infoset, action=action)

    def _draw_graph(self, outfilename):
        #from networkx.drawing.nx_agraph import graphviz_layout
        plt.clf()
        G = self.graph
        graph_pos = nx.spectral_layout(G)
        #graph_pos = graphviz_layout(G)
        nx.draw_networkx_nodes(G, graph_pos, with_labels=False, node_size=50, node_color='red', alpha=0.3)
        nx.draw_networkx_edges(G, graph_pos, width=1, alpha=0.3, edge_color='green')

        edge_labels = nx.get_edge_attributes(self.graph, 'action')
        nx.draw_networkx_edge_labels(G, graph_pos, edge_labels=edge_labels, font_size=6)

        plt.savefig(outfilename)



