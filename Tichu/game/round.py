import warnings
from collections import namedtuple
from game.cards import Card, Deck, Cards, CardValue
from game.exceptions import LogicError, IllegalActionError
from game.abstract_tichuplayer import PlayerAction, TichuPlayer


class Trick(object):
    """ List of PlayerActions """

    def __init__(self):
        self._actions = list()

    def is_empty(self):
        return len(self._actions) == 0

    def add(self, action, check_validity=True):
        """
        :param action: the PlayerAction to be added.
        :param check_validity: boolean (default True); If True, checks whether the action can be played on the given trick.
        :return: self
        :raise ValueError: if check_validity=True and the check fails.
        :raise ValueError: if the action is not a PlayerAction
        """
        if not isinstance(action, PlayerAction):
            raise ValueError("action must be a PlayerAction")
        if check_validity:
            if self.is_empty() and action.is_pass():
                raise ValueError("Cant add a pass action on an empty trick. ({}) -> ({})".format(action, self.__repr__()))
            elif not self.is_empty() and not action.can_be_played_on(self.last_combination()):
                raise ValueError("Cant play {} on {}.".format(action, self.__repr__()))
        self._actions.append(action)
        return self

    @property
    def combinations(self):
        return [a.combination for a in self._actions]

    def is_dragon_trick(self):
        return Card.DRAGON in self.last_combination()

    def last_combination(self):
        return self._actions[-1].combination

    def last_action(self):
        return self._actions[-1]

    def copy(self):
        new_trick = Trick()
        for action in self._actions:
            new_trick.add(action, check_validity=False)
        return new_trick

    def __repr__(self):
        "Trick({})".format(' -> '.join([repr(com) for com in self._actions]))

    def __iter__(self):
        return self._actions.__iter__()

    def __contains__(self, item):
        # item may be a combination or an action.
        return item in self._actions or item in self.combinations


class TichuAnnounced(object):
    """
    Keeps track of announced Tichus
    """

    def __init__(self, nbr_players=4):
        self._nbr_players = nbr_players
        self._grand_tichu = {k: False for k in range(nbr_players)}
        self._normal_tichu = {k: False for k in range(nbr_players)}

    def copy(self):
        """
        Returns a deep copy of this TichuAnnounced instance.
        """
        cpy = TichuAnnounced(nbr_players=self._nbr_players)
        cpy._grand_tichu = {k: self._grand_tichu[k] for k in self._grand_tichu}
        cpy._normal_tichu = {k: self._normal_tichu[k] for k in self._normal_tichu}
        return cpy

    def announce_grand_tichu(self, player_id):
        self._grand_tichu[player_id] = True

    def announce_tichu(self, player_id):
        if self.has_announced_grand_tichu(player_id):
            raise IllegalActionError(
                "Player({}) can't announce normal Tichu when already announced grand Tichu.".format(player_id))
        self._normal_tichu[player_id] = True

    def has_announced_grand_tichu(self, player_id):
        return self._grand_tichu[player_id]

    def has_announced_tichu(self, player_id):
        return self._normal_tichu[player_id]

    def get_announced_grand_tichu(self):
        """
        :return: List[int], the list containing all players that announced a grand tichu
        """
        # TODO Improvement, can be made more efficient by storing the list.
        return [k for k in self._grand_tichu if self._grand_tichu[k]]

    def get_announced_tichu(self):
        """
        :return: List[int], the list containing all players that announced a normal tichu
        """
        # TODO Improvement, can be made more efficient by storing the list.
        return [k for k in self._normal_tichu if self._normal_tichu[k]]

    def tichu_points(self, winner_id):
        """
        :param winner_id: int, The id of the player finished first
        :return: dict{int: points}, a dict containing the points of each player gained (or lost) by succeeding or failing to fullfill a (grand)Tichu
        """
        points_gt = {pid: val * -200 for pid, val in self._grand_tichu.items()}  # assuming all players failed
        points_gt[winner_id] *= -1  # inverse winner points.
        points_t = {pid: val * -100 for pid, val in self._normal_tichu.items()}  # assuming all players failed
        points_t[winner_id] *= -1  # inverse winner points.
        return {pid: points_gt[pid] + points_t[pid] for pid in range(self._nbr_players)}  # put together


class Ranking(object):
    """
    Keeps track of the order the players finished
    """

    def __init__(self, team1, team2):
        self._teams = [team1, team2]

        self._players = [self._teams[0].first_player,
                         self._teams[1].first_player,
                         self._teams[0].second_player,
                         self._teams[1].second_player]

        self._rank = list()

    @property
    def ranking(self):
        return list(self._rank)

    @property
    def winner(self):
        """
        :return: The winner of the round. None if there is no winner yet.
        """
        return self._rank[0] if len(self._rank) > 0 else None

    @property
    def looser(self):
        """
        :return: The looser of the round. None if there is no looser yet.
        """
        return self._rank[3] if len(self._rank) == 4 else None

    def rank_of(self, player):
        """
        :param player:
        :return: The rank of the given player (starting from 1), or None if the player has no rank
        """
        return self._rank.index(player) + 1 if player in self._rank else None

    def next_to_finish(self, player):
        """
        Adds the player_id to the ranking.
        :param player: int, must be a player with valid player.id and must not yet be in the ranking.
        :raise ValueError if player_id is not valid
        """
        if player.id not in range(4) or player in self._rank:
            raise ValueError("player({}) not valid for {}.".format(player, self.__repr__()))
        self._rank.append(player)

    def is_double_win(self):
        """
        :return: True iff the first two players are on the same team, False otherwise. (if less than 2 players finished, then also false).
        """
        if len(self._rank) < 2:
            return False

        return any([self._rank[0] in team and self._rank[1] in team for team in self._teams])

    def __repr__(self):
        return "Ranking({})".format(', '.join(["{}:{}".format(rank, pl.short_str()) for rank, pl in enumerate(self._rank)]))

    def __iter__(self):
        return list(self._rank.__iter__())

    def __contains__(self, item):
        return self._rank.__contains__(item)

    def __len__(self):
        return len(self._rank)


class CardSwap(object):
    """
    Stores a CardSwap.
    - a card
    - a recipient
    """

    def __init__(self, card, to):
        if not isinstance(card, Card):
            raise ValueError("Card must be instance of Card")
        elif to not in range(4):
            raise ValueError("'to' must be integer in [0, 1, 2, 3]")

        self._card = card
        self._to = to

    @property
    def to(self):
        return self._to

    @property
    def card(self):
        return self._card

Card_To = namedtuple("Card_To", ["card", "to"])
SwapCard = namedtuple("SwapCard", ["card", "from_", "to"])


class SwapCards(object):
    """
    Contains 3 CardSwap instances from a player.
    """

    def __init__(self, player, card_to1, card_to2, card_to3):
        swapcards = [card_to1, card_to2, card_to3]

        # validate input
        if not all([isinstance(ct, Card_To) and isinstance(ct.card, Card) and ct.to in range(4) for ct in swapcards]):
            raise ValueError("The card_toX must be instance of Card_To and card must be instance of Card and 'to' must be in range(4).")
        if not isinstance(player, TichuPlayer):
            raise ValueError("The player must be instance of TichuPlayer")
        if player.id in [sc.to for sc in swapcards]:
            raise ValueError("can't swap a card to itself")
        if not len(set([sc.to for sc in swapcards])) == 3:
            raise ValueError("must have 3 different recipients")
        if not len(set([sc.card for sc in swapcards])) == 3:
            raise ValueError("must have 3 different cards")
        if not all([sc.card in player.hand_cards for sc in swapcards]):
            raise ValueError("the player must possess all 3 cards")

        self._swapcards = tuple([SwapCard(card=sc.card, from_=player.id, to=sc.to) for sc in swapcards])
        self._from = player.id

    @property
    def swapcards(self):
        return self._swapcards

    @property
    def from_id(self):
        return self._from

    def __iter__(self):
        return self._swapcards.__iter__()

    def __contains__(self, item):
        return self._swapcards.__contains__(item)

    def __getitem__(self, item):
        return self._swapcards.__getitem__(item)


class Round(object):
    def __init__(self, team1, team2):
        # TODO what to do when both teams may win in this round.
        """
        Creates a new Round for the game TichuGame
        :param team1: The first team
        :param team2: The second team
        """
        self._teams = [team1, team2]

        self._players = [self._teams[0].first_player,
                         self._teams[1].first_player,
                         self._teams[0].second_player,
                         self._teams[1].second_player]
        self._tichus = TichuAnnounced()
        self._player_ranking = Ranking(team1, team2)  # used to store which player finished at which position

    def run(self):
        """
        Runs a single round (from distributing cards until 3 players finished) and counts the points
        Returns a tuple with points of the teams (points of team 1, points of team 2)
        """
        # distribute cards
        self._distribute_cards()

        # Players may announce a normal tichu before card swap
        self._ask_for_tichu()

        # card swaps
        self._swap_cards()

        # round-loop
        leading_player = self._mahjong_player()

        while self._nbr_finished_players() < 3:  # while more than 1 player has cards left
            leading_player = self._run_trick(leading_player=leading_player)
            if leading_player.has_finished():  # if the leading player has already finished
                leading_player = self._next_to_play(leading_player.position)

        # round ended, count scores
        (score_t1, score_t2) = self._finish_round()

        return (score_t1, score_t2)

    def _run_trick(self, leading_player):
        """
        Leads through a trick (and updates the game state accordingly)
        leading_player: the Player to  play first.
        Returns the player to go next
        """

        def _check_action_validity(action, player, on_trick):
            """
            Tests:
            - whether action is a PlayerAction
            - whether the player has the cards to play that combination
            - the combination can be played on the trick_on_table
            :param action: PlayerAction; The action
            :param player: The player playing the action
            :param on_trick: The trick the action is played on.
            :raise an IllegalActionError if move is not valid.
            :return True otherwise
            """
            if not isinstance(played_action, PlayerAction):
                raise IllegalActionError("{} is no PlayerAction.".format(action))
            action.does_player_have_cards(player=player, raise_exception=True)
            action.can_be_played_on(on_trick.last_combination(), raise_exception=True)
            return True

        trick_ended = False
        trick_on_table = Trick()
        next_to_play = leading_player
        nbr_pass = 0
        wish = None
        while nbr_pass < 3 and not trick_ended:
            played_action = None
            if trick_on_table.is_empty():  # first play of the trick
                played_action = next_to_play.play_first()
                if played_action.is_pass():
                    raise IllegalActionError("First to play can't PASS.")
            else:
                played_action = next_to_play.play_combination(on_trick=trick_on_table, wish=wish)

            # check validity of the action
            _check_action_validity(played_action, next_to_play, trick_on_table)

            if played_action.is_pass():
                nbr_pass += 1
            else:  # if trick
                # handle tichu
                if played_action.is_tichu() and next_to_play.can_announce_tichu():
                    self._tichus.announce_tichu(next_to_play.id)
                    self._notify_all_players_about_tichus()

                # update the players hand_cards
                next_to_play.hand_cards.remove_all(played_action.combination)
                # update the trick on the table
                trick_on_table.add(played_action)
                # update the leading_player
                leading_player = next_to_play
                # update the nbr pass actions
                nbr_pass = 0

                # verify wish
                if wish is not None:
                    if not played_action.is_pass() and wish in {c.cardvalue for c in played_action.combination}:
                        wish = None  # wish is satisfied
                    elif wish in {c.cardvalue for c in next_to_play.hand_cards}:  # TODO! make correct
                        warnings.warn("Must comply with the wish when possible.")

                # handle Mahjong (wish)
                if Card.MAHJONG in played_action.combination:
                    # ask for wish
                    wish = next_to_play.wish()
                    if (not isinstance(wish, CardValue) and wish is not None) or wish in {CardValue.PHOENIX, CardValue.DRAGON, CardValue.DOG, CardValue.MAHJONG}:
                        raise IllegalActionError("The wish must be a CardValue and not a special card.")

                # if the player finished with this move
                if next_to_play.has_finished():
                    self._player_ranking.next_to_finish(next_to_play.position)

                    # test doppelsieg
                    trick_ended = trick_ended or self._player_ranking.is_double_win()

                    # test whether 3rd player to win and thus ends the trick.
                    # (3rd to win automatically gets the last trick)
                    if len(self._player_ranking) == 3:
                        self._player_ranking.next_to_finish(
                            self._next_to_play(next_to_play.position))  # add last player
                        trick_ended = True

                # handle dog
                if Card.DOG in played_action.combination:
                    assert len(played_action.combination) == 1  # just to be sure
                    leading_player = self._teammate(next_to_play.position)  # give lead to teammate
                    trick_ended = True  # no one can play on the DOG
            # fi

            if not trick_ended and not played_action.is_pass():
                # ask all players whether they want to play a bomb
                bomb_action = self._ask_for_bomb(trick_on_table, next_to_play.position)
                while bomb_action is not None:
                    # is it really a bomb?
                    if not bomb_action.is_bomb():
                        raise IllegalActionError("Only bombs can be played here!")

                    bomb_player = bomb_action.player
                    _check_action_validity(bomb_action, bomb_player, trick_on_table)
                    trick_on_table.add(bomb_action)  # update the trick on the table
                    bomb_player.hand_cards.remove_all(
                        bomb_action.combination)  # remove the played cards from the players hand
                    leading_player = bomb_player  # update the leading player
                    next_to_play = self._next_to_play(bomb_player.position)
                    nbr_pass = 0

                    # ask again for bomb
                    bomb_action = self._ask_for_bomb(trick_on_table, next_to_play.position)

            # determine the next player to play
            next_to_play = self._next_to_play(next_to_play.position)

        # end-while

        # give the trick to the correct player.
        receiving_player = leading_player
        if trick_on_table.is_dragon_trick():  # handle dragon trick
            receiving_player = self._players[leading_player.give_dragon_away(trick_on_table.copy())]

        # give trick to the correct player
        receiving_player.tricks.append(trick_on_table)

        # return the leading player
        return leading_player

    def _team_of(self, player):
        """
        :param player
        :return the team of the given player
        """
        # TODO better solution? Dict for example
        t = self._teams[0] if player in self._teams[0] else self._teams[1]
        assert player in t  # just to be sure
        return t

    def _finish_round(self):
        """
        Gives the hand cards of the last player to the enemy and the tricks to the first player and counts the points for each team.
        :return a tuple (points of team 1, points of team 2) ie. (point of player 0 and 2, point of player 1 and 3)
        """
        # TODO add some asserts to make sure everything is as expected
        assert len(self._player_ranking) == 4

        winner_id = self._player_ranking.winner
        # grand + normal tichu
        points = self._tichus.tichu_points(winner_id)

        # doppelsieg
        if self._player_ranking.is_double_win():
            points[winner_id] += 200
        else:
            loosing_id = self._player_ranking.looser
            # last player gives hand_cards to enemy ...
            self._players[(loosing_id + 1) % 4].tricks.append(self._players[loosing_id].remove_hand_cards())

            # ... and tricks to first player
            self._players[winner_id].tricks.add_all(self._players[loosing_id].remove_tricks())

            # count points in tricks
            for p_id in range(4):
                points[p_id] += sum([cards.sum() for cards in self._players[p_id].tricks])

        return (points[0] + points[2], points[1] + points[3])

    def _swap_cards(self):
        """
        Asks all players to swap cards.
        :return List containing the swapped cards
        """
        swapcards = set()
        # ask for swapcards
        for pl in self._players:
            pl_swapcards = pl.swap_cards()
            if not isinstance(pl_swapcards, SwapCards):
                raise IllegalActionError("The Swapcards must be an instance of 'SwapCards', but were {}".format(pl_swapcards.__class__))
            for sc in pl_swapcards:
                swapcards.add(sc)
        # distribute swapped cards
        for pl in self._players:
            pl.receive_swapped_cards([sc for sc in swapcards if sc.to == pl.id])

        return True

    def _ask_for_bomb(self, trick_on_table, current_player_id):
        """
        Asks all players whether they want to play a bomb.
        :param trick_on_table: Trick; The trick on the table.
        :param current_player_id: int; The id of the player whose turn it is.
        :return The player that wants to play a bomb. Or None if no player plays a bomb.
        """
        p_id = self._next_to_play(current_player_id)
        while p_id != current_player_id: # To prevent infinite loop
            p = self._players[p_id]
            if not p.has_finished():
                bomb_action = p.play_bomb_or_not(trick_on_table)
                if bomb_action:
                    return bomb_action
            p_id = (p_id + 1) % 4
        return None

    def _ask_for_tichu(self):
        """
        Asks all players whether they want to announce a Tichu.
        :return True iff at least one player announced a Tichu, False otherwise
        """

        did_announce = False
        for pl in self._players:
            # can't announce tichu if already announced grand tichu
            if not self._tichus.has_announced_grand_tichu(pl.position) and pl.announce_tichu_or_not(
                    self._tichus.get_announced_tichu(), self._tichus.get_announced_grand_tichu()):
                self._tichus.announce_tichu(pl.id)
                did_announce = True

        self._notify_all_players_about_tichus()

        return did_announce

    def _notify_all_players_about_tichus(self):
        """
        Notifies all players who announced grand and normal tichus.
        :return: Nothing
        """
        for pl in self._players:
            pl.players_announced_tichu(self._tichus.get_announced_tichu())
            pl.players_announced_grand_tichu(self._tichus.get_announced_grand_tichu())

    def _next_to_play(self, current_player_id):
        """
        :param current_player_id: int; The id of the player whose turn it is currently.
        :return the next player that still has handcards left
        """
        next_to_play_id = (current_player_id + 1) % 4
        while self._players[next_to_play_id].has_finished:
            # make sure no infinite loop happens
            if next_to_play_id == current_player_id:
                raise LogicError("No player has any cards left!")
            next_to_play_id = (next_to_play_id + 1) % 4
        return self._players[next_to_play_id]

    def _nbr_finished_players(self):
        """ Returns the number of players with no handcards left """
        return len(self._player_ranking)

    def _teammate(self, player_id):
        """ Returns the teamate of the player with the given playerID"""
        return self._players[(player_id + 2) % 4]

    def _mahjong_player(self):
        """
        Returns the player holding the mahjong
        Raises a LogicError if no such player exists.
        """
        for p in self._players:
            if Card.MAHJONG in p.hand_cards:
                return p
        raise LogicError("No player has MAHJONG card")

    def _distribute_cards(self):
        """
        Distributes 14 cards to each player and asks after the 8th card for a grand Tichu.
        Returns the distributed hand_cards as a list of Cards instances
        """
        # remove all cards from the players
        for pl in self._players:
            pl.remove_hand_cards()
            pl.remove_tricks()

        deck = Deck(full=True)
        piles = deck.split(nbr_piles=4, random_=True)
        assert all([len(pile) == 14 for pile in piles])  # make sure the piles are correct (have size 14)
        for pile in piles:
            assert all([isinstance(c, Card) for c in pile])

        # distribute cards and ask for grand tichus
        for k in range(0, 4):
            self._players[k].receive_first_8_cards(piles[k][0:8])
            if self._players[k].announce_grand_tichu_or_not(announced_tichu=[], announced_grand_tichu=self._tichus.get_announced_grand_tichu()):
                self._tichus.announce_grand_tichu(player_id=k)
            self._players[k].receive_last_6_cards(piles[k][8:14])

        # notify all players about the announced grand tichus
        for player in self._players:
            player.players_announced_grand_tichu(announced=self._tichus.get_announced_grand_tichu())

        # return the distributed hand_cards
        return piles
