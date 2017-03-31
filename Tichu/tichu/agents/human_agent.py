

import random

import logging

import time

from tichu.agents.baseagent import BaseAgent
from tichu.cards.card import Card
from tichu.cards.card import CardValue
from tichu.game.gameutils import PassAction, CombinationAction, SwapCardAction, Trick, RoundState


class HumanInputAgent(BaseAgent):

    def __init__(self):
        super().__init__()
        self._mcts = MonteCarloTreeSearch()

    def give_dragon_away(self, hand_cards, trick, round_history):
        print("You won the Trick with the Dragon. Therefore you have to give it away.")
        print("Whom do you want to give it?")
        pl_pos = int(self._ask_for_input([(self.position + 1) % 4, (self.position + 1) % 4]))
        return pl_pos

    def wish(self, hand_cards, round_history):
        print(f"You played the MAHJONG ({str(Card.MAHJONG)}) -> You may wish a card Value:")
        answ = self._ask_for_input([cv.name for cv in CardValue if cv not in {CardValue.DOG, CardValue.DRAGON, CardValue.MAHJONG, CardValue.PHOENIX}])
        cv = CardValue.from_name(answ)
        return cv

    def play_combination(self, wish, hand_cards, round_history):
        print("Your turn to Play:")
        print(f"You have following cards: {hand_cards.pretty_string()}")
        print(f"On the Table is following Trick:")
        print(f"{round_history.tricks[-1]}")
        if wish:
            print(f"If you can you have to play a {wish} because this is the wish of the MAHJONG.")
        possible_actions = self._possible_actions(round_history=round_history, hand_cards=hand_cards, trick_on_table=round_history.tricks[-1], wish=wish)
        query_actions = {str(k): act for k, act in enumerate(possible_actions)}
        answ = self._ask_for_input(query_actions)
        action = query_actions[answ]
        return action

    def play_bomb(self, hand_cards, round_history):
        bombs = hand_cards.bombs()
        if len(bombs) > 0:
            print("You have a Bomb, do you want to play it?")
            print(f"On the Table is following Trick:")
            print(f"{round_history.tricks[-1]}")
            query_ = {str(k): b for k, b in enumerate(["Don't play a Bomb"] + list(bombs))}
            assert query_[0] == "Don't play a Bomb"
            answ = self._ask_for_input(query_)
            if answ == 0:
                return None
            else:
                bomb_comb = query_[answ]
                action = CombinationAction(self._position, combination=bomb_comb)
                return action
        return None

    def play_first(self, hand_cards, round_history, wish):
        print("Your turn to Play first. There is no Trick on the Table.")
        print(f"You have following cards: {hand_cards.pretty_string()}")
        if wish:
            print(f"If you can you have to play a {wish} because this is the wish of the MAHJONG.")
        possible_actions = self._possible_actions(round_history=round_history, hand_cards=hand_cards, trick_on_table=Trick([]), wish=wish)
        query_actions = {str(k): act for k, act in enumerate(possible_actions)}
        answ = self._ask_for_input(query_actions)
        action = query_actions[answ]
        return action

    def swap_cards(self, hand_cards):
        print("Time to swap cards:")
        print("Cards to Swap to your Teammate:")
        query_actions = {str(k): c for k, c in enumerate(hand_cards)}
        answ_teammate = self._ask_for_input(query_actions)
        card_teammate = query_actions.pop(answ_teammate)

        print("Cards to Swap to the player on your RIGHT:")
        answ_right = self._ask_for_input(query_actions)
        card_right = query_actions.pop(answ_right)

        print("Cards to Swap to the player on your LEFT:")
        answ_left = self._ask_for_input(query_actions)
        card_left = query_actions.pop(answ_left)


        scards = [
            SwapCardAction(player_from=self._position, card=card_right, player_to=(self.position + 1) % 4),
            SwapCardAction(player_from=self._position, card=card_teammate, player_to=(self.position + 2) % 4),
            SwapCardAction(player_from=self._position, card=card_left, player_to=(self.position + 3) % 4)
        ]
        return scards

    def notify_about_announced_tichus(self, tichu, grand_tichu):
        if len(grand_tichu) > 0:
            print(f"Following Players announced GRAND Tichu: {grand_tichu}")
        if len(tichu) > 0:
            print(f"Following Players announced Tichu: {tichu}")

    def announce_tichu(self, announced_tichu, announced_grand_tichu, round_history):
        return self._ask_announce_tichu(announced_tichu, announced_grand_tichu)

    def announce_grand_tichu(self, announced_grand_tichu):
        return self._ask_announce_tichu(announced_tichu={}, announced_grand_tichu=announced_grand_tichu, grand=True)

    def _ask_announce_tichu(self, announced_tichu, announced_grand_tichu, grand=False):
        print("Do you want to announce a {}Tichu?".format("grand-" if grand else ""))
        self.notify_about_announced_tichus(tichu=announced_tichu, grand_tichu=announced_grand_tichu)
        answ = self._ask_for_input(['no', 'n', 'yes', 'y'])
        return answ == 'yes' or answ == 'y'

    def _possible_actions(self, round_history, hand_cards, trick_on_table, wish):
        roundstate = RoundState(announced_grand_tichu=round_history.announced_grand_tichu,
                                announced_tichu=round_history.announced_tichu,
                                current_pos=self.position,
                                hand_cards=hand_cards,
                                nbr_passed=round_history.nbr_passed(),
                                ranking=round_history.ranking,
                                trick_on_table=trick_on_table,
                                wish=wish,
                                won_tricks=round_history.won_tricks)
        possible_actions = roundstate.possible_actions()
        return possible_actions

    def _ask_for_input(self, possible_answers):
        possible_answers = [str(s) for s in possible_answers]
        while True:
            answer = input(f"Possible choices: {possible_answers}")
            if answer in possible_answers:
                return answer
            else:
                print("Wrong input, please try again.")