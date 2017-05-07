
import sys, os

this_folder = '/'.join(os.getcwd().split('/')[:])
parent_folder = '/'.join(os.getcwd().split('/')[:-1])

for p in [this_folder, parent_folder]:  # Adds the parent folder (ie. game) to the python path
    if p not in sys.path:
        sys.path.append(p)

from gamemanager import TichuGame
from gym_agents import BaseGymAgent


if __name__ == "__main__":
    tichumgame = TichuGame(BaseGymAgent(), BaseGymAgent(), BaseGymAgent(), BaseGymAgent())
    tichumgame.start_game()
