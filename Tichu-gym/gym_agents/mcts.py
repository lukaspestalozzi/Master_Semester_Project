import uuid
import abc
import itertools
import logging
import networkx as nx
import matplotlib.pyplot as plt
import random
import atexit

from collections import defaultdict
from functools import lru_cache
from operator import itemgetter
from typing import Optional, Union, Hashable, NewType, TypeVar, Tuple, List
from math import sqrt, log
from time import time

from profilehooks import timecall, profile

from gym_tichu.envs.internals import TichuState, PlayerAction, PassAction, Trick, CardSet, HandCards
from gym_tichu.envs.internals.utils import check_param, flatten

logger = logging.getLogger(__name__)

__all__ = ('InformationSetMCTS', 'InformationSetMCTS_absolute_evaluation', 'EpicISMCTS', 'ISMctsLGR', 'ISMctsEpicLGR')

NodeID = NewType('NodeID', Hashable)
RewardVector = NewType('RewardVector', Tuple[int, int, int, int])


@lru_cache(maxsize=2**16)  # 64k CacheInfo(hits=2274111, misses=43745, maxsize=65536, currsize=43745)
def _uid_trick(trick: Trick) -> str:
    return ''.join(map(str, trick.combinations()))  # TODO improve


@lru_cache(maxsize=2048)  # CacheInfo(hits=329379, misses=1767, maxsize=2048, currsize=1767)
def _uid_cardset(cards: CardSet) -> str:
    return ''.join(map(str, cards))  # TODO improve


@lru_cache(maxsize=2**16)  # with 131k (2**17):  CacheInfo(hits=233368, misses=331146, maxsize=131072, currsize=131072)
def unique_infoset_id(state: TichuState, observer_id: int) -> str:
    return '|'.join(
            map(str, (
                state.player_pos,
                state.wish.height if state.wish else 'NoWish',
                state.ranking,
                sorted(state.announced_tichu),
                sorted(state.announced_grand_tichu),
                _uid_trick(state.trick_on_table),
                *map(_uid_trick, state.won_tricks.iter_all_tricks()),
                *map(len, state.handcards),  # length of handcards.
                _uid_cardset(state.handcards[observer_id])
            ))
        )


@lru_cache(maxsize=2048)
def position_in_episode(state: TichuState)->str:
    # TODO try: - with/without passactions; - include/remove playerid; - use the trick and not history; use 'generic' actions (eg. pair(As) instead of Pair(As1, As2))

    # history is the current trick on the table (only played combinations)
    if state.trick_on_table.is_empty():
        return "ROOT_" + str(state.player_id)
    else:
        return '->'.join(map(str, state.trick_on_table.combinations()))


def _atexit_caches_info():
    """
    Printing the info of cached functions on program exit.
    """
    caches = [_uid_trick, _uid_cardset, unique_infoset_id, position_in_episode]
    print("=============== cache infos ===================")
    for cache in caches:
        print(cache.__name__, ': ', cache.cache_info())
    print()

atexit.register(_atexit_caches_info)


class UCB1Record(object):
    """The Record to store UTC infos"""

    __slots__ = ("_ucb_cache", "total_reward", "visit_count", "availability_count", "_uuid")

    def __init__(self):
        self.total_reward = [0, 0, 0, 0]
        self.visit_count = 0
        self.availability_count = 0
        self._ucb_cache = None
        self._uuid = uuid.uuid4()

    def add_reward(self, amounts):
        """

        :param amounts: sequence of length 4
        :return: 
        """
        self._ucb_cache = None
        assert len(self.total_reward) == len(amounts) == 4
        for k in range(len(amounts)):
            self.total_reward[k] += amounts[k]

    def increase_number_visits(self, amount=1):
        self._ucb_cache = None
        self.visit_count += amount

    def increase_availability_count(self, amount=1):
        self._ucb_cache = None
        self.availability_count += amount

    def ucb(self, p: int, c: float = 0.7)->Union[int, float]:
        """
        The UCT value is defined as:
        (r / n) + c * sqrt(log(m) / n)
        where r is the total reward, n the visit count of this record and m the availability count and c is a exploration/exploitation therm

        if either n or m are 0, the UCT value is infinity (float('inf'))
        :param p: The index of the player in the reward_vector
        :param c: 
        :return: The UCT value of this record
        """
        if self._ucb_cache is not None:
            return self._ucb_cache
        r = self.total_reward[p]
        n = self.visit_count
        av = self.availability_count
        if n == 0 or av == 0:
            res = float('inf')
        else:
            res = (r / n) + c * sqrt(log(av) / n)
        self._ucb_cache = res
        return res

    def __repr__(self):
        return "{me.__class__.__name__} uuid:{me._uuid} (available:{me.availability_count}, visits:{me.visit_count}, rewards: {me.total_reward})".format(me=self)

    def __str__(self):
        return "{me.__class__.__name__}(av:{me.availability_count}, v:{me.visit_count}, rewards:{me.total_reward} -> {av_reward})".format(
                me=self, av_reward=[(r / self.visit_count if self.visit_count > 0 else 0) for r in self.total_reward])


class MCTS(object, metaclass=abc.ABCMeta):

    @abc.abstractmethod
    def search(self, root_state: TichuState, observer_id: int, iterations: int, cheat: bool = False):
        pass


class InformationSetMCTS(MCTS):
    """
    **Type:** Information Set MCTS
    
    **determinisation:** Uniformely Random

    **Selection:** UCB1

    **Simulation:** Uniform Random

    **Best Action:** Most Visited
    """

    def __init__(self):
        self.graph = nx.DiGraph(name='GameGraph')
        self.observer_id = None
        self._visited_records = set()
        self._available_records = set()

    @timecall(immediate=False)
    def search(self, root_state: TichuState, observer_id: int, iterations: int, cheat: bool = False, clear_graph_on_new_root=True) -> PlayerAction:
        logger.debug(f"Started {self.__class__.__name__} with observer {observer_id}, for {iterations} iterations and cheat={cheat}")
        check_param(observer_id in range(4))

        root_state = TichuState(*root_state, allow_tichu=False, allow_wish=False)  # Don't allow tichus or wishes in the simulation

        self.observer_id = observer_id
        root_nid = self._graph_node_id(root_state)

        if root_nid not in self.graph and clear_graph_on_new_root:
            self.graph.clear()
        else:
            logger.debug("Could keep the graph :)")
        self.add_root(root_state)

        iteration = 0
        while iteration < iterations:
            iteration += 1
            self._init_iteration()
            # logger.debug("iteration "+str(iteration))
            state = self.determinization(state=root_state, cheat=cheat)
            # logger.debug("Tree policy")
            leaf_state = self.tree_policy(state)
            # logger.debug("rollout")
            rollout_result = self.rollout_policy(leaf_state)
            # logger.debug("backpropagation")
            assert len(rollout_result) == 4
            self.backpropagation(reward_vector=rollout_result)

        action = self.best_action(root_state)
        logger.debug(f"size of graph after search: {len(self.graph)}")
        # self._draw_graph('./graphs/graph_{}.pdf'.format(time()))
        return action

    @property
    def info(self):
        return "MCTS: {me.__class__.__name__}, observer: {me.observer_id}".format(me=self)

    def _init_iteration(self) -> None:
        self._visited_records = set()
        self._available_records = set()

    def _graph_node_id(self, state: TichuState) -> NodeID:
        return unique_infoset_id(state=state, observer_id=self.observer_id)

    def determinization(self, state: TichuState, cheat: bool)->TichuState:
        if cheat:
            return state
        else:
            unknown_cards = list(flatten((hc for idx, hc in enumerate(state.handcards) if idx != self.observer_id)))
            # logging.debug('unknown cards: '+str(unknown_cards))
            random.shuffle(unknown_cards)
            new_hc_list = [None]*4
            for idx in range(4):
                if idx == self.observer_id:
                    new_hc_list[idx] = list(state.handcards[idx])
                else:
                    l = len(state.handcards[idx])
                    det_cards = unknown_cards[:l]
                    unknown_cards = unknown_cards[l:]
                    new_hc_list[idx] = det_cards

            # print(*map(str, flatten(new_hc_list)))
            new_handcards = HandCards(*new_hc_list)
            assert all(c is not None for c in new_hc_list)  # all players have handcards
            assert sum(len(hc) for hc in new_handcards) == sum(len(hc) for hc in state.handcards)  # no card is lost
            assert new_handcards[self.observer_id] == state.handcards[self.observer_id]  # observers handcards have not been changed
            ts = state.change(handcards=new_handcards)
            return ts

    def add_child_node(self, from_nid: Optional[NodeID] = None, to_nid: Optional[NodeID] = None, action: Optional[PlayerAction] = None) -> None:
        """
        Adds a node for each infoset (if not already in graph) and an edge from the from_infoset to the to_infoset

        Adds the node if the argument is not None (if from_nid is not None, adds a node with the nid=from_nid) etc.
        Adds the edge if no argument is None

        :param from_nid: 
        :param to_nid: 
        :param action: 
        :return: None
        """

        def add_node(nid: NodeID):
            self.graph.add_node(nid, attr_dict={'record': UCB1Record()})

        if from_nid is not None and from_nid not in self.graph:
            add_node(from_nid)

        if to_nid is not None and to_nid not in self.graph:
            add_node(to_nid)

        if action is not None and from_nid is not None and to_nid is not None:  # if all 3 are not none
            self.graph.add_edge(u=from_nid, v=to_nid, attr_dict={'action': action})

    def add_root(self, state: TichuState) -> None:
        nid = self._graph_node_id(state)
        self.add_child_node(from_nid=nid, to_nid=None, action=None)

    def expand(self, leaf_state: TichuState) -> None:
        leaf_nid = self._graph_node_id(leaf_state)
        for action in leaf_state.possible_actions_gen():
            to_nid = self._graph_node_id(state=leaf_state.next_state(action))
            self.add_child_node(from_nid=leaf_nid, to_nid=to_nid, action=action)

    @timecall(immediate=False)
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
                # logger.debug("tree_policy expand and return")
                return curr_state.next_state(self.tree_selection(curr_state))
            else:
                curr_state = curr_state.next_state(self.tree_selection(curr_state))

        # logger.debug("tree_policy return (state is terminal)")
        return curr_state

    def is_fully_expanded(self, state: TichuState) -> bool:
        poss_acs = set(state.possible_actions())
        existing_actions = {action for _, _, action in
                            self.graph.out_edges_iter(nbunch=[self._graph_node_id(state)], data='action', default=None)}
        if len(existing_actions) < len(poss_acs):
            return False

        # if all possible actions already exist -> is fully expanded
        return poss_acs.issubset(existing_actions)

    def tree_selection(self, state: TichuState) -> PlayerAction:
        """

        :param state:
        :return: 
        """
        # logger.debug("Tree selection")
        nid = self._graph_node_id(state)
        # store record for backpropagation
        rec = self.graph.node[nid]['record']
        self._visited_records.add(rec)
        self._available_records.add(rec)

        # find max (return uniformly at random from max UCB1 value)
        poss_actions = set(state.possible_actions())
        max_val = -float('inf')
        max_actions = list()
        for _, to_nid, action in self.graph.out_edges_iter(nbunch=[nid], data='action', default=None):
            # logger.debug("Tree selection looking at "+str(action))
            if action in poss_actions:
                child_record = self.graph.node[to_nid]['record']
                self._available_records.add(child_record)
                val = child_record.ucb(p=state.player_pos)
                if max_val == val:
                    max_actions.append(action)
                elif max_val < val:
                    max_val = val
                    max_actions = [action]

        next_action = random.choice(max_actions)
        # logger.debug(f"Tree selection -> {next_action}")
        return next_action

    @timecall(immediate=False)
    def rollout_policy(self, state: TichuState) -> RewardVector:
        """
        Does a rollout from the given state and returns the reward vector

        :param state: 
        :return: the reward vector of this rollout
        """
        rollout_state = state
        while not rollout_state.is_terminal():
            rollout_state = rollout_state.next_state(rollout_state.random_action())
        return self.evaluate_state(rollout_state)

    def evaluate_state(self, state: TichuState) -> RewardVector:
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

    @timecall(immediate=False)
    def backpropagation(self, reward_vector: RewardVector) -> None:
        """
        Called at the end with the rollout result.

        Updates the search state.

        :param reward_vector: 
        :return: 
        """

        assert self._visited_records.issubset(self._available_records), "\nvisited: {}\n\navail: {}".format(self._visited_records, self._available_records)

        # logger.debug(f"visited: {len(self._visited_records)}, avail: {len(self._available_records)})")
        for record in self._available_records:
            record.increase_availability_count()

        for record in self._visited_records:
            # logger.debug("record: {}".format(record))
            record.increase_number_visits()
            record.add_reward(reward_vector)

    def best_action(self, state: TichuState) -> PlayerAction:
        """
        Returns the actions with the highest ucb value
        
        :param state: 
        :return: The best action to play from the given state
        """
        nid = self._graph_node_id(state)

        assert nid in self.graph
        assert self.graph.out_degree(nid) > 0

        possactions = state.possible_actions()

        max_a = next(iter(possactions))
        max_v = -float('inf')
        for _, to_nid, action in self.graph.out_edges_iter(nid, data='action', default=None):
            if action in possactions:
                rec = self.graph.node[to_nid]['record']
                val = rec.ucb(p=state.player_pos)
                # logger.debug(f"   {val}->{action}: {rec}")
                if val > max_v:
                    max_v = val
                    max_a = action

        return max_a

    def _draw_graph(self, outfilename):
        # from networkx.drawing.nx_agraph import graphviz_layout
        plt.clf()
        G = self.graph
        graph_pos = nx.spring_layout(G)
        # graph_pos = graphviz_layout(G)
        nx.draw_networkx_nodes(G, graph_pos, with_labels=False, node_size=30, node_color='red', alpha=0.3)
        nx.draw_networkx_edges(G, graph_pos, width=1, alpha=0.3, edge_color='green')

        edge_labels = nx.get_edge_attributes(self.graph, 'action')
        nx.draw_networkx_edge_labels(G, graph_pos, edge_labels=edge_labels, font_size=3)

        plt.savefig(outfilename)


class InformationSetMCTS_absolute_evaluation(InformationSetMCTS):
    """
    Same as InformationSetMCTS, but the evaluation uses the absolute points instead of the difference.
    """

    def evaluate_state(self, state: TichuState) -> RewardVector:
        points = state.count_points()
        assert points[0] == points[2] and points[1] == points[3]
        return points


class EpicISMCTS(InformationSetMCTS):
    def _graph_node_id(self, state: TichuState) -> NodeID:
        return position_in_episode(state)


class ISMctsLGR(InformationSetMCTS):
    """
    **Type:** Information Set MCTS

    **Selection:** UCB1

    **Simulation:** LastGoodResponse (Moves of winning player gets stored and chosen in next rollout if applicable)

    **Best Action:** Most Visited
    """
    MOVE_BREAK = "MoveBreak"  # used to signalise the end of a trick in the made_moves attribute

    def __init__(self, *args, forgetting: bool = True, **kwargs):
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
                and self._lgr_map[last_action][
                    rollout_state.player_id] in rollout_state.possible_actions()):  # only take possible actions
                next_action = self._lgr_map[last_action][rollout_state.player_id]
                # logger.debug("LGR hit: {}->{}".format(last_action, next_action))
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

        # logger.debug("Size of LGR cache: {}".format(len(self._lgr_map)))
        self._made_moves.clear()


class ISMctsEpicLGR(ISMctsLGR, EpicISMCTS):
    """
    **Type:** Information Set MCTS

    **Selection:** EPIC-UCB1

    **Simulation:** LastGoodResponse (Moves of winning player gets stored and chosen in next rollout if applicable)

    **Best Action:** Most Visited
    """
    pass
