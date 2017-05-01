import logging
import datetime
from time import time

import sys, os

for p in ['/'.join(os.getcwd().split('/')[:-1])]:  # Adds the parent folder (ie. game) to the python path
    if p not in sys.path:
        sys.path.append(p)
# print('PATH:', sys.path)

from game.tichu import (HumanInputAgent, SimpleMonteCarloPerfectInformationAgent, RandomAgent,
                        ISMctsUCB1Agent, ISMctsEpicAgent, ISMctsLGRAgent, ISMctsEpicLGRAgent)
from game.tichu import TichuGame
from game.tichu import Team
from game.tichu import TichuPlayer
from game.tichu import logginginit

if __name__ == "__main__":
    nbr_games = 1
    if len(sys.argv) > 1:
        nbr_games = int(sys.argv[1])
    for _ in range(nbr_games):
        stime = time()
        start_ftime = datetime.datetime.now().strftime("%Y-%m-%d_%H:%M")
        logginginit.initialize_logger("./logs/"+start_ftime, console_log_level=logging.INFO, all_log="all.log")
        """
        players = [
            TichuPlayer(name="player0", agent=ISMctsUCB1Agent(iterations=100)),
            TichuPlayer(name="player1", agent=ISMctsUCB1Agent(iterations=100)),
            TichuPlayer(name="player2", agent=ISMctsUCB1Agent(iterations=100)),
            TichuPlayer(name="player3", agent=ISMctsUCB1Agent(iterations=100)),
        ]
        """
        players = [
            TichuPlayer(name="player0", agent=ISMctsUCB1Agent(iterations=30, cheat=False)),
            TichuPlayer(name="player1", agent=ISMctsEpicLGRAgent(iterations=30, cheat=False)),
            TichuPlayer(name="player2", agent=ISMctsUCB1Agent(iterations=30, cheat=False)),
            TichuPlayer(name="player3", agent=ISMctsEpicLGRAgent(iterations=30, cheat=False)),
        ]

        players_vs_string = "0: {0}\n2: {2} \nVS.\n1: {1}\n3: {3}\n\n".format(*[p.agent_info() for p in players])
        logging.info("Playing: \n"+players_vs_string)

        team1 = Team(player1=players[0], player2=players[2])
        team2 = Team(player1=players[1], player2=players[3])
        GM = TichuGame(team1, team2, target_points=1000)
        res = GM.start_game()

        res_string = res.pretty_string()
        out_string = "\n\n################################## GAME ##################################\n"
        out_string += "start-time: {}\n".format(start_ftime) + "\n"
        out_string += "end-time: {}\n".format(datetime.datetime.now().strftime("%Y-%m-%d_%H:%M")) + "\n"
        time_in_seconds = time() - stime
        out_string += "duration: {} seconds ({} minutes and {} seconds)\n".format(time_in_seconds, time_in_seconds // 60, time_in_seconds % 60) + "\n"
        out_string += players_vs_string
        out_string += "Outcome: "+str(res.points)+"\n"

        info_string = out_string  # copy before adding game history

        out_string += res_string + "\n"

        logging.info(out_string)
        logging.info(info_string)

        with open("./logs/game_res.log", "a") as f:
            f.write(out_string)

