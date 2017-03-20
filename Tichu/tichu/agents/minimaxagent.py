import random

import logging
from collections import namedtuple

import time

from tichu.agents.abstractagent import BaseAgent
from tichu.cards.card import CardValue, Card
from tichu.cards.cards import Cards
from tichu.game.gameutils import Card_To, HandCardSnapshot

GameState = namedtuple("GameState", ["player_pos", "hand_cards", "combination_on_table", "ranking", "nbr_passed"])


class MiniMaxPIAgent(BaseAgent):  # MiniMaxPerfectInformationAgent

    def __init__(self):
        super().__init__()

    def give_dragon_away(self, hand_cards, round_history):
        pl_pos = (self.position + 1) % 4
        return pl_pos

    def wish(self, hand_cards, round_history):
        wish = random.choice([cv for cv in CardValue
                              if cv is not CardValue.DOG
                              and cv is not CardValue.DRAGON
                              and cv is not CardValue.MAHJONG
                              and cv is not CardValue.PHOENIX])
        return None  # TODO for now make no wish!!

    def play_combination(self, wish, hand_cards, round_history):
        nbr_passed = round_history.nbr_passed()
        assert nbr_passed in range(0, 4)
        comb = self._start_minimax(hand_cards=hand_cards, round_history=round_history, wish=wish,
                                   combination_on_table=round_history.combination_on_table, nbr_passed=nbr_passed)
        return comb

    def play_bomb(self, hand_cards, round_history):
        return None  # TODO, for now only play bomb when it's your turn -> bomb will never be beaten by another bomb!!

    def play_first(self, hand_cards, round_history, wish):
        nbr_passed = round_history.nbr_passed()
        assert nbr_passed == 0
        comb = self._start_minimax(hand_cards=hand_cards, round_history=round_history, wish=wish, combination_on_table=None, nbr_passed=nbr_passed)

        return comb

    def _possible_combinations(self, hand_cards, played_on, wish):
        """
        :param hand_cards:
        :param wish:
        :return: A combination fulfilling the wish if possible, None if not possible
        """
        possible_combs = list(hand_cards.all_combinations(played_on=played_on))
        # verify wish
        if wish and wish in (c.card_value for c in hand_cards):
            pcombs = [comb for comb in possible_combs if comb.contains_cardval(wish)]
            if len(pcombs):
                return pcombs
        return possible_combs

    def _start_minimax(self, hand_cards, round_history, wish, combination_on_table, nbr_passed):
        def is_double_win(state):
            return len(state.ranking) >= 2 and state.ranking[0] == (state.ranking[1] + 2) % 4

        def is_terminal(state, depth):
            assert len(state.ranking) <= 4, "{}".format(state.ranking)
            #logging.debug("terminal test at depth: {}".format(depth))
            # len(state.ranking) >= 3
            return sum([len(hc) > 0 for hc in state.hand_cards]) <= 1 or is_double_win(state)

        def eval_state(state):
            res = 0
            playerpos = self.position
            # update ranking
            final_ranking = state.ranking + [ppos for ppos in range(4) if ppos not in state.ranking]
            assert len(final_ranking) == 4, "{} -> {}".format(state.ranking, final_ranking)
            # evaluate
            if is_double_win(state):
                res = 200 if playerpos in state.ranking else 0
            elif playerpos == final_ranking[0]:
                res = 100
            elif playerpos in final_ranking[1:3]:
                res = 0
            else:
                assert playerpos == final_ranking[3], "pos: {}; ranking: {}".format(state.position, state.ranking)
                res = -100
            # logging.debug("evaluating state; pos:{s.player_pos} ranking: {s.ranking} -> {res}".format(s=state, res=res))
            return res

        def action_state_transition(state):
            """
            :param state:
            :return: generator yielding all (action, next_state) tuples reachable from the given state
            """
            # TODO incoorporate wish
            assert state.hand_cards is not None
            assert sum([len(hc) > 0 for hc in state.hand_cards]) >= 2  # at least 2 players must have cards left
            assert 0 <= state.nbr_passed <= 2
            assert len(state.hand_cards[state.player_pos]) > 0  # current player has handcards
            # if player in ranking, must have no handcards
            for ppos, hc in enumerate(state.hand_cards):
                if ppos in state.ranking:
                    assert len(hc) == 0, "r:{}, hc:{}".format(state.ranking, hc)

            next_player = next((ppos % 4 for ppos in range(state.player_pos+1, state.player_pos+4)
                                if len(state.hand_cards[ppos % 4]) > 0))
            assert next_player is not None

            comb_on_table = state.combination_on_table
            if comb_on_table is not None:
                # pass action is possible
                gs = GameState(player_pos=next_player,
                               hand_cards=state.hand_cards,
                               combination_on_table=comb_on_table if state.nbr_passed < 2 else None,  # test if this pass action is the 3rd
                               ranking=list(state.ranking),
                               nbr_passed=state.nbr_passed+1 if state.nbr_passed < 2 else 0)
                assert ((gs.combination_on_table is None and gs.nbr_passed == 0)
                        or (gs.combination_on_table is not None and gs.nbr_passed > 0))
                yield (None, gs)

            possible_combs = state.hand_cards[state.player_pos].all_combinations(played_on=comb_on_table)
            curr_player_handcards = state.hand_cards[state.player_pos]
            assert len(curr_player_handcards) > 0
            for comb in possible_combs:
                # remove comb from handcards:
                player_handcards = Cards(curr_player_handcards)
                assert len(player_handcards) > 0
                player_handcards.remove_all(comb)
                assert len(player_handcards) < len(curr_player_handcards)
                new_handcards_l = list(state.hand_cards)
                new_handcards_l[state.player_pos] = player_handcards.to_immutable()
                new_handcards = HandCardSnapshot(*new_handcards_l)
                assert new_handcards[state.player_pos].issubset(player_handcards), "new:{}; phc:{}".format(new_handcards[state.player_pos], player_handcards)
                assert len(player_handcards) == len(new_handcards[state.player_pos])
                # ranking:
                new_ranking = list(state.ranking)
                if len(player_handcards) == 0:
                    new_ranking.append(state.player_pos)
                    assert len(set(new_ranking)) == len(new_ranking), "state:{}\ncomb:{}".format(state, comb)

                # handle dog
                if Card.DOG in comb:
                    next_player = next_player = next((ppos % 4 for ppos in range(state.player_pos+2, state.player_pos+3+2)
                                    if len(state.hand_cards[ppos % 4]) > 0))
                    assert next_player is not None
                    comb = None

                # create game-state
                gs = GameState(player_pos=next_player,
                               hand_cards=new_handcards,
                               combination_on_table=comb,
                               ranking=new_ranking,
                               nbr_passed=0)
                yield (comb, gs)

            # TODO everyone can play a bomb if they want

            # END action_state_transition

        logging.info("player #{} started minimax".format(self.position))
        start_t = time.time()
        # print("rh:", round_history)
        logging.debug(("handcards before minimax:", round_history.last_handcards))
        start_state = GameState(player_pos=self.position,
                                hand_cards=round_history.last_handcards,
                                combination_on_table=combination_on_table,
                                ranking=round_history.ranking,
                                nbr_passed=nbr_passed)

        action = MiniMaxPIAgent.minimax_decision(start_state=start_state,
                                                 is_terminal=is_terminal,
                                                 eval_state=eval_state,
                                                 action_state_transisions=action_state_transition)

        logging.info("player #{} ended minimax (time: {})".format(self.position, time.time()-start_t))
        return action

    def swap_cards(self, hand_cards):
        sc = hand_cards.random_cards(3)
        scards = [
                   Card_To(sc[0], (self.position + 1) % 4),
                   Card_To(sc[1], (self.position + 2) % 4),
                   Card_To(sc[2], (self.position + 3) % 4)
                ]
        return scards

    def notify_about_announced_tichus(self, tichu, grand_tichu):
        pass

    def announce_tichu(self, announced_tichu, announced_grand_tichu, round_history):
        return False

    def announce_grand_tichu(self, announced_grand_tichu):
        return False

    # Minimax Search
    @staticmethod
    def minimax_decision(start_state, is_terminal, eval_state, action_state_transisions):

        def pretty_print_gs(state):
            return ("GS: {s.player_pos}"
                    "\n\tcards:{s.hand_cards}"
                    "\n\tcomb:{s.combination_on_table}"
                    "\n\trank:{s.ranking}"
                    "\n\tnbrpass:{s.nbr_passed}".format(s=state))

        def max_value(state, alpha, beta, depth):
            # logging.debug("+max: {}".format(pretty_print_gs(state)))
            if is_terminal(state, depth):
                # logging.debug("+max is terminal")
                return eval_state(state)
            v = -float("inf")
            for (a, s) in action_state_transisions(state):
                v = max(v, min_value(s, alpha, beta, depth+1))
                if v >= beta:
                    return v
                alpha = max(alpha, v)
            return v

        def min_value(state, alpha, beta, depth):
            # logging.debug("-min: {}".format(pretty_print_gs(state)))
            if is_terminal(state, depth):
                # logging.debug("-min is terminal")
                return eval_state(state)
            v = float("inf")
            for (a, s) in action_state_transisions(state):
                v = min(v, max_value(s, alpha, beta, depth+1))
                if v <= alpha:
                    return v
                beta = min(beta, v)
            return v

        # Body of minimax_decision starts here:
        res = [(a, min_value(state=s, alpha=-float("inf"), beta=float("inf"), depth=0)) for a, s in action_state_transisions(start_state)]
        action, val = max(res, key=lambda a_s: a_s[1])
        logging.info("result of minimax:{}; --> action:{}, val:{}".format(res, action, val))
        return action
