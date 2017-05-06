import uuid
from collections import defaultdict
from operator import itemgetter
from typing import Optional
import abc
import random
from math import sqrt, log
from time import time
import logging
import networkx as nx
import matplotlib.pyplot as plt

from game.tichu.new_.tichu_states import TichuState
from game.tichu.tichu_actions import TichuAction, PassAction
from game.utils import check_param, NodeID, RewardVector


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
        return "{self.__class__.__name__}(av:{self.availability_count}, v:{self.visit_count}, rewards:{self.total_reward} -> {av_reward})".format(self=self, av_reward=[(r/self.visit_count if self.visit_count > 0 else 0) for r in self.total_reward])


class InformationSetMCTS(object):
    """
    **Type:** Information Set MCTS
    
    **Selection:** UCB1
    
    **Simulation:** Uniform Random
    
    **Best Action:** Most Visited
    """

    def __init__(self):

        self.graph = nx.DiGraph(name='GameGraph')
        self.observer_id = None
        self._visited_records = set()
        self._available_records = set()

    def search(self, root_state: TichuState, observer_id: int, iterations: int, cheat: bool=False, clear_graph_on_new_root=True) -> TichuAction:
        logging.debug(f"started {self.__class__.__name__} with observer {observer_id}, for {iterations} iterations and cheat={cheat}")
        check_param(observer_id in range(4))
        self.observer_id = observer_id
        root_nid = self._graph_node_id(root_state)

        if root_nid not in self.graph and clear_graph_on_new_root:
            _ = self.graph.clear()
        else:
            logging.debug("Could keep the graph :)")
        self.add_root(root_state)

        iteration = 0
        while iteration < iterations:
            iteration += 1
            self._init_iteration()
            # logging.debug("iteration "+str(iteration))
            state = root_state.determinization(observer_id=self.observer_id, cheat=cheat)
            # logging.debug("Tree policy")
            leaf_state = self.tree_policy(state)
            # logging.debug("rollout")
            rollout_result = self.rollout_policy(leaf_state)
            # logging.debug("backpropagation")
            assert len(rollout_result) == 4
            self.backpropagation(reward_vector=rollout_result)

        action = self.best_action(root_state)
        logging.debug(f"size of graph after search: {len(self.graph)}")
        # self._draw_graph('./graphs/graph_{}.pdf'.format(time()))
        return action

    def _init_iteration(self)->None:
        self._visited_records = set()
        self._available_records = set()

    def _graph_node_id(self, state: TichuState) -> NodeID:
        return state.unique_infoset_id(self.observer_id)

    def add_child_node(self, from_nid: Optional[NodeID]=None, to_nid: Optional[NodeID]=None, action: Optional[TichuAction]=None) -> None:
        """
        Adds a node for each infoset (if not already in graph) and an edge from the from_infoset to the to_infoset
        
        Adds the node if the argument is not None (if from_nid is not None, adds a node with the nid=from_nid) etc.
        Adds the edge if no argument is None
        
        :param from_nid: 
        :param to_nid: 
        :param action: 
        :return: None
        """

        # assert from_infoset is None or isinstance(from_infoset, TichuInfoSet)
        # assert to_infoset is None or isinstance(to_infoset, TichuInfoSet)

        def add_node(nid: NodeID):
            self.graph.add_node(nid, attr_dict={'record': UCB1Record()})

        if from_nid is not None and from_nid not in self.graph:
            add_node(from_nid)

        if to_nid is not None and to_nid not in self.graph:
            add_node(to_nid)

        if action is not None and from_nid is not None and to_nid is not None:  # if all 3 are not none
            self.graph.add_edge(u=from_nid, v=to_nid, attr_dict={'action': action})

    def add_root(self, state: TichuState)->None:
        nid = self._graph_node_id(state)
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
            if not self.is_fully_expanded(curr_state):
                self.expand(curr_state)
                # logging.debug("tree_policy expand and return")
                return curr_state.next_state(self.tree_selection(curr_state))
            else:
                curr_state = curr_state.next_state(self.tree_selection(curr_state))

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

    def tree_selection(self, state: TichuState) -> TichuAction:
        """
        
        :param state:
        :return: 
        """
        # logging.debug("Tree selection")
        nid = self._graph_node_id(state)
        # store record for backpropagation
        rec = self.graph.node[nid]['record']
        self._visited_records.add(rec)

        # find max (return uniformly at random from max UCB1 value)
        poss_actions = set(state.possible_actions())
        max_val = -float('inf')
        max_actions = list()
        for _, to_nid, action in self.graph.out_edges_iter(nbunch=[nid], data='action', default=None):
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
        return next_action

    def rollout_policy(self, state: TichuState)->RewardVector:
        """
        Does a rollout from the given state and returns the reward vector
        
        :param state: 
        :return: the reward vector of this rollout
        """
        rollout_state = state
        while not rollout_state.is_terminal():
            rollout_state = rollout_state.next_state(rollout_state.random_action())
        return self.evaluate_state(rollout_state)

    def evaluate_state(self, state: TichuState)->RewardVector:
        """
        
        :param state: 
        :return: 
        """
        points = state.count_points()
        assert points[0] == points[2] and points[1] == points[3]
        # reward is the difference to the enemy team
        r0 = points[0] - points[1]
        r1 = r0 * -1
        return (r0, r1, r0, r1)

    def backpropagation(self, reward_vector: RewardVector)->None:
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

    def best_action(self, state: TichuState) -> TichuAction:
        """

        :param state: 
        :return: The best action to play from the given state
        """
        nid = self._graph_node_id(state)

        assert nid in self.graph
        assert self.graph.out_degree(nid) > 0

        possactions= state.possible_actions()

        max_a = next(iter(possactions))
        max_v = -float('inf')
        for _, to_nid, action in self.graph.out_edges_iter(nid, data='action', default=None):
            if action in possactions:
                rec = self.graph.node[to_nid]['record']
                val = rec.ucb[state.player_id]
                logging.debug(f"   {val}->{action}: {rec}")
                if val > max_v:
                    max_v = val
                    max_a = action

        return max_a

    def _draw_graph(self, outfilename):
        #from networkx.drawing.nx_agraph import graphviz_layout
        plt.clf()
        G = self.graph
        graph_pos = nx.spring_layout(G)
        #graph_pos = graphviz_layout(G)
        nx.draw_networkx_nodes(G, graph_pos, with_labels=False, node_size=30, node_color='red', alpha=0.3)
        nx.draw_networkx_edges(G, graph_pos, width=1, alpha=0.3, edge_color='green')

        edge_labels = nx.get_edge_attributes(self.graph, 'action')
        nx.draw_networkx_edge_labels(G, graph_pos, edge_labels=edge_labels, font_size=3)

        plt.savefig(outfilename)


class InformationSetMCTS_old_evaluation(InformationSetMCTS):
    """
    Same as InformationSetMCTS, but the evaluation uses the absolute points instead of the difference.
    """

    def evaluate_state(self, state: TichuState) -> RewardVector:
        points = state.count_points()
        assert points[0] == points[2] and points[1] == points[3]
        return points


class EpicISMCTS(InformationSetMCTS):

    def _graph_node_id(self, state: TichuState)->NodeID:
        return state.position_in_episode()


class ISMctsLGR(InformationSetMCTS):
    """
    **Type:** Information Set MCTS
    
    **Selection:** UCB1
    
    **Simulation:** LastGoodResponse (Moves of winning player gets stored and chosen in next rollout if applicable)
    
    **Best Action:** Most Visited
    """
    MOVE_BREAK = "MoveBreak"  # used to signalise the end of a trick in the made_moves attribute

    def __init__(self, *args, forgetting: bool=True, **kwargs):
        """
        
        :param args: 
        :param forgetting: if True, looser moves will be forgotten
        :param kwargs: 
        """
        super().__init__(*args, **kwargs)
        self.forgetting = forgetting
        self._lgr_map = defaultdict(lambda: [None, None, None, None])
        self._made_moves = list()

    def search(self, *args, **kwargs):
        self._lgr_map.clear()
        return super().search(*args, **kwargs)

    def _init_iteration(self):
        self._made_moves.clear()
        super()._init_iteration()

    def tree_selection(self, state: TichuState):
        if state.trick_on_table.is_empty():
            self._made_moves.append(self.MOVE_BREAK)
        action = super().tree_selection(state)
        if not isinstance(action, PassAction):  # exclude pass actions
            self._made_moves.append(action)
        return action

    def rollout_policy(self, state: TichuState) -> RewardVector:
        """
        Does a rollout from the given state and returns the reward vector

        :param state: 
        :return: the reward vector of this rollout
        """

        rollout_state = state
        last_action = None
        next_action = None
        while not rollout_state.is_terminal():
            if rollout_state.trick_on_table.is_empty():
                self._made_moves.append(self.MOVE_BREAK)

            if (last_action in self._lgr_map
                    and self._lgr_map[last_action] is not None
                    and self._lgr_map[last_action][rollout_state.player_id] in rollout_state.possible_actions()):  # only take possible actions
                next_action = self._lgr_map[last_action][rollout_state.player_id]
                # logging.debug("LGR hit: {}->{}".format(last_action, next_action))
            else:
                next_action = rollout_state.random_action()

            if not isinstance(next_action, PassAction):  # exclude pass actions
                self._made_moves.append(next_action)
            rollout_state = rollout_state.next_state(next_action)
            last_action = next_action
        return self.evaluate_state(rollout_state)

    def backpropagation(self, reward_vector: RewardVector, *args, **kwargs):
        super().backpropagation(reward_vector, *args, **kwargs)
        winners = {0, 2} if reward_vector[0] > reward_vector[1] else {1, 3}
        prev_action = self._made_moves.pop(0)
        for action in self._made_moves:
            if prev_action != self.MOVE_BREAK and action != self.MOVE_BREAK:
                if action.player_pos in winners:
                    self._lgr_map[prev_action][action.player_pos] = action
                elif self.forgetting and prev_action in self._lgr_map:
                    self._lgr_map[prev_action][action.player_pos] = None
            prev_action = action

        # logging.debug("Size of LGR cache: {}".format(len(self._lgr_map)))
        self._made_moves.clear()


class ISMctsEpigLGR(ISMctsLGR, EpicISMCTS):
    """
    **Type:** Information Set MCTS

    **Selection:** EPIC-UCB1

    **Simulation:** LastGoodResponse (Moves of winning player gets stored and chosen in next rollout if applicable)

    **Best Action:** Most Visited
    """
    pass
