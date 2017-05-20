import uuid
import abc
import os
from itertools import islice
import logging
import networkx as nx
import matplotlib.pyplot as plt
import random
import atexit

from collections import defaultdict
from functools import lru_cache
from operator import itemgetter
from typing import Optional, Union, Hashable, NewType, TypeVar, Tuple, List, Dict, Iterable, Generator, Set, FrozenSet
from math import sqrt, log
from time import time
from scraper.tichumania_game_scraper import GenCombWeights

from profilehooks import timecall, profile

from gym_tichu.envs.internals import (TichuState, PlayerAction, PassAction, Trick, CardSet, HandCards, Card, CardRank,
                                      GeneralCombination, Combination, all_general_combinations_gen, InitialState,
                                      RolloutTichuState)
from gym_tichu.envs.internals.utils import check_param, flatten

logger = logging.getLogger(__name__)

__all__ = ('InformationSetMCTS', 'InformationSetMCTS_absolute_evaluation', 'EpicISMCTS', 'ISMctsLGR', 'ISMctsEpicLGR',
           'InformationSetMCTSWeightedDeterminization' 'InformationSetMCTSHighestUcbBestAction')

NodeID = NewType('NodeID', Hashable)
RewardVector = NewType('RewardVector', Tuple[int, int, int, int])


@lru_cache(maxsize=2**15)  # with (2**16) 64k CacheInfo(hits=2274111, misses=43745, maxsize=65536, currsize=43745)
def _uid_trick(trick: Trick) -> str:
    return ''.join(map(str, trick.combinations()))  # TODO improve


@lru_cache(maxsize=2048)  # CacheInfo(hits=329379, misses=1767, maxsize=2048, currsize=1767)
def _uid_cardset(cards: CardSet) -> str:
    return ''.join(map(str, cards))  # TODO improve


@lru_cache(maxsize=2**15)  # with 131k (2**17):  CacheInfo(hits=233368, misses=331146, maxsize=131072, currsize=131072)
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


@lru_cache(maxsize=2**15)
def position_in_episode(state: TichuState)->str:
    # TODO try: - with/without passactions; - include/remove playerid; - use the trick and not history; use 'genericcombinations'

    # history is the current trick on the table (only played combinations)
    if state.trick_on_table.is_empty():
        return "ROOT_" + str(state.player_pos)
    else:
        return _uid_trick(state.trick_on_table)


def _atexit_caches_info():
    """
    Printing the info of cached functions on program exit.
    """
    caches = [_uid_trick, _uid_cardset, unique_infoset_id, position_in_episode]
    print("=============== cache infos ===================")
    for cache in caches:
        print('{}: {}'.format(cache.__name__, cache.cache_info()))
    print()

atexit.register(_atexit_caches_info)


PPos = int  # playerPositionType
Len = int  # lengthType


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
    
    **determinization:** Uniformly Random

    **Selection:** UCB1

    **Simulation:** Uniform Random

    **Best Action:** Most Visited
    """

    def __init__(self):
        self.graph = nx.DiGraph(name='GameGraph')
        self.observer_id = None
        # self._visited_records = set()
        # self._available_records = set()
        self._visited_records = defaultdict(int)
        self._available_records = defaultdict(int)
        self._determinization_generator = None

    @timecall(immediate=False)
    def search(self, root_state: TichuState, observer_id: int, iterations: int, cheat: bool = False, clear_graph_on_new_root=True) -> PlayerAction:
        logger.debug(f"Started {self.__class__.__name__} with observer {observer_id}, for {iterations} iterations and cheat={cheat}")
        check_param(observer_id in range(4))

        root_search_state: TichuState = TichuState(*root_state, allow_tichu=False, allow_wish=False)  # Don't allow tichus or wishes in the simulation

        self.observer_id = observer_id
        self._determinization_generator = self._make__determinization_generator(root_search_state, observer_id)
        root_nid = self._graph_node_id(root_search_state)

        if root_nid not in self.graph and clear_graph_on_new_root:
            self.graph.clear()
        else:
            logger.debug("Could keep the graph :)")
        self.add_root(root_search_state)

        iteration = 0
        while iteration < iterations:
            iteration += 1
            self._init_iteration()
            # logger.debug("iteration "+str(iteration))
            state_det = root_search_state if cheat else next(self._determinization_generator)
            assert self._graph_node_id(state_det) == self._graph_node_id(root_search_state)  # make sure it is the same node
            # logger.debug("Tree policy")
            leaf_state = self.tree_policy(state_det)
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
        self._visited_records.clear()
        self._available_records.clear()

    def _graph_node_id(self, state: TichuState) -> NodeID:
        return unique_infoset_id(state=state, observer_id=self.observer_id)

    def _record_for_state(self, state: TichuState)->UCB1Record:
        return self.graph.node[self._graph_node_id(state)]['record']

    def _make__determinization_generator(self, state: TichuState, observer_id: int):
        """
        Overwrite to change determinization strategy
        
        :param state: 
        :param observer_id:
        :return: A Generator generating determinizations for the given state and observer
        """
        return Determiner(state=state, observer=observer_id).uniform_random_determinization_gen()

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
        assert isinstance(state, TichuState)
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
        # add the state to the available states since it is the root state
        self._available_records[self._record_for_state(state)] += 1
        while not curr_state.is_terminal():
            # add curr_state to visited nodes
            self._visited_records[self._record_for_state(curr_state)] += 1
            # check if needs to expand
            if not self.is_fully_expanded(curr_state):
                self.expand(curr_state)
                # select one of the nodes that just were expanded
                ret_state = curr_state.next_state(self.tree_selection(curr_state))
                # add the returned sate to the visited nodes
                self._visited_records[self._record_for_state(ret_state)] += 1
                return ret_state
            else:
                # No expanding, just select next node
                curr_state = curr_state.next_state(self.tree_selection(curr_state))

        return curr_state

    def is_fully_expanded(self, state: TichuState) -> bool:
        existing_actions = {action for _, _, action in self.graph.out_edges_iter(nbunch=[self._graph_node_id(state)], data='action', default=None)}
        if len(existing_actions) < len(state.possible_actions_set):
            return False

        # if all possible actions already exist -> is fully expanded
        return state.possible_actions_set.issubset(existing_actions)

    def tree_selection(self, state: TichuState) -> PlayerAction:
        """

        :param state:
        :return: 
        """
        # logger.debug("Tree selection")
        nid = self._graph_node_id(state)

        # find max (return uniformly at random from max UCB1 value)
        poss_actions = state.possible_actions_set
        max_val = -float('inf')
        max_actions = list()
        for _, to_nid, action in self.graph.out_edges_iter(nbunch=[nid], data='action', default=None):
            # logger.debug("Tree selection looking at "+str(action))
            if action in poss_actions:
                child_record = self.graph.node[to_nid]['record']
                self._available_records[child_record] += 1
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

        rollout_state = RolloutTichuState.from_tichustate(state)
        return self.evaluate_state(rollout_state.random_rollout())  # TODO make RolloutState.random_rollout() to return a normal TichuState?

    @timecall(immediate=False)
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

        # def str_dict(d):
        #     s = ""
        #     for k, v in d.items():
        #         s += "\n{} -> {}".format(repr(k), repr(v))
        #     return s+"\n"

        # all visited are were available at least once
        assert set(self._visited_records.keys()).issubset(set(self._available_records.keys()))  #, "\nvisited: {} \n avail: {}".format(str_dict(self._visited_records), str_dict(self._available_records))
        assert all(self._available_records[vk] >= vv for vk, vv in self._visited_records.items())  # at least as much available as visited

        # logger.debug(f"visited: {len(self._visited_records)}, avail: {len(self._available_records)})")
        for record, amount in self._available_records.items():
            record.increase_availability_count(amount=amount)

        for record, amount in self._visited_records.items():
            # logger.debug("record: {}".format(record))
            record.increase_number_visits(amount=amount)
            record.add_reward([r*amount for r in reward_vector])

    def best_action(self, state: TichuState) -> PlayerAction:
        """
        Returns the actions with the highest visit count
        
        :param state: 
        :return: The best action to play from the given state
        """
        nid = self._graph_node_id(state)

        assert nid in self.graph
        assert self.graph.out_degree(nid) > 0

        possactions = state.possible_actions_set

        max_a = next(iter(possactions))
        max_v = -float('inf')
        for _, to_nid, action in self.graph.out_edges_iter(nid, data='action', default=None):
            if action in possactions:
                rec = self.graph.node[to_nid]['record']
                val = rec.visit_count
                logger.debug(f"   {val}->{action}: {rec}")
                if val > max_v:
                    max_v = val
                    max_a = action
            else:
                logger.debug(f"    not possible: {action}")

        logger.debug("---> {}".format(max_a))
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


class ISMCTS_old_rollout(InformationSetMCTS):
    """
    Uses the older (slower) rollout loop (instead of the dedicated RolloutState class).
    """

    @timecall(immediate=False)
    def rollout_policy(self, state: TichuState):
        rollout_state = state
        while not rollout_state.is_terminal():
            rollout_state = rollout_state.next_state(rollout_state.random_action())
        return self.evaluate_state(rollout_state)


class InformationSetMCTS_absolute_evaluation(InformationSetMCTS):
    """
    Same as InformationSetMCTS, but the evaluation uses the absolute points instead of the difference.
    """

    def evaluate_state(self, state: TichuState) -> RewardVector:
        points = state.count_points()
        assert points[0] == points[2] and points[1] == points[3]
        return points


class InformationSetMCTS_ranking_evaluation(InformationSetMCTS):
    """
    Same as InformationSetMCTS, but the evaluation is:
    +1 for doublewin 
    -1 for double loss (enemy has doublewin)
    0.5 for finishing first (but no doublewin)
    0 for enemy finishing first (but no doublewin)
    """

    def evaluate_state(self, state: TichuState) -> RewardVector:
        if len(state.ranking) == 2:
            assert state.ranking[0] == (state.ranking[1] + 2) % 4
            # doublewin, winner get 1, loosers -1
            return (1, -1, 1, -1) if 0 in state.ranking else (-1, 1, -1, 1)
        else:
            # no doublewin, winner team gets 0.5, looser team 0
            final_ranking = tuple(state.ranking) + tuple([ppos for ppos in range(4) if ppos not in state.ranking])  # TODO speed
            assert len(final_ranking) == 4
            winner = state.ranking[0]
            return (0.5, 0, 0.5, 0) if winner == 0 or winner == 2 else (0, 0.5, 0, 0.5)


class InformationSetMCTSWeightedDeterminization(InformationSetMCTS):

    def _make__determinization_generator(self, state: TichuState, observer_id: int):
        return Determiner(state=state, observer=observer_id).weighted_determinization_gen()


class InformationSetMCTSHighestUcbBestAction(InformationSetMCTS):
    """
    InformationSetMCTS where the best_action is the one with the highest ucb value.
    """

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


PlayerPos = NewType('PlayerPos', int)  # a playerposition (in range(4))
Length = NewType('Length', int)  # denotes a length. ie the length of a cards set.


def _make_random_weights_dict()->Dict[GeneralCombination, Dict[Len, float]]:
    d = dict()
    for gcomb in all_general_combinations_gen():
        weights = [random.random() for _ in range(1, 15)]
        s = sum(weights)
        weights = [w / s for w in weights]
        for l0, w in enumerate(weights):
            d[(gcomb, l0+1)] = w
    return d

# Probability that given some handcards of the length, the GeneralCombination is in it.
WEIGHTS_DICT: Dict[Tuple[Length, GeneralCombination], float] = GenCombWeights.weights_from_file("{}/gcombweights.pkl".format(os.path.dirname(os.path.realpath(__file__))))


class Determiner(object):
    """
    Class generating determinizations from a given state
    """

    def __init__(self, state: TichuState, observer: PlayerPos):
        self._state = state
        self._observer = observer
        self._cards = self._unknown_cards()
        self._observer_handcards = state.handcards[observer]

        self._right, self._teammate, self._left = (observer + 1) % 4, (observer + 2) % 4, (observer + 3) % 4
        self._other_players = (self._right, self._teammate, self._left)
        self._pos_to_goallength: Dict[PlayerPos, Length] = {ppos: len(state.handcards[ppos]) for ppos in self._other_players}

    def uniform_random_determinization_gen(self)->TichuState:
        """
        Does a uniform random determinization of the given state with the observer keeping the original cards
        :return: TichuState with the determinization applied
        """
        full_unknown_cards = list(self._unknown_cards())
        while True:
            unknown_cards = list(full_unknown_cards)
            random.shuffle(unknown_cards)
            # logging.debug('unknown cards: '+str(unknown_cards))
            new_hc_list = [list()]*4
            for idx in range(4):
                if idx == self._observer:
                    new_hc_list[idx] = list(self._state.handcards[idx])
                else:
                    l = len(self._state.handcards[idx])
                    det_cards = unknown_cards[:l]
                    unknown_cards = unknown_cards[l:]
                    new_hc_list[idx] = det_cards

            # print(*map(str, flatten(new_hc_list)))
            yield self._apply_the_determinization_to_state(new_hc_list)

    def weighted_determinization_gen(self)->Generator[TichuState, None, None]:
        while True:
            yield self._pool_strategy()


    def _pool_strategy(self)->TichuState:
        # Setup stuff
        handcards = {ppos: list() for ppos in self._other_players}
        remaining_cards: CardSet = self._cards

        assert len(self._cards) == sum(self._pos_to_goallength.values())  # cards to distribute match the goal lengths

        while any(len(handcards[ppos]) != self._pos_to_goallength[ppos] for ppos in self._other_players):  # while not all players have their cards
            # Find all possible generalcombinations
            gencombs, possible_for_dict = self.possible_gencombs(remaining_cards, remaining_lengths={ppos: self._pos_to_goallength[ppos] - len(hc) for ppos, hc in handcards.items()})
            # Find probability that the gencomb is in any of the 3 handcards
            gcomb_weight = list()
            for gcomb in gencombs:
                # only taking the probas into account where the gcomb is acctually possible.
                probas = [WEIGHTS_DICT[(l, gcomb)] for l in (self._pos_to_goallength[ppos] for ppos in possible_for_dict[gcomb])]
                weight = sum(probas) / len(probas) if len(probas) else 0  # weight is the average of those probas
                assert 0.0 <= weight <= 1.0
                if len(possible_for_dict[gcomb]) == 0:
                    logger.warning("Determiner::_pool_strategy: General Comb can't be added to any player -> {}".format(weight))
                else:
                    gcomb_weight.append((gcomb, weight))

            # Sample from all gcombs with their respective weights
            chosen_gcomb = random.choices(population=list(map(itemgetter(0), gcomb_weight)), weights=list(map(itemgetter(1), gcomb_weight)))[0]
            # print("chosen: ", chosen_gcomb, "gcomb-weight: ", gcomb_weight[list(map(itemgetter(0), gcomb_weight)).index(chosen_gcomb)])

            # Give to most probable player (take current handcards into account)
            best_ppos = None
            p = -float('inf')
            for ppos in possible_for_dict[chosen_gcomb]:
                w = WEIGHTS_DICT[(self._pos_to_goallength[ppos], chosen_gcomb)]
                if w > p:
                    p = w
                    best_ppos = ppos

            # convert gcomb to actual cards.
            chosen_comb = chosen_gcomb.find_in_cards(remaining_cards)
            handcards[best_ppos].extend(chosen_comb)
            remaining_cards = CardSet(c for c in remaining_cards if c not in chosen_comb)

        assert len(remaining_cards) == 0
        handcards[self._observer] = list(self._observer_handcards)
        return self._apply_the_determinization_to_state([handcards[ppos] for ppos in range(4)])

    def _apply_the_determinization_to_state(self, new_handcards_list: List[List[Card]]) -> TichuState:
        """
        Applies the determinization and does some sanity checks

        :param new_handcards_list: 
        :param observer: 
        :return: The TichuState where the handcards are replaced by the HandCards instance created by the new_handcards_list.
        """
        new_handcards = HandCards(*new_handcards_list)
        assert all(c is not None for c in new_handcards_list)  # all players have handcards
        assert sum(len(hc) for hc in new_handcards) == sum(
                len(hc) for hc in self._state.handcards), "\nnew: {} \nold: {}".format(new_handcards, self._state.handcards)  # no card is lost
        assert all(len(old_hc) == len(new_hc) for old_hc, new_hc in zip(self._state.handcards, new_handcards))  # each player has the same amount of cards as before
        assert new_handcards[self._observer] == self._state.handcards[self._observer]  # observers handcards have not been changed
        ts = self._state.change(handcards=new_handcards)
        return ts

    def _unknown_cards(self) -> CardSet:
        """
        :return: The shuffeled cards of the 3 players (that are not the observer) 
        """
        return CardSet(flatten((hc for idx, hc in enumerate(self._state.handcards) if idx != self._observer)))

    def possible_gencombs(self, cards: CardSet, remaining_lengths: Dict[PlayerPos, Length])->Tuple[FrozenSet[GeneralCombination], Dict[GeneralCombination, List[PlayerPos]]]:
        """
        
        :param cards: 
        :return: A Tuple containing: 
        - A set of possible GeneralCombinations in the given cards (taking the goal_lengths into account). 
        - a dict mapping each gcomb to the playerpos where it can be added
        """
        max_length = max(remaining_lengths.values())
        gen_combs_set = frozenset(gcomb for gcomb in cards.all_general_combinations() if gcomb.nbr_cards() <= max_length)
        gcomb_ppos_dict = {gcomb: [ppos for ppos, l in remaining_lengths.items() if gcomb.nbr_cards() <= l] for gcomb in gen_combs_set}

        return gen_combs_set, gcomb_ppos_dict


if __name__ == '__main__':
    def count_different_cardranks(hc1: HandCards, hc2: HandCards):
        count = 0

        for k in range(4):
            cards1: CardSet = hc1[k]
            cards2: CardSet = hc2[k]
            rank_dict1 = cards1.rank_dict()
            rank_dict2 = cards2.rank_dict()
            for rank in CardRank:
                count += abs(len(rank_dict1.get(rank, [])) - len(rank_dict2.get(rank, [])))
        return count


    initstate = InitialState().announce_grand_tichus([]).announce_tichus([]).trade_cards(trades=list())
    next_handcards = initstate.handcards
    # remove some cards
    next_handcards = next_handcards.remove_cards(player=1, cards=islice(next_handcards.iter_all_cards(player=1), 7))
    next_handcards = next_handcards.remove_cards(player=2, cards=islice(next_handcards.iter_all_cards(player=2), 9))
    next_handcards = next_handcards.remove_cards(player=3, cards=islice(next_handcards.iter_all_cards(player=3), 10))

    state = initstate.change(handcards=next_handcards)
    D: Determiner = Determiner(state, observer=0)
    rand_gen = D.uniform_random_determinization_gen()
    weighted_gen = D.weighted_determinization_gen()
    count_diff_proba_vs_rand = 0
    for _ in range(100):
        det = next(weighted_gen)
        rand_det = next(rand_gen)
        diff_rand = count_different_cardranks(D._state.handcards, rand_det.handcards)
        diff_proba = count_different_cardranks(D._state.handcards, det.handcards)
        count_diff_proba_vs_rand += (diff_rand - diff_proba)  # if positive, proba was better, if negative, random was better

        print("{} - {}".format(diff_rand, diff_proba))
        for k in range(4):
            print("Orig:       ", D._state.handcards[k])
            print("Det:        ", det.handcards[k])
            print("random Det: ", rand_det.handcards[k])
            print()
        print("different cards to probabilistic: ", diff_proba)
        print("different cards to random: ", diff_rand)

    print(count_diff_proba_vs_rand)
