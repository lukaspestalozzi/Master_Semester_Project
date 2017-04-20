import logging
import datetime
from game.tichu import HumanInputAgent, SimpleMonteCarloPerfectInformationAgent, RandomAgent
from game.tichu import TichuGame
from game.tichu import Team
from game.tichu import TichuPlayer
from game.tichu import logginginit

if __name__ == "__main__":
    logginginit.initialize_logger("./logs", console_log_level=logging.INFO, all_log="all.log")
    """
    players = [
        TichuPlayer(name="player0", agent=HumanInputAgent(), perfect_information_mode=True),
        TichuPlayer(name="player1", agent=SimpleMonteCarloPerfectInformationAgent(), perfect_information_mode=True),
        TichuPlayer(name="player2", agent=SimpleMonteCarloPerfectInformationAgent(), perfect_information_mode=True),
        TichuPlayer(name="player3", agent=SimpleMonteCarloPerfectInformationAgent(), perfect_information_mode=True),
    ]
    """
    players = [
        TichuPlayer(name="player0", agent=HumanInputAgent(), perfect_information_mode=True),
        TichuPlayer(name="player1", agent=RandomAgent(), perfect_information_mode=True),
        TichuPlayer(name="player2", agent=RandomAgent(), perfect_information_mode=True),
        TichuPlayer(name="player3", agent=RandomAgent(), perfect_information_mode=True),
    ]

    team1 = Team(player1=players[0], player2=players[2])
    team2 = Team(player1=players[1], player2=players[3])
    GM = TichuGame(team1, team2, target_points=1)
    res = GM.start_game()

    res_string = res.pretty_string()
    print(res_string)

    with open("./logs/game_res.log", "a") as f:
        f.write("\n\n################################## NEW GAME ##################################\n")
        now = datetime.datetime.now()
        f.write("time: {}\n".format(now.strftime("%Y-%m-%d %H:%M")))
        f.write(res_string)

