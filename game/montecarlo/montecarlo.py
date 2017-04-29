import uuid
from operator import itemgetter
from typing import Optional
from game.tichu.new_.tichu_states import TichuInfoSet
import abc
import random
from math import sqrt, log
from time import time
import logging
import networkx as nx
import matplotlib.pyplot as plt

from game.tichu.new_.tichu_states import TichuState
from game.tichu.tichu_actions import TichuAction
from game.utils import check_param


class UCB1Record(object):
    """The Record to store UTC infos"""

    __slots__ = ("_utc_cache", "total_reward", "visit_count", "availability_count", "_uuid")

    def __init__(self):
        self.total_reward = [0, 0, 0, 0]
        self.visit_count = 0
        self.availability_count = 0
        self._utc_cache = None
        self._uuid = uuid.uuid4()

    def add_reward(self, amounts):
        """

        :param amounts: sequence of length 4
        :return: 
        """
        self._utc_cache = None
        assert len(self.total_reward) == len(amounts) == 4
        for k in range(len(amounts)):
            self.total_reward[k] += amounts[k]

    def increase_number_visits(self, amount=1):
        self._utc_cache = None
        self.visit_count += amount

    def increase_availability_count(self, amount=1):
        self._utc_cache = None
        self.availability_count += amount

    def ucb(self, p: int, c: float=0.7):
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
        n = self.visit_count
        av = self.availability_count
        if n == 0 or av == 0:
            res = float('inf')
        else:
            res = (r / n) + c * sqrt(log(av) / n)
        self._utc_cache = res
        return res

    def __repr__(self):
        return "{self.__class__.__name__} uuid:{self._uuid} (available:{self.availability_count}, visits:{self.visit_count}, rewards: {self.total_reward})".format(self=self)

    def __str__(self):
        return "{self.__class__.__name__}(av:{self.availability_count}, v:{self.visit_count}, rewards:{self.total_reward})".format(self=self)


NodeID = str


class InformationSetMCTS(object):
    """
    
    """

    def __init__(self):

        self.graph = nx.DiGraph(name='BaseIcarus-GameGraph')
        self.observer_id = None
        self._visited_records = set()
        self._available_records = set()

    def search(self, start_infoset: TichuInfoSet, observer_id: int, iterations: int, cheat: bool=False) -> TichuAction:
        logging.debug(f"started InformationSetMCTS with observer {observer_id}, for {iterations} iterations and cheat={cheat}")
        check_param(observer_id in range(4))
        self.observer_id = observer_id

        if start_infoset not in self.graph:
            _ = self.graph.clear()
            self.add_root(start_infoset)
        else:
            logging.debug("Could keep the graph :)")

        iteration = 0
        while iteration < iterations:
            iteration += 1
            self._init_iteration()
            # logging.debug("iteration "+str(iteration))
            start_state = start_infoset.determinization(observer_id=self.observer_id, cheat=cheat)
            # logging.debug("Tree policy")
            leaf_state = self.tree_policy(start_state)
            # logging.debug("rollout")
            rollout_result = self.rollout_policy(leaf_state)
            # logging.debug("backpropagation")
            assert len(rollout_result) == 4
            self.backpropagation(reward_vector=rollout_result)

        action = self.best_action(start_infoset)
        logging.debug(f"size of graph after search: {len(self.graph)}")
        return action

    def _init_iteration(self)->None:
        self._visited_records = set()
        self._available_records = set()

    def _graph_node_id(self, state: TichuState) -> NodeID:
        return state.unique_infoset_id(self.observer_id)
        """
        if isinstance(state, TichuInfoSet):
            return state
        else:
            return TichuInfoSet.from_tichustate(state, self.observer_id)
        """

    def add_child_node(self, from_nid: Optional[NodeID], to_nid: Optional[NodeID], action: Optional[TichuAction]) -> None:
        """
        Adds a node for each infoset (if not already in graph) and an edge from the from_infoset to the to_infoset
        
        :param from_nid: 
        :param to_nid: 
        :param action: 
        :return: None
        """

        # assert from_infoset is None or isinstance(from_infoset, TichuInfoSet)
        # assert to_infoset is None or isinstance(to_infoset, TichuInfoSet)

        def add_node(nid: str):
            self.graph.add_node(nid, attr_dict={'record': UCB1Record()})

        if from_nid is not None and from_nid not in self.graph:
            add_node(from_nid)

        if to_nid is not None and to_nid not in self.graph:
            add_node(to_nid)

        if action is not None and from_nid is not None and to_nid is not None:  # if all 3 are not none
            self.graph.add_edge(u=from_nid, v=to_nid, attr_dict={'action': action})

    def add_root(self, nid: NodeID)->None:
        if not isinstance(nid, NodeID):
            nid = self._graph_node_id(nid)
        self.add_child_node(from_nid=nid, to_nid=None, action=None)

    def expand(self, leaf_state: TichuState)->None:
        leaf_nid = self._graph_node_id(leaf_state)
        for action in leaf_state.possible_actions_gen():
            to_nid = self._graph_node_id(state=leaf_state.next_state(action))
            self.add_child_node(from_nid=leaf_nid, to_nid=to_nid, action=action)

    def tree_policy(self, state: TichuState) -> TichuState:
        """
        Traverses the Tree and selects a leaf-node to be expanded (and expands it).
        
        :param state: 
        :return: The leaf_state used for simulation (rollout) policy
        """
        curr_state = state
        while not curr_state.is_terminal():
            isid = self._graph_node_id(curr_state)
            if not self.is_fully_expanded(isid):
                self.expand(isid)
                # logging.debug("tree_policy expand and return")
                return self.tree_selection(isid)
            else:
                curr_state = self.tree_selection(isid)

        # logging.debug("tree_policy return (state is terminal)")
        return curr_state

    def is_fully_expanded(self, state: TichuState) -> bool:
        poss_acs = set(state.possible_actions())
        existing_actions = {action for _, _, action in
                            self.graph.out_edges_iter(nbunch=[self._graph_node_id(state)], data='action', default=None)}
        if len(existing_actions) < len(poss_acs):
            return False

        # if all possible actions already exist -> is fully expanded
        return poss_acs.issubset(existing_actions)

    def tree_selection(self, state: TichuState) -> TichuState:
        """
        
        :param state:
        :return: 
        """
        # logging.debug("Tree selection")
        isid = self._graph_node_id(state)
        # store record for backpropagation
        rec = self.graph.node[isid]['record']
        self._visited_records.add(rec)
        self._available_records.add(rec)

        # find max (return uniformly at random from max UCB1 value)
        poss_actions = set(state.possible_actions())
        max_val = -float('inf')
        max_actions = list()
        for _, to_nid, action in self.graph.out_edges_iter(nbunch=[isid], data='action', default=None):
            # logging.debug("Tree selection looking at "+str(action))
            if action in poss_actions:
                child_record = self.graph.node[to_nid]['record']
                self._available_records.add(child_record)
                val = child_record.ucb(p=state.player_id)
                if max_val == val:
                    max_actions.append(action)
                elif max_val < val:
                    max_val = val
                    max_actions = [action]

        next_action = random.choice(max_actions)
        # logging.debug(f"Tree selection -> {next_action}")
        return state.next_state(next_action)

    def rollout_policy(self, state: TichuState)->tuple:
        """
        Does a rollout from the given state and returns the reward vector
        
        :param state: 
        :return: the reward vector of this rollout
        """
        rollout_state = state
        while not rollout_state.is_terminal():
            rollout_state = rollout_state.next_state(rollout_state.random_action())
        return self.evaluate_state(rollout_state)

    def evaluate_state(self, state: TichuState)->tuple:
        """
        
        :param state: 
        :return: 
        """
        points = state.count_points()

        assert points[0] == points[2] and points[1] == points[3], str(points)
        return points

    def backpropagation(self, reward_vector: tuple)->None:
        """
        Called at the end with the rollout result.
        
        Updates the search state.
        
        :param reward_vector: 
        :return: 
        """

        assert self._visited_records.issubset(self._available_records)

        # logging.debug(f"visited: {len(self._visited_records)}, avail: {len(self._available_records)})")
        for record in self._available_records:
            record.increase_availability_count()

        for record in self._visited_records:
            # logging.debug("record: {}".format(record))
            record.increase_number_visits()
            record.add_reward(reward_vector)

    def best_action(self, infoset: TichuInfoSet) -> TichuAction:
        """
        
        :param infoset: 
        :return: The best action to play from the given infoset
        """
        max_a = None
        max_v = -float('inf')
        for _, to_nid, action in self.graph.out_edges_iter(infoset, data='action', default=None):
            rec = self.graph.node[to_nid]['record']
            if rec.visit_count > max_v:
                max_v = rec.visit_count
                max_a = action

            # logging.debug(f"   {action}: {rec}")

        # logging.debug(f"best action -> {max_a}")
        return max_a


class MCTS(InformationSetMCTS):
    """
    'Normal' MCTS. One searchtree for each determinization.
    
    """
    pass

