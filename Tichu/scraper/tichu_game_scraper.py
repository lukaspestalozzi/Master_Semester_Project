import traceback
from collections import defaultdict
import datetime

import json
import functools
import requests
import grequests as greq
import sys
import glob

import time
from bs4 import BeautifulSoup
import os
import errno
from collections import namedtuple

from itertools import islice

from Tichu.tichu.game.gameutils import *
from Tichu.tichu.cards.card import Card as C
from tichu.cards.cards import ImmutableCards
from tichu.players.tichuplayers import TichuPlayer


class Player(namedtuple('Player', ['rank', 'name', 'nbr_games', 'nbr_won_games', 'elo'])):

    def __init__(self, *args, **kwargs):
        super().__init__()

    def __hash__(self):
        return super().__hash__()

    def __eq__(self, other):
        return super().__eq__(other)


class GameOverview(namedtuple('GameOverview', ['date', 'p0', 'p1', 'p2', 'p3', 'result', 'won_rounds', 'highcards', 'bombs', 'tichus', 'grand_tichus', 'game_number'])):
    def __init__(self, *args, **kwargs):
        super().__init__()

    def __hash__(self):
        return super().__hash__()

    def __eq__(self, other):
        return super().__eq__(other)


class Game(namedtuple('Game', ['game_overview', 'p0', 'p1', 'p2', 'p3', 'result', 'rounds'])):
    def __init__(self, *args, **kwargs):
        super().__init__()
    """
    def to_tichu_game_history(self):
        player0 = TichuPlayer(name=self.p0, agent=None)
        player1 = TichuPlayer(name=self.p1, agent=None)
        player2 = TichuPlayer(name=self.p2, agent=None)
        player3 = TichuPlayer(name=self.p3, agent=None)
        team1 = Team(player0, player2)
        team2 = Team(player1, player3)

        points_t1 = int(self.result.split(':')[0])  # TODO make self.result a tuple
        points_t2 = int(self.result.split(':')[1])
        winner_team = team1 if points_t1 > points_t2 else team2

        rounds = tuple([round_.to_round_history() for round_ in self.rounds])

        gh = GameHistory(team1=team1, team2=team2, winner_team=winner_team,
                         points=(points_t1, points_t2), target_points=1000, rounds=rounds)
        return gh
    """

    def __hash__(self):
        return hash((self.game_overview, self.result))

    def __eq__(self, other):
        return super().__eq__(other)


class Round(namedtuple('Round', ['initial_points', 'result', 'gt_hands', 'grand_tichus', 'tichus', 'trading_hands', 'traded_cards',
                                 'complete_hands', 'moves'])):
    def __init__(self, *args, **kwargs):
        super().__init__()

    """
    def to_round_history(self, player_0_name, player_1_name, player_2_name, player_3_name):
        player_names = [player_0_name, player_1_name, player_2_name, player_3_name]
        def to_cards_list(hands_dict):
            return [hands_dict[player_0_name], hands_dict[player_1_name],
                    hands_dict[player_2_name], hands_dict[player_3_name]]

        def player_name_to_pos(name):
            return player_names.index(name)

        rhb = RoundHistoryBuilder(self.initial_points)
        # hands
        rhb.grand_tichu_hands = cards_class_lists_to_snapshot(*to_cards_list(self.gt_hands))
        rhb.before_swap_hands = cards_class_lists_to_snapshot(*to_cards_list(self.trading_hands))
        rhb.complete_hands = cards_class_lists_to_snapshot(*to_cards_list(self.complete_hands))

        # grand_tichus
        for player_name in self.grand_tichus:
            rhb.append_event(GrandTichuAction(player_name_to_pos(player_name)))

        # normal tichus  TODO add at actual position in the game (take care of tichus announced before swaping)
        for player_name in self.tichus:
            rhb.append_event(TichuAction(player_name_to_pos(player_name)))

        # swap cards
        for player_name, traded_cards in self.traded_cards.items():  # traded cards: plname -> tuple(c to right, c to teammate, c to left)
            player_pos = player_name_to_pos(player_name)
            to_cards = [((player_pos+idx+1) % 4, card_class_to_tichu_card(cc)) for idx, cc in enumerate(traded_cards)]
            rhb.append_event(SwapCardAction(player_pos, to_cards[0], to_cards[1]))

        trick = UnfinishedTrick()
        for move in self.moves:
            player_pos = player_name_to_pos(move.player_name)
            if move.is_pass:
                rhb.append_event(PassAction(player_pos))

            if move.is_clear:
                rhb.append_event(WinTrickEvent(player_pos, trick.finish(), ))

            if move.dragon_to:
                rhb.append_event(GiveDragonAwayAction(player_pos, player_name_to_pos(move.dragon_to), trick.finish()))

            if move.tichu:
                rhb.append_event(TichuAction(player_pos))

            if len(move.cards_played):
                comb = Combination.make(cards_class_list_to_immutable_cards(move.cards_played))
                rhb.append_event(CombinationAction(player_pos, comb))
                trick.append(comb)
    """

    def __hash__(self):
        return hash(tuple(self.moves))

    def __eq__(self, other):
        return super().__eq__(other)


class Move(namedtuple('Move', ['cards_before', 'player_name', 'cards_played', 'is_pass', 'is_clear', 'tichu', 'dragon_to'])):
    def __init__(self, *args, **kwargs):
        super().__init__()

    def __hash__(self):
        return hash((tuple(self.cards_before), self.player_name, tuple(self.cards_played), self.is_pass, self.is_clear, self.tichu, self.dragon_to))

    def __eq__(self, other):
        return super().__eq__(other)


class_to_card_dict = {
        'c_00': C.DOG,
        'c_10': C.MAHJONG,
        'c_21': C.TWO_SWORD,
        'c_32': C.THREE_PAGODA,
        'c_43': C.FOUR_JADE,
        'c_54': C.FIVE_HOUSE,
        'c_61': C.SIX_SWORD,
        'c_72': C.SEVEN_PAGODA,
        'c_83': C.EIGHT_JADE,
        'c_94': C.NINE_HOUSE,
        'c_101': C.TEN_SWORD,
        'c_112': C.J_PAGODA,
        'c_123': C.Q_JADE,
        'c_134': C.K_HOUSE,
        'c_141': C.A_SWORD,
        'c_22': C.TWO_PAGODA,
        'c_33': C.THREE_JADE,
        'c_44': C.FOUR_HOUSE,
        'c_51': C.FIVE_SWORD,
        'c_62': C.SIX_PAGODA,
        'c_73': C.SEVEN_JADE,
        'c_84': C.EIGHT_HOUSE,
        'c_91': C.NINE_SWORD,
        'c_102': C.TEN_PAGODA,
        'c_113': C.J_JADE,
        'c_124': C.Q_HOUSE,
        'c_131': C.K_SWORD,
        'c_142': C.A_PAGODA,
        'c_23': C.TWO_JADE,
        'c_34': C.THREE_HOUSE,
        'c_41': C.FOUR_SWORD,
        'c_52': C.FIVE_PAGODA,
        'c_63': C.SIX_JADE,
        'c_74': C.SEVEN_HOUSE,
        'c_81': C.EIGHT_SWORD,
        'c_92': C.NINE_PAGODA,
        'c_103': C.TENJADE,
        'c_114': C.J_HOUSE,
        'c_121': C.Q_SWORD,
        'c_132': C.K_PAGODA,
        'c_143': C.A_JADE,
        'c_24': C.TWO_HOUSE,
        'c_31': C.THREE_SWORD,
        'c_42': C.FOUR_PAGODA,
        'c_53': C.FIVE_JADE,
        'c_64': C.SIX_HOUSE,
        'c_71': C.SEVEN_SWORD,
        'c_82': C.EIGHT_PAGODA,
        'c_93': C.NINE_JADE,
        'c_104': C.TEN_HOUSE,
        'c_111': C.J_SWORD,
        'c_122': C.Q_PAGODA,
        'c_133': C.K_JADE,
        'c_144': C.A_HOUSE,
        'c_150': C.PHOENIX,
        'c_160': C.DRAGON,
    }


def card_class_to_tichu_card(cclass: str):
    return class_to_card_dict[cclass]


def cards_class_list_to_immutable_cards(clist):
    return ImmutableCards([card_class_to_tichu_card(cc) for cc in clist])


def cards_class_lists_to_snapshot(clist0, clist1, clist2, clist3):
    imm_cards = [cards_class_list_to_immutable_cards(cl) for cl in [clist0, clist1, clist2, clist3]]
    return HandCardSnapshot(*imm_cards)


def pretty_print_game(game: Game):
    print(game.game_overview)
    print()
    print(game.result)
    print(game.p0, 'and', game.p2, "vs.", game.p1, 'and', game.p3)
    print('rounds:')
    for round_ in game.rounds:
        print("=================================================================")
        print(round_.result)
        print('gt_hands', round_.gt_hands)
        print('grand_tichus', round_.grand_tichus)
        print('trading_hands', round_.trading_hands)
        print('traded_cards', round_.traded_cards)
        print('complete_hands', round_.complete_hands)
        print("moves:")
        for move in round_.moves:
            print("---------------------------------")
            print('player', move.player_name)
            print('cards_before', move.cards_before)
            print('cards_played', move.cards_played)
            print('is_pass:', move.is_pass, ', is_clear:', move.is_clear,
                  ', tichu:', move.tichu, ', dragon_to:', move.dragon_to)


def exceptions_to_warning(function):
    """
    A decorator that wraps the passed in function and warns the exception text, should one occur
    :return In case of an exception, the decorator/function returns None, otherwise whatever the function returns
    """

    @functools.wraps(function)
    def wrapper(*args, **kwargs):
        try:
            return function(*args, **kwargs)
        except Exception as ex:
            print(f"There was an exception in '{function.__name__}': text: ", repr(ex), "traceback: ", file=sys.stderr,
                  flush=True)
            traceback.print_tb(ex.__traceback__)

            return None

    return wrapper


def grouper(n, iterable):
    """

    :param n: integer > 0
    :param iterable: any iterable
    :return: Generator yielding tuples of size n from the iterable
    """
    it = iter(iterable)
    while True:
        chunk = tuple(islice(it, n))
        if not chunk:
            return
        yield chunk


def now():
    """
    :return: datetime.datetime.now()
    """
    return datetime.datetime.now()


def make_sure_path_exists(path):
    """
    Creates the folder if it does not exists yet.


    :param path:
    :return:
    """
    try:
        os.makedirs(path)
    except OSError as exception:
        if exception.errno != errno.EEXIST:
            raise


class TichumaniaScraper(object):
    def __init__(self, base_url: str = 'http://log.tichumania.de/view/pages/', elolist_page: str = 'Elolist.php', games_page: str = 'Games.php', game_page: str = 'Game.php',
                 folder_path: str = './tichumania_scraper/', scraped_gamenumbers_file: str = '.gamenumbers.json', scraped_gameoverviews_file: str = '.gameoverviews.json'):

        self.base_url = base_url
        self.elolist_page = elolist_page
        self.games_page = games_page
        self.game_page = game_page

        make_sure_path_exists(folder_path)  # creates the folder if it does not exists yet

        self.scraper_out_folder = folder_path
        self.scraped_gamenumbers_file = scraped_gamenumbers_file
        self.scraped_gameoverviews_file = scraped_gameoverviews_file
        self._out_folder_f = folder_path + '{}'

        self.scraped_gamenumbers = self._load_scraped_gamenumbers()
        self.scraped_gameoverviews = self._load_scraped_game_overviews()
        self._newly_scraped_games = set()

        print("nbr scraped_gamenumbers: ", len(self.scraped_gamenumbers))
        print("nbr scraped_gameoverviews: ", len(self.scraped_gameoverviews))

    @property
    def elolist_url(self):
        return f'{self.base_url}{self.elolist_page}'

    # ==================== Public Scrape Methods ====================

    def game_url(self, game_nbr):
        return '{self.base_url}{self.game_page}?game={game_nbr}'.format(self=self, game_nbr=game_nbr)

    def save_scraped_games_to_file(self, filename='scraper_out.json'):
        return self._write_to_file(self._newly_scraped_games, filename=filename)

    """
    def find_games_of_best_players(self, nbr_players=10, nbr_games_per_player=10, return_dict=False, save_periodicaly=100):


        :param nbr_players: how many players (length of returned dict) (None means to fetch all players)
        :param nbr_games_per_player: how many games to fetch for each player (length of each set for each player); (None means to fetch all games)
        :param return_dict: If True, returns a dict player -> tuple of games for that player. if False, returns None, this is preferred if the result is not used directly as the games are already stored in the 'scraped_games' attribute.
        :param save_periodicaly: integer. calls 'save_scraped_games_to_file' after scraping the given amount of games. set negative to disable
        :return: If return_dict is True, returns a dict player -> tuple of games for that player. if False, returns None.

        start_t = time.time()
        d = dict()
        for player in islice(self.find_best_players(), nbr_players):
            if player is None:
                continue
            print(f"fetching {nbr_games_per_player} games for the player '{player.name}'")
            games_gen = islice(self.games_for_playername(player.name, save_periodicaly=save_periodicaly),
                               nbr_games_per_player)
            if return_dict:
                d[player] = tuple(game for game in games_gen)
            else:
                for _ in games_gen:  # don't store the result.
                    pass
        seconds_taken = time.time() - start_t
        print(f"done find_games_of_best_players, time: {int(seconds_taken // 60)}mins and {seconds_taken % 60 :.2f}s")
        return d if return_dict else None
    """
    def scrape_games(self, max_nbr_games: int = None, max_time: int = None):
        """
        Scrapes games until either interrupted (by CTRL-C) or max_nbr_games is reached or max_time (in minutes) is reached.
        Skips games already scraped (games in the 'scraped_games' attribute)
        Stores the games in the folder determined by the 'scraper_out_folder/games/' attribute in the file '{current_time}_scraped_games.json'.

        :param max_nbr_games:
        :param max_time:
        :return: The number of scraped games
        """
        scraped_game_nbrs = set()
        nbr_scraped = 0
        try:
            gos_batch_gen = grouper(n=8, iterable=self.game_overviews_gen())
            if not max_nbr_games:
                max_nbr_games = float('inf')
            if not max_time:
                max_time = float('inf')

            start_t = time.time()
            end_t = start_t + max_time * 60
            while nbr_scraped < max_nbr_games:
                gos_batch = next(gos_batch_gen)
                games_batch = list(self._scrape_batch_of_games(gos_batch))
                # update various lists and sets
                game_nbrs = self._update_newly_scraped_games(games_batch)
                scraped_game_nbrs.update(game_nbrs)

                nbr_scraped += len(games_batch)
                if end_t < time.time():
                    break
            return nbr_scraped
        finally:
            # store scraped games
            make_sure_path_exists(self._out_folder_f.format('games/'))
            self._write_to_file([g for g in self._newly_scraped_games if g.game_overview.game_number in scraped_game_nbrs], filename=f'games/{now().strftime("%Y-%m-%d_%H:%M")}_scraped_games.json')
            # store scraped gamenumbers
            self._store_scraped_gamenumbers()

    def scrape_players(self, out_file: str = 'players.json'):
        """
        Scrapes all players and stores them to the file (in the folder determined by the 'scraper_out_folder' attribute.)

        :param out_file:
        :return: a list of all players.
        """
        players = list(self.find_best_players())
        self._write_to_file(players, filename=out_file)
        return players

    def scrape_gameoverviews(self, out_file: str = 'game_overviews.json', max_nbr_overviews: int = None, max_time: int = None):
        """
        Scrapes gameoverviews (most recent first) until either interrupted (by CTRL-C) or max_nbr_games is reached or max_time (in minutes) is reached.
        And stores them to the out_file (in the folder determined by the 'scraper_out_folder' attribute.)

        :param out_file:
        :param max_nbr_overviews:
        :param max_time: [default None (unlimited time)] Time in Minutes after which the scraping should end (approximately).
        :return: The scraped game overviews
        """
        scraped_gos = []
        try:
            gos_gen = islice(self.game_overviews_gen(), max_nbr_overviews)
            if max_time:
                start_t = time.time()
                end_t = start_t + max_time * 60
                for go in gos_gen:
                    if go is not None:
                        scraped_gos.append(go)
                    if end_t < time.time():
                        break
            else:
                for go in gos_gen:
                    if go is not None:
                        scraped_gos.append(go)

        finally:
            self._write_to_file(scraped_gos, filename=out_file)

    # ==================== Public File Handling Methods ====================

    def all_stored_games_gen(self):
        """

        :return: Generator yielding each game that has been scraped (and is in the scraper_out_folder/games/ folder).
        """
        game_files = glob.glob(self._out_folder_f.format('games/*scraped_games*'))
        for filename in game_files:
            games = self._load_from_file(filename, default=[])
            for game in games:
                yield game



    # ==================== Private Scrape Methods ====================

    def _write_to_file(self, data, filename: str):
        """
        Writes the data to the file

        :param data:
        :param filename:
        :return:
        """
        file_path = self._out_folder_f.format(filename)
        with open(file_path, 'w') as f:
            print("Writing to file ", file_path, "data of type ", type(data), " and of length: ", len(data) if data.__len__ else 'Has no length.')
            json.dump(data, f)

    def _load_from_file(self, filename: str, default=None):
        """
        Loads data from the given file. Must have been written with the '_write_to_file' function.

        :param filename: the filename
        :param default: The value returned if the file does not exist
        :return: the object in the file or none if the file does not exist
        """
        file_path = self._out_folder_f.format(filename)
        try:
            with open(file_path, 'r') as f:
                print("Loading file ", file_path, '... ', end='', flush=True)
                data = json.load(f)
                print("loaded data of type ", type(data), " and of length: ", len(data) if data.__len__ else 'Has no length.')
                return data
        except FileNotFoundError as fnfe:
            print("file did not exist, returning default: ", default)
            return default

    def _store_scraped_gamenumbers(self):
        self._write_to_file(list(self.scraped_gamenumbers), self.scraped_gamenumbers_file)

    def _load_scraped_gamenumbers(self):
        """

        :return: A set of the numbers of the already scraped games.
        """
        gamenumbers = set(self._load_from_file(self.scraped_gamenumbers_file, default=set()))
        return gamenumbers

    def _load_scraped_game_overviews(self):
        """

        :return: a set of the already scraped gameoverviews.
        """
        gameoverviews = set(self._load_from_file(self.scraped_gameoverviews_file, default=set()))
        return gameoverviews

    def _update_newly_scraped_games(self, games):
        """
        Keeps the internal state of the newly scraped games and scraped game numbers consistent.

        :param games:
        :return: a set containing the game numbers of the given games
        """
        if not games.__iter__:
            games = [games]

        to_add = {g for g in games}
        self._newly_scraped_games.update(to_add)
        game_nbrs = {g.game_overview.game_number for g in games}
        self.scraped_gamenumbers.update(game_nbrs)
        return game_nbrs

    def _games_url(self, page_from=0, amount=100, player_name=None):
        gurl = '{self.base_url}games/content.php?start={page_from}&count={amount}'.format(self=self,
                                                                                          page_from=page_from,
                                                                                          amount=amount)
        if player_name:
            gurl += f'&player={player_name}'
        return gurl

    # ==================== Scraping Methods ====================

    # -------------------- players --------------------
    def find_best_players(self):
        """
        :return:Generator yielding players (ranked by elo score) Note: in April 2017 there were almost 5000 players
        """
        r = requests.get(url=self.elolist_url)
        soup = BeautifulSoup(r.text, 'lxml')

        for row in soup.find_all('tr'):
            player = self._player_from_soup(row)
            if player is not None:
                yield player

    @exceptions_to_warning
    def _player_from_soup(self, row_soup):
        col = row_soup.find_all('td')
        if len(col):
            t = [e.text for e in col]
            p = Player(rank=int(t[0]), name=t[1], nbr_games=int(t[2]), nbr_won_games=t[3], elo=int(t[4]))
            return p
        else:
            return None

    # -------------------- game overviews --------------------
    def game_overviews_gen(self, player_name: str = None):
        """

        :param player_name: a playername, if not None, then only returns gameoverviews where the player with this name appears in.
        :return Generator yielding GameOverviews (most recent first).
        """
        all_rows = ['dummy_element']
        next_from = 0
        amount = 100
        while len(all_rows):
            soup = BeautifulSoup(requests.get(url=self._games_url(next_from, amount, player_name=player_name)).text, 'lxml')
            next_from += amount
            all_rows = soup.find_all('tr')
            for row_soup in all_rows:
                go = self._game_overview_from_soup(row_soup)
                if go is not None:
                    yield go

    @exceptions_to_warning
    def _game_overview_from_soup(self, row_soup):
        # TODO check cache
        team0 = tuple([span.text.strip() for span in row_soup.find('td', {'title': 'Home team'}).find_all('span')])
        team1 = tuple([span.text.strip() for span in row_soup.find('td', {'title': 'Guest team'}).find_all('span')])
        go = GameOverview(date=row_soup.find('td', {'title': 'Date'}).text.strip(),
                          p0=team0[0], p1=team1[0],
                          p2=team0[1], p3=team1[1],
                          result=self._read_score(row_soup.find('td', {'title': 'Result'})),
                          won_rounds=self._read_score(row_soup.find('td', {'title': 'Won rounds'})),
                          highcards=self._read_score(row_soup.find('td', {'title': 'Highcards'})),
                          bombs=self._read_score(row_soup.find('td', {'title': 'Bombs'})),
                          tichus=self._read_score(row_soup.find('td', {'title': 'Tichus'})),
                          grand_tichus=self._read_score(row_soup.find('td', {'title': 'Grand Tichus'})),
                          game_number=row_soup.find('a', {'class': 'gameLink'}).get('href').split('=')[-1])
        assert all(e is not None for e in go)
        return go

    # -------------------- games --------------------
    """
    def games_for_playername(self, name, save_periodicaly=100):

        Generator yielding Games (most recent first) where the player with the given name played in.

        :param name: player name
        :param save_periodicaly: integer. calls 'save_scraped_games_to_file' after scraping the given amount of games. set negative to disable

        gos_gen = self.game_overviews_for_playername(name)
        for gos in grouper(8, gos_gen):
            for game in self._scrape_batch_of_games(gos):
                if game is not None:
                    if 0 < save_periodicaly and len(self.scraped_games) % save_periodicaly == 0:
                        self.save_scraped_games_to_file(self.periodical_saves_file)
                    yield game
    """

    def _scrape_batch_of_games(self, game_overviews):
        """
        Sends the requests for the games asynchronously and then parses the games from the responses.
        Already scraped games are skipped.

        Note: tichumania has a limit of around 8 simultaneous requests from the same user. so len(game_overviews) should not be bigger than 8

        :param game_overviews:
        :return: Generator yielding the individual games for the game_overviews
        """

        gos = list()
        skipped = 0  # counts the number of games skipped because already scraped before.
        for go in game_overviews:
            if go.game_number not in self.scraped_gamenumbers:
                gos.append(go)
            else:
                skipped += 1
        # if skipped > 0:
            # print(f'skipped {skipped} games')

        urls = [self.game_url(go.game_number) for go in gos]
        if len(urls) == 0:
            return  # nothing to do here

        rqsts = (greq.get(url) for url in urls)
        responses = greq.map(rqsts)
        failed_resp = [r for r in responses if not r.ok]
        if len(failed_resp) > 0:
            print("Following requests failed: ", failed_resp)
        for game in (self.scrape_game_from_soup(BeautifulSoup(r.text, 'lxml'), go) for r, go in zip(responses, gos) if r is not None):
            if game is not None:
                yield game


    @exceptions_to_warning
    def scrape_game(self, game_overview):
        """
        Scrapes the game corresponding to the overview from the server.

        Note: Does NOT store the game anywhere.

        :param game_overview:
        :return: The Game corresponding to the given GameOverview.
        :returns None: if either some exception occured or the game already was scraped before.
        """

        if game_overview.game_number in self.scraped_gamenumbers:
            # print("already fetched ", game_overview.game_number, ':)')
            return None

        r = requests.get(url=self.game_url(game_overview.game_number))
        game_soup = BeautifulSoup(r.text, 'lxml')
        game = self.scrape_game_from_soup(game_soup, game_overview)

        return game

    @exceptions_to_warning
    def scrape_game_from_soup(self, game_soup, game_overview):
        """

        :param game_soup: The beautifulsoup object of the game page
        :param game_overview:
        :return: The Game corresponding to the given game_soup
        """
        print(f"parsing game {game_overview.game_number} ... ", end='')
        start_t = time.time()
        # print(game_soup.prettify())
        game_data = {
            'game_overview': game_overview,
            'p0': game_overview.p0,
            'p1': game_overview.p1,
            'p2': game_overview.p2,
            'p3': game_overview.p3,
            'result': game_soup.find('span', {'class': 'gameResult'}).text
        }

        rounds = [self._scrape_round(round_tag) for round_tag in game_soup.find_all('div', {'class': 'round'})]

        # create the Game
        game_data['rounds'] = rounds
        print('done. time:', time.time() - start_t)

        return Game(**game_data)

    def _scrape_round(self, round_soup):
        """

        :param round_soup: beautiful soup tag of the tichu round
        :return: The scraped Round described by the round_tag
        """
        round_data = {}

        # grand tichu hands
        gt_hands = self._scrape_grand_tichu_hands(round_soup)
        round_data['gt_hands'] = gt_hands

        # grand tichu
        round_data['grand_tichus'] = self._scrape_players_announced_grand_tichu(round_soup)

        # trading hands
        trading_hands = self._scrape_trading_hands(round_soup)
        round_data['trading_hands'] = {pl_name: t[0] for pl_name, t in trading_hands.items()}
        round_data['traded_cards'] = {pl_name: t[1:] for pl_name, t in trading_hands.items()}

        # complete hands
        complete_hands = self._scrape_complete_hands(round_soup)
        round_data['complete_hands'] = complete_hands

        # Moves
        moves = self._scrape_moves(round_soup)
        round_data['moves'] = moves
        round_data['tichus'] = tuple({m.player_name for m in moves if m.tichu})

        # round result
        initial_points_str = ''.join(rr.text for rr in round_soup.find_all('span', {'class': 'interimResult'}))
        result_str = ''.join(rr.text for rr in round_soup.find_all('span', {'class': 'roundResult'}))
        round_data['initial_points'] = tuple([int(n) for n in initial_points_str.strip().split(':')])
        round_data['result'] = tuple([int(n) for n in result_str.strip().split(':')])

        # Create Round
        return Round(**round_data)

    @staticmethod
    def _read_score(soup):
        # TODO make nicer
        return ':'.join(e.text.strip() for e in soup.find_all('span')[:2])

    @staticmethod
    def _scrape_grand_tichu_hands(round_soup):
        """

        :param round_soup:
        :return: a dictionary player_name -> tuple of cards
        """
        hands = {}
        gt_hands = round_soup.find('div', {'class': 'gtHands'})
        for hand in gt_hands.find_all('div', {'class': 'line'}):
            cards_tag = hand.find('div', {'class': 'cards'})
            player_name = hand.find('span', {'class': 'name'}).find('span').text  # TODO ev text from first span

            # cards
            cards = [c_span['class'][-1] for c_span in cards_tag.find_all('span')]
            hands[player_name] = cards

        return hands

    @staticmethod
    def _scrape_players_announced_grand_tichu(round_soup):
        """
        :param round_soup:
        :return: tuple containing the playernames of the players that announced grand tichu
        """
        gtichus = set()
        for gt_span in round_soup.find_all('span', {'class': 'gt'}):
            player_name = gt_span.parent.find('span', {'class': 'name'}).find(
                'span').text  # TODO ev text from first span
            gtichus.add(player_name)
        return tuple(gtichus)

    @staticmethod
    def _scrape_trading_hands(round_soup):
        """

        :param round_soup:
        :return: a dictionary player_name -> tuple(list of cards, traded card right, traded card teammate, traded card left)
        """
        trading_data = defaultdict(lambda: [None, None, None, None])
        trading_hands = round_soup.find('div', {'class': 'fullHands'})
        for hand in trading_hands.find_all('div', {'class': 'line'}):
            cards_tag = hand.find('div', {'class': 'cards'})
            player_name = hand.find('span', {'class': 'name'}).find('span').text  # TODO ev text from first span
            cards = [c_span['class'][-1] for c_span in cards_tag.find_all('span', {'class': 'card'})]
            trading_data[player_name][0] = tuple(cards)  # index 0 contains the handcards

            # traded cards
            traded_tags = hand.find_all('div', {'class': 'trading'})
            assert len(traded_tags) == 3, "traded_tags: " + traded_tags.prettify()
            for traded_t in traded_tags:
                trade_icon_tag = traded_t.find('span', {'class': 'tradeIcon'})
                icon_class = trade_icon_tag['class'][-1]
                player_offset = int(icon_class[-1])  # <span class="tradeIcon ti02"></span>
                traded_card = traded_t.find('span', {'class': 'card'})['class'][-1]
                trading_data[player_name][player_offset] = traded_card

                # print("icon_class", icon_class, "-> player_offset", player_offset, '=>', round_data['traded_cards'][player_name])

            # the list immutable
            trading_data[player_name] = tuple(trading_data[player_name])

        return trading_data

    @staticmethod
    def _scrape_complete_hands(round_soup):
        """

        :param round_soup:
        :return: a dictionary player_name -> tuple of cards
        """
        hands = dict()
        complete_hands = round_soup.find('div', {'class': 'completeHands'})
        for hand in complete_hands.find_all('div', {'class': 'line'}):
            cards_tag = hand.find('div', {'class': 'cards'})
            player_name = hand.find('span', {'class': 'name'}).find('span').text  # TODO ev text from first span
            cards = [c_span['class'][-1] for c_span in cards_tag.find_all('span', {'class': 'card'})]
            hands[player_name] = tuple(cards)

        return hands

    @staticmethod
    def _scrape_moves(round_soup):
        """

        :param round_soup:
        :return: tuple of moves
        """
        moves = list()
        for move_tag in round_soup.find_all('div', {'class': 'gameMove'}):
            move_data = {'cards_before': None, 'cards_played': None}
            player_name = move_tag.find('span', {'class': 'name'}).find('span').text  # TODO ev text from first span
            move_data['player_name'] = player_name

            move_data['tichu'] = len(move_tag.find_all('span', {'class': 'tichu'})) > 0

            cards_tag = move_tag.find('div', {'class': 'cards'})
            if cards_tag is not None:
                cards_before_move = [c_span['class'][-1] for c_span in
                                     cards_tag.find_all('span', {'class': 'card'})]
                move_data['cards_before'] = cards_before_move

                cards_played = [c_span['class'][-1] for c_span in cards_tag.find_all('span', {'class': 'played'})]
                move_data['cards_played'] = cards_played

            subline_tag = move_tag.find('div', {'class': 'subline'})
            move_data['is_pass'] = 'Pass' in subline_tag.text
            move_data['is_clear'] = 'final' in subline_tag['class']
            move_data['dragon_to'] = subline_tag.text.strip().split(' ')[-1] if move_data[
                                                                                    'is_clear'] and 'Dragon' in subline_tag.text else None
            moves.append(Move(**move_data))

        return tuple(moves)


if __name__ == '__main__':
    # n_games, output_file = int(sys.argv[1]), sys.argv[2]
    # run_scraper(n_games, output_file)
    scraper = TichumaniaScraper()
    nbr_scraped = scraper.scrape_games(max_nbr_games=2)
    print("nbr scraped: ", nbr_scraped)

