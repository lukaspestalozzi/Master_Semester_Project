import logging
import time

from game.montecarlo.montecarlo import DefaultMonteCarloTreeSearch, MctsState
from .tichu import logginginit
from .tichu.cards.card import Card
from .tichu.cards.deck import Deck
from .tichu.gameutils import Trick, RoundStartEvent, HandCardSnapshot


class MonteCarloGameSimulation(DefaultMonteCarloTreeSearch):

    def __init__(self, search_iterations=50):
        super().__init__(search_iterations=search_iterations)

    def search(self, start_state):
        super_res = super().search(start_state)
        return self.main_line(hand_cards=True)

    def is_end_search(self, iteration):
        if iteration % 50 == 0:
            print("at iteration ", iteration)
        return super().is_end_search(iteration)


def continue_montecarlo_game_simulation(mcgs, start_state):
    start_t = time.time()
    main_line = mcgs.search(start_state=start_state)

    print("Depth: ", len(main_line))
    print("Tree size: ", len(mcgs._nodes))

    for n, a, hc in main_line:
        logging.debug(f"{a}: \n{str(hc)}\n")

    time_taken = time.time() - start_t
    print("time: ", time_taken)


def create_start_state():
    """
    :return: A MctsState corresponding to a random initialisation of the game.
    """

    # distribute cards
    deck = Deck(full=True)
    piles = deck.split(nbr_piles=4, random_=True)
    assert len(piles) == 4
    handcards = HandCardSnapshot.from_cards_lists(*piles)

    # determine starting player
    mahjong_player_pos = None
    for pos, cards in enumerate(handcards):
        if Card.MAHJONG in cards:
            mahjong_player_pos = pos
            break

    return MctsState(current_pos=mahjong_player_pos,
                     hand_cards=handcards,
                     won_tricks=(Trick(), Trick(), Trick(), Trick()),
                     trick_on_table=Trick(),
                     wish=None,
                     ranking=(),
                     nbr_passed=0,
                     announced_tichu=frozenset(),
                     announced_grand_tichu=frozenset(),
                     action_leading_here=RoundStartEvent())

if __name__ == "__main__":
    logginginit.initialize_logger("./logs", console_log_level=logging.INFO, all_log="all.log")
    mcgs = MonteCarloGameSimulation()
    ss = create_start_state()
    continue_montecarlo_game_simulation(mcgs, ss)
