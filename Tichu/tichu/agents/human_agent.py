from pprint import pformat

from tichu.agents.baseagent import BaseAgent
from tichu.cards.card import Card
from tichu.cards.card import CardValue
from tichu.game.gameutils import CombinationAction, SwapCardAction, Trick, RoundState


class HumanInputAgent(BaseAgent):

    def __init__(self):
        super().__init__()

    def start_game(self):
        print(f"You are Player Number {self._position}")
        print(f"Your Teammate is {(self._position + 2) % 4}")

    def give_dragon_away(self, hand_cards, trick, round_history):
        print("You won the Trick with the Dragon. Therefore you have to give it away.")
        print("Whom do you want to give it?")
        pl_pos = int(self._ask_for_input_raw([str((self.position + 1) % 4), str((self.position - 1) % 4)]))
        return pl_pos

    def wish(self, hand_cards, round_history):
        print(f"You played the MAHJONG ({str(Card.MAHJONG)}) -> You may wish a card Value:")
        answ = self._ask_for_input([cv.name for cv in CardValue if cv not in {CardValue.DOG, CardValue.DRAGON, CardValue.MAHJONG, CardValue.PHOENIX}])
        cv = CardValue.from_name(answ)
        return cv

    def play_combination(self, wish, hand_cards, round_history):
        print("Your turn to Play:")
        print(f"You have following cards: {sorted(hand_cards)}")
        print(f"On the Table is following Trick:")
        print(f"{round_history.tricks[-1]}")
        if wish:
            print(f"If you can you have to play a {wish} because this is the wish of the MAHJONG.")
        possible_actions = self._possible_actions(round_history=round_history, trick_on_table=round_history.tricks[-1], wish=wish)
        action = self._ask_for_input(possible_actions)
        return action

    def play_bomb(self, hand_cards, round_history):
        bombs = list(hand_cards.all_bombs())
        if len(bombs) > 0:
            print("You have a Bomb, do you want to play it?")
            print(f"On the Table is following Trick:")
            print(f"{round_history.tricks[-1]}")
            query_ = ["Don't play a Bomb"] + list(bombs)
            bomb_comb = self._ask_for_input(query_)
            if bomb_comb == "Don't play a Bomb":
                return None
            else:
                action = CombinationAction(self._position, combination=bomb_comb)
                return action
        return None

    def play_first(self, hand_cards, round_history, wish):
        print("Your turn to Play first. There is no Trick on the Table.")
        print(f"You have following cards: {sorted(hand_cards)}")
        if wish:
            print(f"If you can you have to play a {wish} because this is the wish of the MAHJONG.")
        possible_actions = self._possible_actions(round_history=round_history, trick_on_table=Trick([]), wish=wish)
        action = self._ask_for_input(possible_actions)
        return action

    def swap_cards(self, hand_cards):
        print("Time to swap cards:")
        print("Cards to Swap to your Teammate:")
        query_actions = sorted(hand_cards)
        card_teammate = self._ask_for_input(query_actions)
        query_actions.remove(card_teammate)

        print("Cards to Swap to the player on your RIGHT:")
        card_right = self._ask_for_input(query_actions)
        query_actions.remove(card_right)

        print("Cards to Swap to the player on your LEFT:")
        card_left = self._ask_for_input(query_actions)
        query_actions.remove(card_left)


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
        print("Your handcards are: ... TODO implement!!")  # TODO
        self.notify_about_announced_tichus(tichu=announced_tichu, grand_tichu=announced_grand_tichu)
        answ = self._ask_for_yes_no("Do you want to announce a {}Tichu?".format("grand-" if grand else ""))
        assert answ is True or answ is False
        return answ

    def _possible_actions(self, round_history, trick_on_table, wish):
        roundstate = RoundState(announced_grand_tichu=round_history.announced_grand_tichus,
                                announced_tichu=round_history.announced_tichus,
                                current_pos=self.position,
                                hand_cards=round_history.last_handcards,
                                nbr_passed=round_history.nbr_passed(),
                                ranking=round_history.ranking,
                                trick_on_table=trick_on_table,
                                wish=wish,
                                won_tricks=round_history.won_tricks)
        possible_actions = roundstate.possible_actions()
        return possible_actions

    def _ask_for_input(self, actions):
        options = [(str(nr), action) for nr, action in enumerate(actions)]
        possible_answers = [s_nr for s_nr, _ in options]
        d = {k: v for k, v in options}
        options_str = '\n'.join(str(op)+' for: '+str(act) for op, act in options)

        while True:
            answer = input(f"Possible options: \n{options_str}\n")
            if answer in possible_answers:
                print("You chose: ", answer, '->', d[answer])
                return d[answer]
            else:
                print("Wrong input, please try again.")

    def _ask_for_input_raw(self, possible_answers):
        while True:
            answer = input(f"Possible options: \n{pformat(possible_answers)}\n")
            if answer in possible_answers:
                print("You chose: ", answer)
                return answer
            else:
                print("Wrong input, please try again.")

    def _ask_for_yes_no(self, question):
        possible_yes = ['y', 'yes']
        possible_no = ['n', 'no']
        while True:
            answer = input(f"{question} {possible_yes+possible_no}")
            if answer in possible_yes:
                return True
            elif answer in possible_no:
                return False
            else:
                print("Wrong input, please try again.")
