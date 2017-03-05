from game.game import TichuGameManager

if __name__ == "__main__":
    GM = TichuGameManager(target_points=1000)
    GM.start()