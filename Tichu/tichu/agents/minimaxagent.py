import random

import logging
from collections import namedtuple
from multiprocessing.pool import ThreadPool, Pool

import time

from tichu.agents.abstractagent import BaseAgent
from tichu.cards.card import CardValue, Card
from tichu.cards.cards import Cards, ImmutableCards
from tichu.game.gameutils import Card_To, HandCardSnapshot, is_double_win
from tichu.utils import indent, check_param

GameState = namedtuple("GameState", ["player_pos", "hand_cards", "tricks", "combination_on_table", "ranking", "nbr_passed"])


class MiniMaxPIAgent(BaseAgent):  # MiniMaxPerfectInformationAgent

    def __init__(self):
        super().__init__()
        self._minimax = MiniMaxSearch(max_depth=100)

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
        comb = self._start_minimax_search(hand_cards=hand_cards, round_history=round_history, wish=wish,
                                          combination_on_table=round_history.combination_on_table, nbr_passed=nbr_passed)
        return comb

    def play_bomb(self, hand_cards, round_history):
        return None  # TODO, for now only play bomb when it's your turn -> bomb will never be beaten by another bomb!!

    def play_first(self, hand_cards, round_history, wish):
        nbr_passed = round_history.nbr_passed()
        assert nbr_passed == 0
        comb = self._start_minimax_search(hand_cards=hand_cards, round_history=round_history, wish=wish, combination_on_table=None, nbr_passed=nbr_passed)

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

    def _start_minimax_search(self, hand_cards, round_history, wish, combination_on_table, nbr_passed):
        logging.info("player #{} started minimax".format(self.position))
        start_t = time.time()
        # print("rh:", round_history)
        logging.debug(("handcards before minimax:", round_history.last_handcards))
        start_state = GameState(player_pos=self.position,
                                hand_cards=round_history.last_handcards,
                                tricks=(ImmutableCards([]), ImmutableCards([]), ImmutableCards([]), ImmutableCards([])),
                                combination_on_table=combination_on_table,
                                ranking=round_history.ranking,
                                nbr_passed=nbr_passed)

        action = self._minimax.search(start_state=start_state, playerpos=self.position)

        logging.info("player #{} ended minimax (time: {})".format(self.position, time.time()-start_t))
        return action
    """
    def _start_minimax(self, hand_cards, round_history, wish, combination_on_table, nbr_passed):
        def is_double_win(state):
            return len(state.ranking) >= 2 and state.ranking[0] == (state.ranking[1] + 2) % 4

        def is_terminal(state, depth):
            assert len(state.ranking) <= 4
            # logging.debug("terminal test at depth: {}".format(depth))
            return (self.position in state.ranking
                    or len(state.ranking) >= 3
                    or sum([len(hc) > 0 for hc in state.hand_cards]) <= 1  # exuivalet to previous one TODO remove?
                    or is_double_win(state))

        def eval_state(state):
            def points_of(plpos, ranking):
                assert len(ranking) == 4  # no double win
                assert plpos in ranking
                assert plpos in range(0, 4)
                if plpos == ranking[0]:  # winner
                    return state.tricks[playerpos].count_points() + state.tricks[ranking[3]].count_points()  # own (winner) + looser tricks point
                elif plpos in ranking[1:3]:  # middle
                    return state.tricks[playerpos].count_points()  # only own tricks
                else:  # looser
                    assert plpos == ranking[3], "pos: {}; ranking: {}".format(playerpos, ranking)
                    return -1  # looser gets no points (less than 0)
            res = 0
            playerpos = self.position
            teammatepos = (playerpos+2) % 4

            # evaluate
            if is_double_win(state):
                res = 200 if playerpos in state.ranking else -200
            elif len(state.ranking) <= 2:
                # player finished 1st or 2nd but no double win
                assert self.position in state.ranking
                return state.tricks[playerpos].count_points() + state.tricks[teammatepos].count_points() + 50 if playerpos == state.ranking[0] else state.tricks[playerpos].count_points()

            else:  # round really ended
                final_ranking = state.ranking + [ppos for ppos in range(4) if ppos not in state.ranking]
                assert len(final_ranking) == 4, "{} -> {}".format(state.ranking, final_ranking)
                res = points_of(playerpos, ranking=final_ranking) + points_of(teammatepos, ranking=final_ranking)
                if final_ranking[3] != playerpos and final_ranking[3] != teammatepos:
                    res += state.hand_cards[final_ranking[3]].count_points()  # handcards go to enemy team

            # logging.debug("evaluating state; pos:{s.player_pos} ranking: {s.ranking} -> {res}".format(s=state, res=res))
            return res

        def action_state_transition(state):

            :param state:
            :return: generator yielding all (action, next_state) tuples reachable from the given state

            # TODO incoorporate wish
            # TODO dragon trick
            assert state.hand_cards is not None
            assert len(state.tricks) == 4
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

            possible_combs = state.hand_cards[state.player_pos].all_combinations(played_on=comb_on_table)
            curr_player_handcards = state.hand_cards[state.player_pos]
            assert len(curr_player_handcards) > 0
            for comb in possible_combs:
                new_comb_on_table = comb
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
                    new_comb_on_table = None

                # create game-state
                gs = GameState(player_pos=next_player,
                               hand_cards=new_handcards,
                               tricks=state.tricks,
                               combination_on_table=new_comb_on_table,
                               ranking=new_ranking,
                               nbr_passed=0)
                yield (comb, gs)

            if comb_on_table is not None:  # pass action is possible
                # give trick to player if this is 3rd passing
                new_tricks = state.tricks
                if state.nbr_passed == 2:
                    trick_winner_pos = (state.player_pos + 1) % 4
                    new_tricks = list(state.tricks)
                    new_tricks[trick_winner_pos] = Cards(state.tricks[trick_winner_pos]).add_all(comb_on_table).to_immutable()
                    new_tricks = tuple(new_tricks)
                gs = GameState(player_pos=next_player,
                               hand_cards=state.hand_cards,
                               tricks=new_tricks,
                               combination_on_table=comb_on_table if state.nbr_passed < 2 else None,  # test if this pass action is the 3rd
                               ranking=list(state.ranking),
                               nbr_passed=state.nbr_passed+1 if state.nbr_passed < 2 else 0)
                assert ((gs.combination_on_table is None and gs.nbr_passed == 0) or (gs.combination_on_table is not None and gs.nbr_passed > 0))
                yield (None, gs)

            # TODO everyone can play a bomb if they want

            # END action_state_transition

        logging.info("player #{} started minimax".format(self.position))
        start_t = time.time()
        # print("rh:", round_history)
        logging.debug(("handcards before minimax:", round_history.last_handcards))
        start_state = GameState(player_pos=self.position,
                                hand_cards=round_history.last_handcards,
                                tricks=(ImmutableCards([]), ImmutableCards([]), ImmutableCards([]), ImmutableCards([])),
                                combination_on_table=combination_on_table,
                                ranking=round_history.ranking,
                                nbr_passed=nbr_passed)

        action = MiniMaxPIAgent.minimax_decision(start_state=start_state,
                                                 is_terminal=is_terminal,
                                                 eval_state=eval_state,
                                                 action_state_transisions=action_state_transition)

        logging.info("player #{} ended minimax (time: {})".format(self.position, time.time()-start_t))
        return action
    """

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

        def indent(n):
            return "-".join("" for _ in range(n))

        def max_value(state, alpha, beta, depth):
            # logging.debug("+max: {}".format(pretty_print_gs(state)))
            if is_terminal(state, depth):
                # logging.debug("+max is terminal")
                return eval_state(state)
            asts = list(action_state_transisions(state))
            logging.debug("max({}){}> fanout:{}".format(depth, indent(depth), len(asts)))
            v = -float("inf")
            for (a, s) in asts:
                logging.debug("max({}){}> looking at:{}".format(depth, indent(depth), a))
                v = max(v, min_value(s, alpha, beta, depth+1))
                if v >= beta:
                    logging.debug("max({}){}> prune".format(depth, indent(depth)))
                    return v
                alpha = max(alpha, v)
            return v

        def min_value(state, alpha, beta, depth):
            # logging.debug("-min: {}".format(pretty_print_gs(state)))
            if is_terminal(state, depth):
                # logging.debug("-min is terminal")
                return eval_state(state)
            asts = list(action_state_transisions(state))
            logging.debug("min({}){}> fanout:{}".format(depth, indent(depth), len(asts)))
            v = float("inf")
            for (a, s) in asts:
                logging.debug("min({}){}> looking at:{}".format(depth, indent(depth), a))
                v = min(v, max_value(s, alpha, beta, depth+1))
                if v <= alpha:
                    logging.debug("min({}){}> prune".format(depth, indent(depth)))
                    return v
                beta = min(beta, v)
            return v

        # Body of minimax_decision starts here:
        asts = list(action_state_transisions(start_state))
        if len(asts) == 1:
            logging.info("result of minimax: only one action; --> action:{}".format(asts[0][0]))
            return asts[0][0]

        asts_sorted = sorted(asts, key=lambda a_s: a_s[0].height if a_s[0] is not None else float("inf"))  # sort: low combinations first, Passing last.

        pool = ThreadPool(processes=4)
        async_results = [(a, pool.apply_async(min_value, (s, -float("inf"), float("inf"), 0))) for a, s in asts_sorted]
        res = [(a, r.get()) for a, r in async_results]
        # res = [(a, min_value(state=s, alpha=-float("inf"), beta=float("inf"), depth=0)) for a, s in asts_sorted]
        action, val = max(res, key=lambda a_s: a_s[1])
        logging.info("result of minimax:{}; --> action:{}, val:{}".format(res, action, val))
        return action


class MiniMaxSearch(object):

    def __init__(self, max_depth=100):
        self._maxdepth = max_depth

    @property
    def maxdepth(self):
        return self._maxdepth

    @maxdepth.setter
    def maxdepth(self, new_maxdepth):
        check_param(new_maxdepth > 0)
        self._maxdepth = new_maxdepth

    def search(self, start_state, playerpos):
        # possible actions
        asts = list(self.action_state_transisions(start_state))
        if len(asts) == 1:
            logging.info("result of minimax: only one action; --> action:{}".format(asts[0][0]))
            return asts[0][0]

        # sort actions for better pruning
        asts_sorted = sorted(asts, key=lambda a_s: a_s[0].height if a_s[0] is not None else float("inf"))  # sort: low combinations first, Passing last.

        # start async search
        # pool = ThreadPool(processes=4)
        # async_results = [(a, pool.apply_async(self.min_value, (s, -float("inf"), float("inf"), 0))) for a, s in asts_sorted]
        # res = [(a, r.get()) for a, r in async_results]

        # start minimax search
        res = [(a, self.min_value(state=s, alpha=-float("inf"), beta=float("inf"), depth=0, playerpos=playerpos)) for a, s in asts_sorted]
        action, val = max(res, key=lambda a_s: a_s[1])
        logging.info("result of minimax:{}; --> action:{}, val:{}".format(res, action, val))
        return action

    def max_value(self, state, alpha, beta, depth, playerpos):
        # logging.debug("+max: {}".format(pretty_print_gs(state)))
        if self.is_terminal(state, depth, playerpos):
            # logging.debug("+max is terminal")
            return self.eval_state(state, playerpos)
        asts = list(self.action_state_transisions(state))
        logging.debug("max({}){}> fanout:{}".format(depth, indent(depth), len(asts)))
        v = -float("inf")
        for (a, s) in asts:
            logging.debug("max({}){}> looking at:{}".format(depth, indent(depth), a))
            v = max(v, self.min_value(s, alpha, beta, depth + 1, playerpos))
            if v >= beta:
                logging.debug("max({}){}> prune".format(depth, indent(depth)))
                return v
            alpha = max(alpha, v)
        return v

    def min_value(self, state, alpha, beta, depth, playerpos):
        # logging.debug("-min: {}".format(pretty_print_gs(state)))
        if self.is_terminal(state, depth, playerpos):
            # logging.debug("-min is terminal")
            return self.eval_state(state, playerpos)
        asts = list(self.action_state_transisions(state))
        logging.debug("min({}){}> fanout:{}".format(depth, indent(depth), len(asts)))
        v = float("inf")
        for (a, s) in asts:
            logging.debug("min({}){}> looking at:{}".format(depth, indent(depth), a))
            v = min(v, self.max_value(s, alpha, beta, depth + 1, playerpos))
            if v <= alpha:
                logging.debug("min({}){}> prune".format(depth, indent(depth)))
                return v
            beta = min(beta, v)
        return v

    # ############# Tichu Search Functions ######################
    def action_state_transisions(self, state):
        # TODO incoorporate wish
        # TODO dragon trick

        # assert integrity of the search
        assert state.hand_cards is not None
        assert len(state.tricks) == 4
        assert sum([len(hc) > 0 for hc in state.hand_cards]) >= 2  # at least 2 players must have cards left
        assert 0 <= state.nbr_passed <= 2
        assert len(state.hand_cards[state.player_pos]) > 0  # current player has handcards
        # if player in ranking, must have no handcards
        for ppos, hc in enumerate(state.hand_cards):
            if ppos in state.ranking:
                assert len(hc) == 0, "r:{}, hc:{}".format(state.ranking, hc)

        def next_player_turn(current_playerpos):
            return next((ppos % 4 for ppos in range(current_playerpos+1, current_playerpos+4) if len(state.hand_cards[ppos % 4]) > 0))

        next_player = next_player_turn(state.player_pos)
        assert next_player is not None

        comb_on_table = state.combination_on_table

        possible_combs = state.hand_cards[state.player_pos].all_combinations(played_on=comb_on_table)
        curr_player_handcards = state.hand_cards[state.player_pos]
        assert len(curr_player_handcards) > 0
        for comb in possible_combs:
            new_comb_on_table = comb
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
                new_comb_on_table = None

            # create game-state
            gs = GameState(player_pos=next_player,
                           hand_cards=new_handcards,
                           tricks=state.tricks,
                           combination_on_table=new_comb_on_table,
                           ranking=new_ranking,
                           nbr_passed=0)
            yield (comb, gs)

        if comb_on_table is not None:  # pass action is possible
            # give trick to player if this is 3rd passing
            new_tricks = state.tricks
            if state.nbr_passed == 2:
                trick_winner_pos = (state.player_pos + 1) % 4
                new_tricks = list(state.tricks)
                new_tricks[trick_winner_pos] = Cards(state.tricks[trick_winner_pos]).add_all(comb_on_table).to_immutable()
                new_tricks = tuple(new_tricks)
            gs = GameState(player_pos=next_player,
                           hand_cards=state.hand_cards,
                           tricks=new_tricks,
                           combination_on_table=comb_on_table if state.nbr_passed < 2 else None,  # test if this pass action is the 3rd
                           ranking=list(state.ranking),
                           nbr_passed=state.nbr_passed+1 if state.nbr_passed < 2 else 0)
            assert ((gs.combination_on_table is None and gs.nbr_passed == 0) or (gs.combination_on_table is not None and gs.nbr_passed > 0))
            yield (None, gs)

        # TODO everyone can play a bomb if they want

    def is_round_end(self, state):
        return (len(state.ranking) >= 3
                or sum([len(hc) > 0 for hc in state.hand_cards]) <= 1  # equivalet to previous one TODO remove?
                or is_double_win(state.ranking))

    def is_terminal(self, state, depth, playerpos):
        assert len(state.ranking) <= 4
        return (depth > self._maxdepth
                or self.is_round_end(state)
                or playerpos in state.ranking)

    def eval_state(self, state, playerpos):
        if not self.is_round_end(state):
            return self.heuristic(state, playerpos)
        else:
            def points_of(plpos, ranking):
                assert len(set(ranking)) == 4  # no double win
                assert plpos in ranking
                assert plpos in range(0, 4)
                if plpos == ranking[0]:  # winner
                    return state.tricks[plpos].count_points() + state.tricks[ranking[3]].count_points()  # own (winner) + looser tricks point
                elif plpos in ranking[1:3]:  # middle
                    return state.tricks[plpos].count_points()  # only own tricks
                else:  # looser
                    assert plpos == ranking[3], "pos: {}; ranking: {}".format(plpos, ranking)
                    return 0  # looser gets no points

            teammatepos = (playerpos+2) % 4

            # evaluate
            if is_double_win(state.ranking):
                res = 200 if playerpos in state.ranking else -200

            else:
                final_ranking = state.ranking + [ppos for ppos in range(4) if ppos not in state.ranking]
                assert len(final_ranking) == 4, "{} -> {}".format(state.ranking, final_ranking)

                res = points_of(playerpos, ranking=final_ranking) + points_of(teammatepos, ranking=final_ranking)
                if final_ranking[3] != playerpos and final_ranking[3] != teammatepos:
                    res += state.hand_cards[final_ranking[3]].count_points()  # handcards go to enemy team

            return res

    def heuristic(self, state, playerpos):
        # player finished 1st or 2nd but no double win, or maxdepth was reached
        if playerpos in state.ranking:
            player_points = state.tricks[playerpos].count_points()
            if playerpos == state.ranking[0]:
                player_points += state.tricks[(playerpos+2) % 4].count_points()
                # player_points += 100  # assume player announced a tichu TODO tichu
            #else:
            #    player_points -= 100  # assume enemy also announced a tichu TODO tichu
            return player_points + 0.1  # mark as 'heuristic' value
        else:
            return len(state.hand_cards[playerpos]) - 0.1  # - 0.1 to mark it as 'heurisic value'



