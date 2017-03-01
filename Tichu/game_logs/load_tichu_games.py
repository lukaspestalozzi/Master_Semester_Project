import sys
from load_data import load_clean_vectorize

def load_games():
    unique_ranks = ['Dr', 'Ph', 'A', 'K', 'Q', 'J', 'T', '9', '8', '7', '6', '5', '4', '3', '2', 'Mahj', 'Dog']

    print('Loading data...')
    data = load_clean_vectorize('data/scrapper_out.csv', 'data/tichucards.csv', unique_ranks, 'final_cards')
    return data
