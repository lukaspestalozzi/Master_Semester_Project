from collections import defaultdict
from typing import Any, Dict, Tuple, Iterable

import numpy as np
import logging

from gym_tichu.envs.internals import TichuState
from gym_tichu.envs.internals.actions import *
from gym_tichu.envs.internals.cards import *
from rl.core import Processor

logger = logging.getLogger(__name__)


def all_general_combinations_gen():
    special_ranks = {CardRank.DOG, CardRank.MAHJONG, CardRank.DRAGON, CardRank.PHOENIX}
    non_special_ranks = {r for r in CardRank if r not in special_ranks}
    # singles
    for rank in CardRank:
        yield GeneralCombination(type=Single, height=rank.value)
    # pairs
    for rank in non_special_ranks:
        yield GeneralCombination(type=Pair, height=rank.value)
    # trios
    for rank in non_special_ranks:
        yield GeneralCombination(type=Trio, height=rank.value)
    # squarebombs
    for rank in non_special_ranks:
        yield GeneralCombination(type=SquareBomb, height=rank.value)
    # fullhouse
    for rank_trio in non_special_ranks:
        yield GeneralCombination(type=FullHouse, height=rank_trio.value)
        # for rank_duo in non_special_ranks:
        #     # Note trio == duo may happen with a squarebomb and the phoenix
        #     yield GeneralCombination(type=FullHouse, height=(rank_trio.value, rank_duo.value))

    # straight
    for rank in non_special_ranks.union({CardRank.MAHJONG}):
        if rank >= CardRank.FIVE:  # streets can't end with a lower card than 5
            for l in range(5, rank.value+1):  # iterate over all lengths possible for the straight ending in rank
                yield GeneralCombination(type=Straight, height=(l, rank.value))  # length, ending rank

    # pairsteps
    for rank in non_special_ranks:
        if rank >= CardRank.TWO:
            for l in range(2, rank.value):  # iterate over all lengths possible for the pairstep ending in rank
                yield GeneralCombination(type=PairSteps, height=(l, rank.value))  # length, ending rank

    # straightbombs (same as streets)
    for rank in non_special_ranks.union({CardRank.MAHJONG}):
        if rank >= CardRank.FIVE:  # streets can't end with a lower card than 5
            for l in range(5, rank.value+1):  # iterate over all lengths possible for the straight ending in rank
                yield GeneralCombination(type=StraightBomb, height=(l, rank.value))  # length, ending rank


all_general_combinations = list(all_general_combinations_gen())

PASS_ACTION_NBR = 257
GENERALCOMBINATION_TO_NBR = {gcomb: idx for idx, gcomb in enumerate(all_general_combinations)}


class DQNProcessor(Processor):

    # My functions
    def encode_tichu_state(self, state: TichuState)->Tuple[Any, Dict[int, PlayerAction]]:
        """
        Encodes the tichu-state for the NN,
        :param state: 
        :return: the encoded state and a dict mapping move nbrs to the action represented by that nbr.
        """
        def encode_cards(cards: Iterable[Card]):
            l = [False]*56
            if cards:
                for c in cards:
                    l[c.number] = True
            return l

        # encode handcards
        encoded = []
        for cards in state.handcards:
            encoded.extend(encode_cards(cards))

        # encode trick on table
        encoded.extend(encode_cards(state.trick_on_table.last_combination))

        # encode possible actions
        nbr_action_dict = dict()
        encoded_gen_actions = [-500]*(len(all_general_combinations)+1)
        for action in state.possible_actions_list:
            if isinstance(action, PassAction):
                nbr = PASS_ACTION_NBR
            else:
                gcomb = GeneralCombination.from_combination(action.combination)
                try:
                    nbr = GENERALCOMBINATION_TO_NBR[gcomb]
                except KeyError:
                    logger.debug("comb: {}".format(action.combination))
                    logger.debug("gcomb: {}".format(gcomb))
                    logger.debug("dict: {}".format('\n'.join(map(str, GENERALCOMBINATION_TO_NBR.items()))))
                    raise
            encoded_gen_actions[nbr] = 0
            nbr_action_dict[nbr] = action

        assert len(encoded) == 56*5
        assert len(encoded_gen_actions) == 258
        enc = (np.array(encoded, dtype=bool), np.array(encoded_gen_actions))
        # logger.warning("enc: {}".format(enc))
        return enc, nbr_action_dict

    # Keras-rl functions
    def process_step(self, observation, r, done, info):
        return observation, r, done, dict()

    def process_state_batch(self, batch):
        # logger.warning("batch: " + str(batch))
        if len(batch) == 1:
            state = batch[0][0]
            # logger.warning("state: {} shape {}, {}".format(state.__class__, state.shape, state))
            # logger.warning("state shapes: {} {}".format(state[0].shape, state[1].shape))
            retbatch = {'cards_input': np.array([state[0]]), 'possible_actions_input': np.array([state[1]])}

            return retbatch

        # logger.warning("Batch > 1: ")
        d = {'cards_input': [], 'possible_actions_input': []}
        for state in batch:
            # logger.warning("state: {} shape {}, {}".format(state.__class__, state.shape, state))
            d['cards_input'].append(state[0][0])
            d['possible_actions_input'].append(state[0][1])
            # logger.warning("shapes: {}, {}".format(processed_state[0].shape, processed_state[1].shape))

            # logger.warning("mybatch: {}".format(mybatch))

        retbatch = [np.array(d['cards_input']), np.array(d['possible_actions_input'])]
        # logger.debug("retbatch: {}".format(retbatch))
        return retbatch


# if __name__ == '__main__':
#     all_gcombs = sorted(all_general_combinations_gen(), key=lambda gc: (gc.type.__name__, gc.height))
#     print('\n'.join(map(str, all_gcombs)))
#     print("len: ", len(all_gcombs))
#
#     type_gcombs_dict = defaultdict(list)
#     for gcomb in all_gcombs:
#         type_gcombs_dict[gcomb.type].append(gcomb)
#
#     print("Nbr of general combinations for each type:")
#     for type, gcombs in type_gcombs_dict.items():
#         print(type.__name__, ": ", len(gcombs))


















# TWO = 2
# THREE = 3
# FOUR = 4
# FIVE = 5
# SIX = 6
# SEVEN = 7
# EIGHT = 8
# NINE = 9
# TEN = 10
# J = 11
# Q = 12
# K = 13
# A = 14
# DRAGON = 15
# PHOENIX = 1.5
# MAHJONG = 1
# DOG = 0