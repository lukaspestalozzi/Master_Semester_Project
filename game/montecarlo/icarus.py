"""
Implementation of the ICARUS Framework described in the Paper:
Monte Carlo Tree Search for games with Hidden Information and Uncertainty, by Daniel Whitehouse
"""

import abc
import random
from collections import Sequence
from array import array
from math import sqrt, log

import networkx as nx

from game.abstract import GameState
from game.tichu.new_.tichu_states import TichuInfoSet, TichuState
from game.tichu.tichu_actions import TichuAction


class MoveHistory(object):

    def __init__(self):
        super().__init__()
        self._states = list()
        self._actions = list()

    @property
    def last_state(self):
        return self._states[-1]

    def state_iter(self, from_=None):
        """
        :param from_: if not None, starts the iterator with the given state. Raises ValueError If the state is not in the history.
        :return: generator iterating over the states in the history (starting from first to last)
        """
        if from_ is None:
            yield from self._states
        else:
            yield from self._states[self._states.index(from_):]

    def action_iter(self):
        """

        :return: generator iterating over the actions in the history (starting from first to last)
        """
        yield from self._actions

    def state_action_iter(self, from_=None):
        """
        :param from_: if not None, starts the iterator with the given state. Raises ValueError If the state is not in the history.
        :return: generator yielding 2-tuples(state, action). Where the action is the action played in the state of None
        """
        if from_ is None:
            yield from zip(self._states, self._actions)
        else:
            idx = self._states.index(from_)
            yield from zip(self._states[idx:], self._actions[idx:])

    def append(self, state, action):
        self._states.append(state)
        self._actions.append(action)

    def __len__(self):
        return len(self._states)

    def __getitem__(self, index):
        return (self._states[index], self._actions[index])


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
        self.capture_contexts = set()

    def search(self, start_infoset: TichuInfoSet, iterations: int) -> TichuAction:
        # initialisation
        self.search_init(start_infoset)

        for iteration in range(iterations):
            # playout
            history = MoveHistory()
            root_state = start_infoset.determinization()
            state = root_state
            while not state.is_terminal:
                action = self.policy(history, state)
                history.append(state=state, action=action)
                next_state = state.next_state(action)
                state = next_state
            # state is terminal
            history.append(state=state, action=None)
            reward_vector = state.evaluate()

            # backpropagation
            for record, capture_context in self.capture(history, root_state):
                self.backpropagation(record, capture_context, reward_vector)
                if record not in self.records:
                    self.records.add(record)

            return self.best_action(start_infoset)

    @abc.abstractmethod
    def search_init(self, infoset: TichuInfoSet) -> None:
        """
        :param infoset:
        :return: 
        """

    @abc.abstractmethod
    def init_records(self) -> set:
        """
        
        :return: 
        """

    @abc.abstractmethod
    def policy(self, history: MoveHistory, state: TichuState) -> TichuAction:
        """
        
        :param history: 
        :param state: 
        :return: 
        """

    @abc.abstractmethod
    def capture(self, history: MoveHistory, root_state: TichuState) -> Sequence:
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
    def best_action(self, infoset: TichuInfoSet) -> TichuAction:
        """
        
        :param infoset: 
        :return: The best action from the given infoset.
        """


class BaseRecord(Record):
    """The Record used in the BaseIcarus Algorithm"""

    __slots__ = ()

    def __init__(self):
        init_reward_vector = array('l', [0, 0, 0, 0])  # 4 players
        super().__init__(array('l', [init_reward_vector, 0, 0]))  # triple (total reward vector, a number of visits, availability count)

    @property
    def total_reward(self):
        return self.info[0]

    def add_reward(self, amounts):
        """
        
        :param amounts: sequence of length 4
        :return: 
        """
        arr = self.info[0]
        assert len(arr) == len(amounts)
        for k in range(len(amounts)):
            arr[k] += amounts[k]

    @property
    def number_visits(self):
        return self.info[1]

    def increase_number_visits(self, amount=1):
        self.info[1] += amount

    @property
    def availability_count(self):
        return self.info[2]

    def increase_availability_count(self, amount=1):
        self.info[2] += amount

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
        # TODO speed (cache result)
        r = self.total_reward[p]
        n = self.number_visits
        m = self.availability_count
        return (r / n) + c * sqrt(log(m) / n)


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
        self.graph = nx.DiGraph(name='BaseGameGraph')

    def policy(self, history: MoveHistory, state: TichuState) -> TichuAction:
        if state.unique_hash() in self.graph:
            return self._tree_policy(history, state)
        else:
            return self._rollout_policy(history, state)

    def _tree_policy(self, history: MoveHistory, state: TichuState) -> TichuAction:
        """
        
        :param history: 
        :param state: Any state in the game_graph, but may be a leaf
        :return: The selected action
        """

        sid = state.unique_hash()
        nabo_action_gen = ((to, action) for from_, to, action
                           in self.graph.out_edges_iter(sid, data='action', default=None))
        # return uniformly at random from max utc
        max_val = 0
        max_nodes = set()
        for child_n, action in nabo_action_gen:
            val = child_n['record'].uct(p=child_n['state'].current_player())
            if val == float('inf'):
                return action  # TODO INFO: not really uniformly random, but faster
            if max_val == val:
                max_nodes.add((child_n, action))
            elif max_val < val:
                max_val = val
                max_nodes = {(child_n, action)}

        return random.choice(max_nodes)[1]

    def _rollout_policy(self, history, state) -> TichuAction:
        return state.random_action()

    def backpropagation(self, record: BaseRecord, capture_context, reward_vector: tuple) -> None:
        record.increase_availability_count()
        if capture_context:
            record.increase_number_visits()
            record.add_reward(reward_vector)

    def capture(self, history: MoveHistory, root_state: TichuState) -> Sequence:
        """
        Capture contexts can be either 'available' or 'visit'.
        'available' records have only their availability count increased, 
        while 'visit' also update their visit count and total reward.
        
        :param history: 
        :param root_state: 
        :return: generator yielding 3-tuples(record, bool (True if capture context is 'visit'), reward_vector)
        """
        reward_vector = history.last_state.reward_vector()
        for state, played_action in history.state_action_iter(from_=root_state):
            sid = state.unique_hash()
            if sid in self.graph:
                node = self.graph[sid]
                yield (node['record'], True, reward_vector)
                if played_action is not None:
                    for from_, to, action in self.graph.out_edges_iter(sid, data='action', default=None):
                        if played_action != action:
                            yield (to['record'], False, reward_vector)

    def best_action(self, infoset: TichuState) -> TichuAction:
        gen = ((to['record'].number_visits, action) for from_, to, action
               in self.graph.out_edges_iter(infoset.unique_hash(), data='action', default=None))
        return max(gen, key=lambda t: t[0])[1]

    def init_records(self) -> set:
        return set()

    def search_init(self, infoset: TichuInfoSet) -> None:
        self._add_new_node_if_not_yet_added(infoset)

    def _add_new_node_if_not_yet_added(self, state: GameState)->None:
        sid = state.unique_hash()
        if sid not in self.graph:
            self.graph.add_node(sid, attr_dict={'record': BaseRecord(), 'state': state})

    def _add_new_edge(self, from_state: TichuState, action: TichuAction, to_state: TichuState)->None:
        fsid = from_state.unique_hash()
        tsid = to_state.unique_hash()
        # TODO if the edge is already in the graph, updates the attr_dict. Should not be a problem? -> check again later.
        self.graph.add_edge(u=fsid, v=tsid, attr_dict={'action': action})

    def _expand_tree(self, leaf_state: TichuState) -> None:
        """
        Expand all possible actions from the leaf_state
        :param leaf_state: 
        :return: 
        """
        for action in leaf_state.possible_actions_gen():
            child = leaf_state.next_state(action)
            self._add_new_node_if_not_yet_added(child)
            self._add_new_edge(leaf_state, action, child)

