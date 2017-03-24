
import logging
from collections import defaultdict
from time import time

from tichu.cards.deck import Deck
from tichu.game.gameutils import *
from tichu.utils import *


class TichuGame(object):

    def __init__(self, team1, team2, target_points=1000):
        """

        :param team1:
        :param team2:
        :param target_points: (integer > 0, default=1000) The game ends when one team reaches this amount of points
        """
        check_isinstance(team1, Team)
        check_isinstance(team2, Team)
        check_param(target_points > 0)

        self._teams = (team1, team2)

        self._players = [team1.first_player,
                         team2.first_player,
                         team1.second_player,
                         team2.second_player]

        self._target_points = target_points
        self._history = GameState(team1, team2, target_points=target_points)

    def start_game(self):
        """
        Starts the tichu
        Returns a tuple containing the two teams, the winner team, and the tichu history
        """
        start_t = time()
        logging.info("Starting game...")

        for k in range(4):
            self._players[k].new_game(k, (k+2) % 4)

        while all([p < self._target_points for p in self._history.points]):
            # run rounds until there is a winner
            self._start_round()

        # determine winner
        final_points = self._history.points
        if final_points[0] > final_points[1]:
            self._history.winner_team = self._history.team1
        else:
            self._history.winner_team = self._history.team2

        outcome = self._history.build()

        logging.warning("Game ended: {go.points} (time: {time} sec)".format(time=time()-start_t, go=outcome))

        return outcome

    def _start_round(self):
        # TODO what to do when both teams may win in this round.
        start_t = time()

        roundstate = self._history.start_new_round()
        logging.info("Start round, with points: "+str(roundstate.initial_points))

        # inform players about new round
        for player in self._players:
            player.new_round()

        # distribute cards
        piles = self._distribute_cards()
        roundstate.grand_tichu_hands = HandCardSnapshot(*[ImmutableCards(pile[0:8]) for pile in piles])
        roundstate.before_swap_hands = HandCardSnapshot(*[ImmutableCards(pile) for pile in piles])

        # Players may announce a normal tichu before card swap
        self._ask_for_tichu()

        # card swaps
        swapped_cards = self._swap_cards()
        roundstate.card_swaps = tuple(swapped_cards)


        # round-loop
        leading_player = self._mahjong_player()

        # ##################### TEST TODO remove later
        nbr_remove = 0
        if nbr_remove > 0:
            for pl in self._players:
                pl._hand_cards.remove_all(pl.hand_cards.random_cards(nbr_remove))  # remove some random cards to make game shorter
                assert len(pl.hand_cards) == 14-nbr_remove
        # #################### END TEST

        roundstate.complete_hands = self.make_handcards_snapshot()

        wish = None
        # trick's loop
        while len(roundstate.ranking) < 3 and not roundstate.is_double_win():
            leading_player, wish = self._run_trick(leading_player=leading_player, wish=wish)

            if leading_player.has_finished:  # if the leading player has already finished
                leading_player = self._next_to_play(leading_player.position)

        # round ended, count scores
        (score_t1, score_t2) = self._finish_round()

        roundstate.points = (score_t1, score_t2)

        logging.warning("Round ends, with points: {rs.points[0]}:{rs.points[1]} -> {rs.final_points[0]}:{rs.final_points[1]} (time: {time:.2f} sec)"
                        .format(time=time()-start_t, rs=roundstate))
        logging.debug("------------------------------------------------------------")

        return (score_t1, score_t2)

    def _run_trick(self, leading_player, wish):
        """
        Leads through a trick (and updates the tichu state accordingly)
        :param leading_player: the Player to  play first.
        :return the player to go next
        """

        rs = self._history.current_round  # current round state
        logging.info("start trick...")

        trick_ended = False
        next_to_play = leading_player
        nbr_pass = 0
        while not trick_ended:
            assert not next_to_play.has_finished
            logging.info("Next to play -> {}.".format(next_to_play.name))
            played_action = None
            if rs.current_trick.is_empty():  # first play of the trick
                played_action = next_to_play.play_first(game_history=self._history, wish=wish)
            else:
                played_action = next_to_play.play_combination(game_history=self._history, wish=wish)

            if played_action.is_pass():
                logging.info("[PASS] {}.".format(next_to_play.name))
                nbr_pass += 1
            else:  # if trick
                logging.info("[PLAY] {}: {}.".format(next_to_play.name, played_action.combination))
                # handle tichu
                if played_action.is_tichu() and next_to_play.can_announce_tichu():
                    rs.announce_tichu(next_to_play.position)
                    self._notify_all_players_about_tichus()

                # update the trick on the table
                rs.current_trick.add(played_action)
                # update the leading_player
                leading_player = next_to_play
                # update the nbr pass actions
                nbr_pass = 0

                # verify wish
                if wish is not None and not played_action.is_pass() and played_action.combination.fulfills_wish(wish):
                    wish = None  # wish is satisfied

                # handle Mahjong (ask for wish)
                if Card.MAHJONG in played_action.combination:
                    wish = next_to_play.wish(game_history=self._history)
                    logging.info("[WISH] {}: {}".format(next_to_play.name, wish))

                # if the players finished with this move
                if next_to_play.has_finished:
                    rs.ranking_append_player(next_to_play.position)
                    logging.info("[FINISH] {}.".format(next_to_play.name))

                    # test doppelsieg
                    if rs.is_double_win():
                        trick_ended = True

                    # test whether 3rd players to win and thus ends the trick.
                    # (3rd to win automatically gets the last trick)
                    if len(rs.ranking) == 3:
                        rs.ranking_append_player(self._next_to_play(next_to_play.position).position)  # add last players
                        trick_ended = True

                    logging.debug("Ranking: {}".format(rs.ranking))

                # handle dog
                if Card.DOG in played_action.combination:
                    assert len(played_action.combination) == 1  # just to be sure
                    leading_player = self._players[next_to_play.team_mate]  # give lead to teammate
                    trick_ended = True  # no one can play on the DOG
            # fi is trick

            if not trick_ended:
                # ask all players whether they want to play a bomb
                bomb_action = self._ask_for_bomb(next_to_play.position)
                while bomb_action is not None:
                    bomb_player = bomb_action.player
                    logging.info("[BOMB] {}: {}.".format(bomb_player.name, bomb_action.combination))
                    rs.current_trick.add(bomb_action)  # update the trick on the table
                    leading_player = bomb_player  # update the leading players
                    next_to_play = self._next_to_play(bomb_player.position)
                    nbr_pass = 0
                    trick_ended = True  # can only play bombs on a bomb
                    # ask again for bomb
                    bomb_action = self._ask_for_bomb(next_to_play.position)

            # determine the next player to play
            next_to_play = self._next_to_play(next_to_play.position)

            # test the pass count
            if nbr_pass >= 3:
                trick_ended = True

            # end-while

        # give the trick to the correct player.
        receiving_player = leading_player
        if rs.current_trick.is_dragon_trick():  # handle dragon trick
            receiving_player = self._players[leading_player.give_dragon_away(self._history)]
            logging.info("[GIVE DRAGON TRICK] {} -> {}".format(next_to_play.name, receiving_player.name))

        # give trick to the receiving player
        receiving_player.add_trick(rs.current_trick.finish())

        rs.finish_trick(self.make_handcards_snapshot())

        logging.info("[WIN TRICK] {}: ({})".format(next_to_play.name, rs.last_finished_trick))

        # return the leading player and the wish
        return leading_player, wish

    def make_handcards_snapshot(self):
        return HandCardSnapshot(*[ImmutableCards(pl.hand_cards) for pl in self._players])

    def _team_of(self, player):  # TODO test if used
        """
        :param player
        :return the team of the given players
        """
        # TODO better solution? Dict for example
        t = self._teams[0] if player in self._teams[0] else self._teams[1]
        assert player in t  # just to be sure
        return t

    def _finish_round(self):
        """
        Gives the hand cards of the last players to the enemy and the tricks to the first players and counts the points for each team.
        :return a tuple (points of team 1, points of team 2) ie. (point of players 0 and 2, point of players 1 and 3)
        """
        rs = self._history.current_round
        logging.info("Finishing Round, ranking: {}".format(rs.ranking))

        winner_pos = rs.ranking[0]
        # grand + normal tichu
        points = self._calculate_tichu_points()
        logging.debug("points after tichu: {}".format(points))

        # doppelsieg
        if rs.is_double_win():
            logging.info("[DOUBLE WIN]")
            points[winner_pos] += 200
        else:
            logging.info("No double win")
            loosing_pos = rs.ranking[-1]
            # last players gives hand_card points to enemy ...
            loosing_handcard_points = self._players[loosing_pos].remove_hand_cards().count_points()
            points[(loosing_pos+1) % 4] += loosing_handcard_points

            logging.debug("points after hands to enemy: {}; {}+={}".format(points, (loosing_pos+1) % 4, loosing_handcard_points))

            # ... and tricks to first players
            loosing_trick_points = self._players[loosing_pos].count_points_in_tricks()
            points[winner_pos] += loosing_trick_points
            self._players[loosing_pos].remove_tricks()

            logging.debug("points after tricks to first: {}; {}+={}".format(points, winner_pos, loosing_trick_points))

            # count points in tricks
            for player_pos in range(4):
                points[player_pos] += self._players[player_pos].count_points_in_tricks()
            logging.debug("points after trick counting: {}".format(points))

        # remove handcards and tricks
        for player in self._players:
            player.remove_hand_cards()
            player.remove_tricks()

        logging.debug("points: {}".format(points))

        return (points[0] + points[2], points[1] + points[3])

    def _calculate_tichu_points(self):
        """
        :return: dict{int: points}, a dict containing the points of each players gained (or lost) by succeeding or failing to fullfill a (grand)Tichu
        """
        points_t, points_gt = defaultdict(lambda: 0), defaultdict(lambda: 0)
        points_gt.update({pid: -200 for pid in self._history.current_round.announced_grand_tichus})  # assuming all players failed
        points_t.update({pid: -100 for pid in self._history.current_round.announced_tichus})  # assuming all players failed
        ranks = self._history.current_round.ranking
        points_gt[ranks[0]] *= -1  # inverse winner points.
        points_t[ranks[0]] *= -1  # inverse winner points.
        return {pid: points_gt[pid] + points_t[pid] for pid in range(4)}  # put together

    def _swap_cards(self):
        """
        Asks all players to swap cards.
        :return set containing the swapped cards
        """
        swapcards = set()
        swapcards_to_return = set()
        # ask for swapcards
        for player in self._players:
            player_swapcards = player.swap_cards()

            if not isinstance(player_swapcards, SwapCards):
                raise IllegalActionException("The Swapcards must be an instance of 'SwapCards', but were {}".format(player_swapcards.__class__))
            for sc in player_swapcards:
                swapcards.add(sc)
            swapcards_to_return.add(player_swapcards)

        # distribute swapped cards
        for player in self._players:
            player.receive_swapped_cards([sc for sc in swapcards if sc.to == player.position])

        assert all([len(p.hand_cards) == 14 for p in self._players])
        assert all([p.hand_cards.issubset(Deck(full=True)) for p in self._players])

        return swapcards_to_return

    def _ask_for_bomb(self, current_player_pos):
        """
        Asks all players whether they want to play a bomb.
        :param current_player_pos: int; The id of the players whose turn it is.
        :return The players that wants to play a bomb. Or None if no players plays a bomb.
        """
        players_to_ask = [self._players[p_pos] for p_pos in [i % 4 for i in range(current_player_pos, current_player_pos+4)] if not self._players[p_pos].has_finished]
        for player in players_to_ask:
            bomb_action = player.play_bomb_or_not(game_history=self._history)
            if bomb_action:
                return bomb_action
        return None

    def _ask_for_tichu(self):
        """
        Asks all players whether they want to announce a Tichu.
        :return True iff at least one players announced a Tichu, False otherwise
        """
        announced_gt = self._history.current_round.announced_grand_tichus
        did_announce = False
        for pl in self._players:
            # can't announce tichu if already announced grand tichu
            if pl.position not in announced_gt and pl.announce_tichu_or_not(
                    self._history.current_round.announced_tichus, list(announced_gt), self._history):
                self._history.current_round.announce_tichu(pl.position)
                did_announce = True

        self._notify_all_players_about_tichus()

        return did_announce

    def _notify_all_players_about_tichus(self):
        """
        Notifies all players who announced grand and normal tichus.
        :return: Nothing
        """
        for pl in self._players:
            pl.players_announced_tichus(tichu=self._history.current_round.announced_tichus,
                                        grand_tichu=self._history.current_round.announced_grand_tichus)

    def _next_to_play(self, current_player_pos):
        """
        :param current_player_pos: int; The id of the players whose turn it is currently.
        :return the next players that still has handcards left
        """
        next_to_play_pos = (current_player_pos + 1) % 4
        while self._players[next_to_play_pos].has_finished:
            # make sure no infinite loop happens
            if next_to_play_pos == current_player_pos:
                raise LogicError("No players has any cards left!")
            next_to_play_pos = (next_to_play_pos + 1) % 4
        return self._players[next_to_play_pos]

    def _mahjong_player(self):
        """
        Returns the players holding the mahjong
        Raises a LogicError if no such players exists.
        """
        for p in self._players:
            # TODO improve (if p.has_majong: return p)
            if Card.MAHJONG in p.hand_cards:
                return p
        raise LogicError("No players has MAHJONG card")

    def _distribute_cards(self):
        """
        Distributes 14 cards to each players and asks after the 8th card for a grand Tichu.
        Returns the distributed hand_cards as a list of Cards instances
        """

        deck = Deck(full=True)
        piles = deck.split(nbr_piles=4, random_=True)
        assert len(piles) == 4

        for k in range(0, 4):
            player_cards = piles[k]
            player = self._players[k]
            assert len(player_cards) == 14
            assert all([isinstance(c, Card) for c in player_cards])

            # remove all cards from the player
            player.remove_hand_cards()
            player.remove_tricks()

            # distribute cards and ask for grand tichu
            first_8 = player_cards[0:8]
            last_6 = player_cards[8:14]

            player.receive_first_8_cards(first_8)

            if player.announce_grand_tichu_or_not(self._history.current_round.announced_grand_tichus):
                self._history.current_round.announce_grand_tichu(k)

            player.receive_last_6_cards(last_6)

        # notify all players about the announced grand tichus
        self._notify_all_players_about_tichus()

        # return the distributed hand_cards
        return piles
