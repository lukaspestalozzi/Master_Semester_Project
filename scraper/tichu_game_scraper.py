
import pickle
import requests
import sys
from bs4 import BeautifulSoup
import warnings

from collections import namedtuple

Player = namedtuple('Player', ['rank', 'name', 'nbr_games', 'nbr_won_games', 'elo'])

GameOverview = namedtuple('GameOverview', ['date', 'p0', 'p1', 'p2', 'p3', 'result', 'won_rounds', 'highcards',
                                           'bombs', 'tichus', 'grand_tichus', 'game_url'])

Game = namedtuple('Game', ['game_overview', 'p0', 'p1', 'p2', 'p3', 'result', 'rounds'])

Round = namedtuple('Round', ['result', 'gt_hands', 'grand_tichus', 'trading_hands', 'traded_cards', 'complete_hands', 'moves'])

Move = namedtuple('Move', ['cards_before', 'player_name', 'cards_played', 'is_pass', 'is_clear', 'tichu', 'dragon_to'])


class TichumaniaScraper(object):

    def __init__(self, base_url='http://log.tichumania.de/view/pages/', elolist_page='Elolist.php', games_page='Games.php'):
        self.base_url = base_url
        self.elolist_page = elolist_page
        self.games_page = games_page

    @property
    def elolist_url(self):
        return f'{self.base_url}{self.elolist_page}'

    @property
    def games_url(self):
        return f'{self.base_url}{self.games_page}'

    def _games_for_player_url(self, player_name, page_from_=0, page_to=100):
        return f'{self.base_url}games/content.php?player={player_name}&start={page_from_}&count={page_to}'

    @staticmethod
    def _read_score(tag):
        # TODO make nicer
        return ':'.join(e.text.strip() for e in tag.find_all('span')[:2])

    def find_best_players(self, n):
        """
        :param n: integer, if <= 0, then retrieves all players.
        :return: The n best players (ranked by elo score)
        """
        # TODO cache
        r = requests.get(url=self.elolist_url)
        soup = BeautifulSoup(r.text, 'lxml')

        players = []
        for row in soup.find_all('tr'):
            if 0 < n <= len(players):
                break

            col = row.find_all('td')
            if len(col):
                t = [e.text for e in col]
                # print("texts: ", t)
                p = Player(rank=int(t[0]), name=t[1], nbr_games=int(t[2]), nbr_won_games=t[3], elo=int(t[4]))
                players.append(p)

        return players

    def game_overviews_for_playername(self, name, n):
        """
        :param name: playername
        :param n:
        :return: n GameOverviews where the player with the given name played
        """
        def soup_for_pages(from_, to):
            r = requests.get(url=self._games_for_player_url(name, from_, to))
            soup = BeautifulSoup(r.text, 'lxml')
            return soup

        soup = soup_for_pages(0, n+1)
        games = []
        for row in soup.find_all('tr'):
            if len(games) >= n:
                break
            col = row.find_all('td')
            if len(col):
                team0 = tuple([span.text.strip() for span in row.find('span', {'title': 'Home Team'}).find_all('span')])
                team1 = tuple([span.text.strip() for span in row.find('span', {'title': 'Guest Team'}).find_all('span')])
                go = GameOverview(date=row.find('span', {'title': 'Date'}).text.strip(),
                                  p0=team0[0].text.strip(), p1=team1[0].text.strip(),
                                  p2=team0[1].text.strip(), p3=team1[0].text.strip(),
                                  result=self._read_score(col[3]), won_rounds=self._read_score(col[4]),
                                  highcards=self._read_score(col[5]),
                                  bombs=self._read_score(col[6]), tichus=self._read_score(col[7]),
                                  grand_tichus=self._read_score(col[8]),
                                  game_url=col[10].find('a').get('href'))
                games.append(go)
        return games


    def games_for_playername(self, name, n):
        """

        :param name:
        :param n:
        :return: n games for the playername
        """
        url = "http://log.tichumania.de/view/pages/{}"
        game_os = game_overviews_for_playername(name, n)
        games = []
        for go in game_os:
            game_url = url.format(go.game_url)
            r = requests.get(url=game_url)
            soup = BeautifulSoup(r.text, 'lxml')

            game_data = {
                'game_overview': go,
                'p0': go.p0,
                'p1': go.p1,
                'p2': go.p2,
                'p3': go.p3,
                'result': soup.find('span', {'class': 'gameResult'}).text
            }

            rounds = []
            for round_tag in soup.find_all('div', {'class': 'round'}):
                round_data = {
                    'grand_tichus': list(),
                    'gt_hands': dict(),  # dict playername -> cards list
                    'trading_hands': dict(),
                    'traded_cards': dict(),  # dict playername -> list of traded cards
                    'complete_hands': dict()
                }

                # grand tichu hands
                gt_hands = round_tag.find('div', {'class': 'gtHands'})
                for hand in gt_hands.find_all('div', {'class': 'line'}):
                    cards_tag = hand.find('div', {'class': 'cards'})
                    player_name = hand.find('span', {'class': 'name'}).find('span').text  # TODO ev text from first span

                    # cards
                    cards = [c_span['class'][-1] for c_span in cards_tag.find_all('span')]
                    round_data['gt_hands'][player_name] = cards

                    # announced grand tichu?
                    if len(hand.find_all('span', {'class': 'gt'})) > 0:
                        round_data['grand_tichus'].append(player_name)

                # trading hands
                trading_hands = round_tag.find('div', {'class': 'fullHands'})
                for hand in trading_hands.find_all('div', {'class': 'line'}):
                    cards_tag = hand.find('div', {'class': 'cards'})
                    player_name = hand.find('span', {'class': 'name'}).find('span').text  # TODO ev text from first span
                    cards = [c_span['class'][-1] for c_span in cards_tag.find_all('span', {'class': 'card'})]
                    round_data['trading_hands'][player_name] = cards
                    # traded cards
                    traded_tags = hand.find_all('div', {'class': 'trading'})
                    assert len(traded_tags) == 3
                    round_data['traded_cards'][player_name] = [None, None, None, None]
                    for traded_t in traded_tags:
                        # player_pos + player_offset % 4 gives the receiving player pos
                        trade_icon_tag = traded_t.find('span', {'class': 'tradeIcon'})
                        icon_class = trade_icon_tag['class'][-1]
                        player_offset = int(icon_class[-1])  # <span class="tradeIcon ti02"></span>
                        traded_card = traded_t.find('span', {'class': 'card'})['class'][-1]
                        round_data['traded_cards'][player_name][player_offset] = traded_card

                        # print("icon_class", icon_class, "-> player_offset", player_offset, '=>', round_data['traded_cards'][player_name])

                    # make round_data['traded_cards'][player_name] immutable and remove the index 0
                    round_data['traded_cards'][player_name] = tuple(round_data['traded_cards'][player_name][1:])

                # complete hands
                complete_hands = round_tag.find('div', {'class': 'completeHands'})
                for hand in complete_hands.find_all('div', {'class': 'line'}):
                    cards_tag = hand.find('div', {'class': 'cards'})
                    player_name = hand.find('span', {'class': 'name'}).find('span').text  # TODO ev text from first span
                    cards = [c_span['class'][-1] for c_span in cards_tag.find_all('span', {'class': 'card'})]
                    round_data[f'complete_hands'][player_name] = cards

                # Moves
                round_data['moves'] = list()
                for move_tag in round_tag.find_all('div', {'class': 'gameMove'}):
                    move_data = {'cards_before': None, 'cards_played': None}
                    player_name = move_tag.find('span', {'class': 'name'}).find('span').text  # TODO ev text from first span
                    move_data['player_name'] = player_name

                    move_data['tichu'] = len(move_tag.find_all('span', {'class': 'tichu'})) > 0

                    cards_tag = move_tag.find('div', {'class': 'cards'})
                    if cards_tag is not None:
                        cards_before_move = [c_span['class'][-1] for c_span in cards_tag.find_all('span', {'class': 'card'})]
                        move_data['cards_before'] = cards_before_move

                        cards_played = [c_span['class'][-1] for c_span in cards_tag.find_all('span', {'class': 'played'})]
                        move_data['cards_played'] = cards_played

                    subline_tag = move_tag.find('div', {'class': 'subline'})
                    move_data['is_pass'] = 'Pass' in subline_tag.text
                    move_data['is_clear'] = 'final' in subline_tag['class']
                    move_data['dragon_to'] = subline_tag.text.strip().split(' ')[-1] if move_data['is_clear'] and 'Dragon' in subline_tag.text else None

                    round_data['moves'].append(Move(**move_data))


                # round result
                round_data['result'] = ''.join(rr.text for rr in round_tag.find_all('div', {'class': 'roundResult'}))

                # Create Round
                rounds.append(Round(**round_data))
            # end-for-round

            # create Game
            game_data['rounds'] = rounds
            games.append(Game(**game_data))
        # end-for-games

        return games


    def _scrape_game(self, game_url):
        pass


    def _scrape_round(self, round_tag):
        pass


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


if __name__ == '__main__':
    # n_games, output_file = int(sys.argv[1]), sys.argv[2]
    # run_scraper(n_games, output_file)
    players = find_best_players(2)
    print('\n'.join(str(p) for p in players))
    for p in players:
        try:
            games = games_for_playername(p.name, 200)
            with open(f'games/games_{p.name}.pkl', 'wb') as f:
                pickle.dump(games, f)
                print("done, player", p.name)
        except Exception as e:
            warnings.warn(e)
