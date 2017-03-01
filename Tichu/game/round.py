from cards import *
from player import DummyPlayer
from exceptions import *

class TichuAnounced():
    def __init__(self, nbr_players=4):
        self._nbr_players = nbr_players
        self._grand_tichu = {k: False for k in range(nbr_players)}
        self._normal_tichu = {k: False for k in range(nbr_players)}

    def copy(self):
        """
        Returns a deep copy of this TichuAnounced instance.
        """
        cpy = TichuAnounced(nbr_players=self._nbr_players)
        cpy._grand_tichu = {k: self._grand_tichu[k] for k in self._grand_tichu}
        cpy._normal_tichu = {k: self._normal_tichu[k] for k in self._normal_tichu}
        return cpy

    def announce_grand_tichu(self, playerID):
        self._grand_tichu[playerID] = True

    def announce_tichu(self, playerID):
        self._normal_tichu[playerID] = True

    def has_announced_grand_tichu(self, playerID):
        return return self._grand_tichu[playerID]

    def has_announced_tichu(self, playerID):
        return self._normal_tichu[playerID]

    def get_announced_grand_tichu(self):
        return [k for k in self._grand_tichu if self._grand_tichu[k]]

    def get_announced_tichu(self):
        return [k for k in self._normal_tichu if self._normal_tichu[k]]

class Round():

    def __init__(self, teams):
        # TODO what to do when both teams may win in this round.
        """
        Creates a new Round for the game TichuGame
        players: list (of length 4) containing the players. The players at position 0 and 2 (team1) play against position 1 and 3 (team2)
        """
        if any([not isinstance(t, Team) for t in teams])
        # TODO check parameters
        self._teams = teams
        self._players = [teams[0].first_player(), teams[1].first_player(), teams[0].second_player(), teams[1].second_player()]
        self._tichus = TichuAnounced()
        self._player_ranks = []

    def run(self):
        # distribute cards
        hand_cards = self._distribute_cards()

        # Players may announce a normal tichu before card swap
        self._ask_for_tichu()

        # card swaps
        self._swap_cards()

        # round-loop
        leading_player = self._mahjong_player(hand_cards) # player with MAHJONG Starts

        while self._nbr_finished_players < 3: # while more than 1 players have cards left
            leading_player = self._run_trick(leading_player=leading_player)

        # round ended, count scores
        (score_t1, score_t2) = self._count_scores()

        return None # TODO decide what to return.

    def _team_of(self, player):
        return self._teams[0] if self._teams[0].in_team(player) else self._teams[1]

    def _count_scores(self):
        points = {k: 0 for k in range(4)}
        winnerID = self._player_ranks[0]
        # grand + normal tichu
        # successful
        if self._tichus.has_announced_grand_tichu(winnerID):
            points[winnerID] += 200
        elif self._tichus.has_announced_grand_tichu(winnerID):
            points[winnerID] += 100

        # unsuccessful IMPROVE write nicer
        for pID in [pID for pID in self._tichus.get_announced_grand_tichu() if pID != winnerID]:
            points[pID] -= 200
        for pID in [pID for pID in self._tichus.get_announced_tichu() if pID != winnerID]:
            points[pID] -= 100







        # TODO doppelsieg
        # TODO last player; handcards to enemy, tricks to first player
        # TODO count points in tricks

    def _run_trick(self, leading_player):
        """
        Leads through a trick (and updates the game state accordingly)
        leading_player: the Player to  play first.
        Returns the player to go next
        """

        next_to_play = leading_player
        trick = leading_player.play_first() # QUESTION give 'game state' as argument?
        # TODO check validity of the move
        # TODO if valid, update gamestate (inkl update handcards and if player finished)
        if Card.DOG in trick:
            # TODO give the dog to the leading players tricks
            # TODO maybe just jump over the while loop (to have the 'end trick' handling in the same place)
            return self._teammate(leading_player.id)
        # TODO ask all players for bomb play. ( for p in active players: ...) if if p.play_bomb(): ... and set nbr_pass = 0

        # trick-loop
        highest_trick = trick
        nbr_pass = 0
        while nbr_pass < 3:
            next_to_play = self_next_to_play(next_to_play.id) # QUESTION don't use player.id (players should not be able to change own id)
            # demand move form player
            action = next_to_play.play_combination(on_trick=highest_trick) # QUESTION give 'game state' as argument?
            # TODO check validity of the move
            # if pass
            if action.type is CombinationType.PASS:
                nbr_pass += 1
            else: # if trick
                highest_trick = action
                leading_player = next_to_play
                nbr_pass = 0
                # TODO update gamestate (inkl update handcards and if player finished)
            # TODO ask all players for bomb play.
        # end-while

        # TODO give the whole trick to the leading player
        # TODO handle Dragon trick (if highest_trick is Dragon: ...)

        # return the leading player
        return leading_player

    def _swap_cards(self):
        """
        Asks all players to swap cards.
        Returns None
        """
        # QUESTION create a 'SwapCards' class? -> change description of players methods
        distribute_cards = {k: [] for k in range(4)}
        # ask for swapcards
        for p in self._players:
            swapcards = p.swap_cards()
            assert 1 in swapcards and -1 in swapcards and 'teammate' in swapcards
            distribute_cards[p.id + 1 % 4].append(swapcards[1])
            distribute_cards[p.id - 1 % 4].append(swapcards[-1])
            distribute_cards[p.id + 2 % 4].append(swapcards['teammate'])
        # TODO distribute swapped cards

        return None

    def _ask_for_tichu(self):
        """
        Asks all players whether they want to announce a Tichu.
        Returns True iff at least one player announced a Tichu, False otherwise
        """
        # TODO can't announce tichu if already anounced grand tichu
        did_announce = False
        for p in self._players:
            if p.announce_tichu_or_not(self._tichus.get_announced_tichu()):
                self._tichus.announce_tichu(p.id)
                did_announce = True
        for p in self._players:
            p.players_announced_tichu(self._tichus.get_announced_tichu())
        return did_announce

    def _next_to_play(self, current_playerID):
        """ Returns the next player that still has handcards left """
        next_to_playID = (current_playerID + 1) % 4
        while self._nbr_handcards(next_to_playID) == 0:
            # make sure no infinite loop happens
            if next_to_playID == current_playerID:
                raise LogicError("No player has any cards left!")
            next_to_playID = (next_to_playID + 1) % 4
        return self._players[next_to_playID]

    def _nbr_handcards(self, playerID):
        """ Returns the number of handcards of the player with the given playerID """
        # TODO implement
        raise NotImplemented()

    def _nbr_finished_players(self):
        """ Returns the number of players with no handcards left """
        # TODO implement
        raise NotImplemented()

    def _teammate(self, playerID):
        """ Returns the teamate of the player with the given playerID"""
        return self._players[(playerID + 2) % 4]

    def _mahjong_player(self, hand_cards):
        """
        Returns the player holding the mahjong
        Raises a LogicError if no such player exists.
        """
        # TODO

    def _distribute_cards(self):
        """
        Distributes 14 cards to each player and asks after the 8th card for a grand Tichu.
        Returns the distributed hand_cards as a list of Cards instances
        """
        deck = Deck(full=True, sorted_=False)
        piles = deck.split(nbr_piles=4)
        assert all([isinstance(pile, Cards) and len(pile) == 14 for pile in piles]) # make sure the piles are correct (are Cards instances and have size 14)

        # distribute cards and ask for grand tichus
        for k in range(0, 4):
            self._players[k].receive_first_8_cards(piles[k][0:8])
            if self._players[k].anounce_grand_tichu_or_not(announced=self._tichus.get_announced_grand_tichu()):
                self._tichus.announce_grand_tichu(player=k)
            self._players[k].receive_last_6_cards(piles[k][8:14])

        # notify all players about the announced grand tichus
        for player in self._players:
            player.players_announced_grand_tichu(announced=self._tichus.get_announced_grand_tichu())

        # return the distributed hand_cards
        return piles
