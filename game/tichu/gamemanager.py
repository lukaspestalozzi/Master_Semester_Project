
import logging
from collections import defaultdict
from time import time

from game.tichu.handcardsnapshot import HandCardSnapshot
from game.tichu.states import GameHistoryBuilder
from game.tichu.team import Team
from game.tichu.tichu_actions import PassAction, TichuAction, FinishEvent, WinTrickEvent, SwapCardAction, \
    GrandTichuAction
from .cards import Card, ImmutableCards, Deck
from .exceptions import IllegalActionException, LogicError

from ..utils import *


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
        self._history = GameHistoryBuilder(team1, team2, target_points=target_points)

    def start_game(self):
        """
        Starts the tichu
        Returns a tuple containing the two teams, the winner team, and the tichu history
        """
        start_t = time()
        logging.info(f"Starting game... target: {self._target_points}")

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

        roundhistory_builder = self._history.start_new_round()

        logging.info("Start round, with points: "+str(roundhistory_builder.initial_points))

        # inform players about new round
        for player in self._players:
            player.new_round()

        # distribute cards
        piles = self._distribute_cards()
        roundhistory_builder.grand_tichu_hands = HandCardSnapshot(*[ImmutableCards(pile[0:8]) for pile in piles])
        roundhistory_builder.before_swap_hands = HandCardSnapshot(*[ImmutableCards(pile) for pile in piles])

        # Players may announce a normal tichu before card swap
        self._ask_for_tichu()

        # card swaps
        swapped_cards = self._swap_cards()
        roundhistory_builder.append_all_events(swapped_cards)

        # round-loop
        leading_player = self._mahjong_player()

        roundhistory_builder.complete_hands = self.make_handcards_snapshot()

        wish = None
        logging.info("handcards after cardswap:\n" + roundhistory_builder.complete_hands.pretty_string(indent_=4))
        # trick's loop
        while not roundhistory_builder.round_ended():
            leading_player, wish = self._run_trick(leading_player=leading_player, wish=wish)

            if leading_player.has_finished:  # if the leading player has already finished
                leading_player = self._next_to_play(leading_player.position)

        # round ended, count scores
        (score_t1, score_t2) = self._finish_round()

        roundhistory_builder.points = (score_t1, score_t2)

        logging.warning("Round ends, with points: {rs.points[0]}:{rs.points[1]} -> {rs.final_points[0]}:{rs.final_points[1]} (time: {time:.2f} sec)"
                        .format(time=time()-start_t, rs=roundhistory_builder))
        logging.debug("------------------------------------------------------------")

        self._history.finish_round()

        return (score_t1, score_t2)

    def _run_trick(self, leading_player, wish):
        """
        Leads through a trick (and updates the tichu state accordingly)
        :param leading_player: the Player to  play first.
        :return the player to go next
        """

        rhb = self._history.current_round  # current round state
        logging.info("start trick...")

        trick_ended = False
        current_player = leading_player
        nbr_pass = 0
        while not trick_ended:
            assert not current_player.has_finished

            logging.debug(f"Next to play -> {current_player.position}, (combination on table: {rhb._current_trick.last_combination}, wish:{wish})")
            played_action = None
            if rhb.current_trick_is_empty():  # first play of the trick
                played_action = current_player.play_first(game_history=self._history, wish=wish)
            else:
                played_action = current_player.play_combination(game_history=self._history, wish=wish)

            rhb.append_event(played_action)  # handles Tichu and update the trick on the table
            if isinstance(played_action, PassAction):
                logging.info(f"[PASS] {current_player.position}. ".ljust(35)+f"(handcards: {current_player.hand_cards.pretty_string()})")
                nbr_pass += 1
            else:  # if trick
                logging.info(f"[PLAY] {current_player.position}: {played_action.combination}. ".ljust(35)+f"(handcards: {current_player.hand_cards.pretty_string()})")

                # update the leading_player
                leading_player = current_player
                # update the nbr pass actions
                nbr_pass = 0

                # if the player announced tichu with the move, announce it to the players
                if isinstance(played_action, TichuAction) and current_player.position in rhb.announced_tichus:
                    logging.info(f"[TICHU] announced by: {current_player.position}. ".ljust(35)+f"(handcards: {current_player.hand_cards.pretty_string()})")
                    self._notify_all_players_about_tichus()

                # verify wish
                if wish is not None and played_action.combination.fulfills_wish(wish):
                    assert not isinstance(played_action, PassAction)
                    wish = None  # wish is satisfied

                # handle Mahjong (ask for wish)
                if Card.MAHJONG in played_action.combination:
                    wish_action = current_player.wish(game_history=self._history)
                    wish = wish_action.card_value
                    rhb.append_event(wish_action)
                    logging.info(f"[WISH] {current_player.position}: {wish}")

                # if the players finished with this move
                if current_player.has_finished:
                    rhb.append_event(FinishEvent(player_pos=current_player.position))
                    logging.info(f"[FINISH] {current_player.position} (on rank {len(rhb.ranking)}).")

                    # test doppelsieg
                    if rhb.is_double_win():
                        logging.debug("Trick ends. Double win")
                        trick_ended = True

                    # test whether 3rd players to win and thus ends the trick.
                    # (3rd to win automatically gets the last trick)
                    if len(rhb.ranking) == 3:
                        rhb.append_event(FinishEvent(player_pos=self._next_to_play(current_player.position).position))  # add last players
                        logging.debug("Trick ends. Dog trick.")
                        trick_ended = True

                    logging.debug(f"Ranking: {rhb.ranking}")

                # handle dog
                if Card.DOG in played_action.combination:
                    assert len(played_action.combination) == 1  # just to be sure
                    leading_player = self._players[current_player.team_mate]  # give lead to teammate
                    assert current_player.team_mate == (current_player.position + 2) % 4
                    trick_ended = True  # no one can play on the DOG
            # fi is trick

            if not trick_ended:
                # ask all players whether they want to play a bomb
                bomb_action = self._ask_for_bomb(current_player.position)
                while bomb_action is not None:
                    bomb_player = self._players[bomb_action.player_pos]
                    logging.info(f"[BOMB] {bomb_player.position}: {bomb_action.combination}.")
                    rhb.append_event(bomb_action)
                    leading_player = bomb_player  # update the leading players
                    current_player = self._next_to_play(bomb_player.position)
                    nbr_pass = 0
                    trick_ended = True  # can only play bombs on a bomb
                    # ask again for bomb
                    bomb_action = self._ask_for_bomb(current_player.position)

            # determine the next player to play
            if not trick_ended:
                just_played = current_player
                current_player = self._next_to_play(current_player.position)

                # test if leading player wins the trick (ie, if the next player is the leading player or the leading player was jumped over)
                if (leading_player.position == current_player.position
                        or just_played.position < leading_player.position < current_player.position
                        or current_player.position < just_played.position < leading_player.position
                        or leading_player.position < current_player.position < just_played.position):
                    logging.debug("Trick ends. it's the leading_players turn again.")
                    trick_ended = True

            # end-while

        # give the trick to the correct player.
        receiving_player = leading_player
        thetrick = rhb.curr_trick_finished
        if Card.DRAGON in thetrick.last_combination:  # handle dragon trick
            dragon_away_action = leading_player.give_dragon_away(game_history=self._history, trick=thetrick)
            rhb.append_event(dragon_away_action)
            receiving_player = self._players[dragon_away_action.to]
            assert receiving_player.position != leading_player.position and receiving_player.position != (leading_player.position+2) % 4
            logging.info(f"[GIVE DRAGON TRICK] {leading_player.position} -> {receiving_player.position}")

        # give trick to the receiving player
        rhb.append_event(WinTrickEvent(player_pos=receiving_player.position, trick=thetrick, hand_cards=self.make_handcards_snapshot()))
        receiving_player.add_trick(thetrick)

        logging.info(f"[WIN TRICK] {receiving_player.position}: ({thetrick})")

        # return the leading player and the wish
        return leading_player, wish

    def make_handcards_snapshot(self):
        return HandCardSnapshot(*[ImmutableCards(pl.hand_cards) for pl in self._players])

    def _finish_round(self):
        """
        Gives the hand cards of the last players to the enemy and the tricks to the first players and counts the points for each team.
        :return a tuple (points of team 1, points of team 2) ie. (point of players 0 and 2, point of players 1 and 3)
        """
        rhb = self._history.current_round
        logging.info("Finishing Round, ranking: {}".format(rhb.ranking))

        winner_pos = rhb.ranking[0]
        # grand + normal tichu
        points = self._calculate_tichu_points()
        logging.debug("points after tichu: {}".format(points))

        # doppelsieg
        if rhb.is_double_win():
            logging.info("[DOUBLE WIN]")
            points[winner_pos] += 200
        else:
            loosing_pos = rhb.ranking[-1]
            logging.info(f"No double win (winner:{winner_pos}, looser:{loosing_pos})")
            # last players gives hand_card points to enemy ...
            loosing_handcard_points = self._players[loosing_pos].remove_hand_cards().count_points()
            points[(loosing_pos+1) % 4] += loosing_handcard_points

            logging.debug(f"points after hands to enemy: enemy-of-looser:{(loosing_pos+1) % 4}: {points}")

            # ... and tricks to first players
            loosing_trick_points = self._players[loosing_pos].count_points_in_tricks()
            points[winner_pos] += loosing_trick_points
            self._players[loosing_pos].remove_tricks()

            logging.debug(f"points after tricks to first: looser:{loosing_pos}: {points}")

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
        # TODO there is a nicer version in monecarlo state
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
        :return set containing all the swapped cards actions
        """
        swapcards_actions = set()
        # ask for swapcards
        for player in self._players:
            player_swapcards = player.swap_cards()

            check_true(len(player_swapcards) == 3 and all(isinstance(sc, SwapCardAction) for sc in player_swapcards), ex=IllegalActionException,
                       msg="The Swapcards must be an instance of 'SwapCardAction', but were {}".format(player_swapcards))
            for sca in player_swapcards:
                swapcards_actions.add(sca)

        # distribute swapped cards
        for player in self._players:
            player.receive_swapped_cards([sc for sc in swapcards_actions if sc.to == player.position])

        # paranoid checks:
        assert all([len(p.hand_cards) == 14 for p in self._players])
        assert all([p.hand_cards.issubset(Deck(full=True)) for p in self._players])

        return swapcards_actions

    def _ask_for_bomb(self, current_player_pos):
        """
        Asks all players whether they want to play a bomb.
        :param current_player_pos: int; The id of the players whose turn it is.
        :return The CombinationAction containing a Bomb or None if no player wants to play a bomb
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
            if pl.position not in announced_gt and pl.announce_tichu_or_not(announced_tichu=self._history.current_round.announced_tichus,
                                                                            announced_grand_tichu=list(announced_gt),
                                                                            game_history=self._history):
                self._history.current_round.append_event(TichuAction(player_pos=pl.position))
                logging.info(f"[TICHU] announced by: {pl.position}. ".ljust(35)+f"(handcards: {pl.hand_cards.pretty_string()})")
                did_announce = True
        if did_announce:
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

            if player.announce_grand_tichu_or_not(announced_grand_tichu=self._history.current_round.announced_grand_tichus):
                self._history.current_round.append_event(GrandTichuAction(k))
                logging.info(f"[GRAND TICHU] announced by: {player.position}. ".ljust(35)+f"(handcards: {player.hand_cards.pretty_string()})")

            player.receive_last_6_cards(last_6)

        # notify all players about the announced grand tichus
        self._notify_all_players_about_tichus()

        # return the distributed hand_cards
        return piles
