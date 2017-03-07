from game.game import TichuGame

if __name__ == "__main__":
    GM = TichuGame(target_points=10000)
    res = GM.start()