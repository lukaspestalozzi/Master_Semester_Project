from collections import OrderedDict


from tichu.agents.baseagent import DefaultAgent
from tichu.agents.partialagents import RandomSwappingCardsPartialAgent
from tichu.cards.card import Card
from tichu.cards.card import CardValue
from tichu.game.gameutils import CombinationAction, Trick, RoundState, PassAction, CombinationTichuAction


class HumanInputAgent(RandomSwappingCardsPartialAgent, DefaultAgent):

    def __init__(self):
        super().__init__()
        self._can_announce_tichu = True

    def start_game(self):
        print(f"You are Player Number {self._position}")
        print(f"Your Teammate is {(self._position + 2) % 4}")
        self._can_announce_tichu = True

    def give_dragon_away(self, trick, round_history):
        print("You won the Trick with the Dragon. Therefore you have to give it away.")
        print("Whom do you want to give it?")
        pl_pos = int(self.ask_user_to_choose_one_of([str((self.position + 1) % 4), str((self.position - 1) % 4)]))
        return pl_pos

    def wish(self, round_history):
        print(f"You played the MAHJONG ({str(Card.MAHJONG)}) -> You may wish a card Value:")
        answ = HumanInputAgent.ask_user_to_choose_one_of([cv.name for cv in CardValue if cv not in {CardValue.DOG, CardValue.DRAGON, CardValue.MAHJONG, CardValue.PHOENIX}])
        cv = CardValue.from_name(answ)
        return cv

    def play_combination(self, wish, round_history):
        print("Your turn to Play:")
        print(f"You have following cards: {sorted(self._hand_cards)}")
        print(f"On the Table is following Trick:")
        print(f"{round_history.tricks[-1]}")
        if wish:
            print(f"If you can you have to play a {wish} because this is the wish of the MAHJONG.")
        possible_actions = self._possible_actions(round_history=round_history, trick_on_table=round_history.tricks[-1], wish=wish)
        # create combinations
        possible_combs = []
        pass_ = False
        for ac in possible_actions:
            if isinstance(ac, PassAction):
                pass_ = "Pass"
            else:
                possible_combs.append(ac.combination)

        # sort combs
        possible_combs = sorted(possible_combs, key=lambda c: (len(c), c.height))

        # prepend PASS if allowed
        if pass_:
            possible_combs = [pass_] + possible_combs
        comb = self.ask_user_to_choose_with_numbers(possible_combs)

        # did user choose to pass ?
        if comb == pass_:
            return PassAction(self._position)

        return self._play_tichu_if_wants_and_can_to(CombinationAction(self._position, comb))

    def play_bomb(self, round_history):
        bombs = list(self._hand_cards.all_bombs())
        if len(bombs) > 0:
            print(f"You have a Bomb, do you want to play it? (hadcards: {self.hand_cards})")
            print(f"On the Table is following Trick:")
            print(f"{round_history.tricks[-1]}")
            dont_play = "Don't play a Bomb"
            bomb_comb = self.ask_user_to_choose_with_numbers([dont_play] + list(bombs))
            if bomb_comb == dont_play:
                return None
            else:
                return bomb_comb
        return None

    def play_first(self, round_history, wish):
        print("Your turn to Play first. There is no Trick on the Table.")
        print(f"You have following cards: {sorted(self._hand_cards)}")
        if wish:
            print(f"If you can you have to play a {wish} because this is the wish of the MAHJONG.")
        possible_combs = [a.combination for a in self._possible_actions(round_history=round_history, trick_on_table=Trick([]), wish=wish)]
        # sort combs
        possible_combs = sorted(possible_combs, key=lambda c: (len(c), c.height))

        comb = self.ask_user_to_choose_with_numbers(sorted(possible_combs, key=lambda comb: (len(comb), comb.height)))

        return self._play_tichu_if_wants_and_can_to(CombinationAction(self._position, comb))

    def swap_cards(self):
        """
        print("Time to swap cards:")
        print("Cards to Swap to your Teammate:")
        query_actions = sorted(self._hand_cards)
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
        """
        return super().swap_cards()

    def swap_cards_received(self, swapped_cards_actions):
        print("You received following Cards during swapping:")
        for sw in swapped_cards_actions:
            relative_pos = 'Teammate'
            if sw.from_ == (self.position + 1) % 4:
                relative_pos = 'Enemy Right'
            elif sw.from_ == (self.position - 1) % 4:
                relative_pos = 'Enemy Left'
            print(f"From {sw.from_}({relative_pos}) you got {sw.card}")
        self.ask_user_for_keypress()

    def notify_about_announced_tichus(self, tichu, grand_tichu):
        if len(grand_tichu) > 0:
            print(f"Following Players announced GRAND Tichu: {', '.join(str(t) for t in grand_tichu)}")
        if len(tichu) > 0:
            print(f"Following Players announced Tichu: {', '.join(str(t) for t in tichu)}")
        if len(grand_tichu) > 0 or len(tichu) > 0:
            self.ask_user_for_keypress()

    def announce_tichu(self, announced_tichu, announced_grand_tichu):
        return self._ask_announce_tichu(announced_tichu, announced_grand_tichu)

    def announce_grand_tichu(self, announced_grand_tichu):
        return self._ask_announce_tichu(announced_tichu={}, announced_grand_tichu=announced_grand_tichu, grand=True)

    def _play_tichu_if_wants_and_can_to(self, action):
        if self._can_announce_tichu:
            self._can_announce_tichu = False
            print("This is your first play.")
            tichu = self.ask_user_yes_no_question("Do you want to announce a Tichu?")
            if tichu:
                print("You just announced Tichu!")
                return CombinationTichuAction(action.player_pos, action.combination)  # return tichu action
        return action

    def _ask_announce_tichu(self, announced_tichu, announced_grand_tichu, grand=False):
        print(f"Your handcards are: {self.hand_cards}")
        self.notify_about_announced_tichus(tichu=announced_tichu, grand_tichu=announced_grand_tichu)
        answ = self.ask_user_yes_no_question("Do you want to announce a {}Tichu?".format("grand-" if grand else ""))
        assert answ is True or answ is False
        if answ:
            self._can_announce_tichu = False
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

    @staticmethod
    def ask_user_to_choose_one_of(possible_answers):
        options_dict = OrderedDict([(k, k) for k in possible_answers])
        answer, _ = HumanInputAgent.ask_user_to_choose_from_options(options_dict)
        return answer

    @staticmethod
    def ask_user_to_choose_with_numbers(option):
        """
        Asks the user to choose one of the options, but makes it easier by numbering the options and the user only has to enter the number.
        :param option:
        :return: The choosen option
        """
        options_dict = OrderedDict(sorted((nr, o) for nr, o in enumerate(option)))
        inpt, comb = HumanInputAgent.ask_user_to_choose_from_options(options_dict)
        return comb

    @staticmethod
    def ask_user_yes_no_question(question):
        """
        Asks the user to answer the question.
        :param question: string
        :return: True if the answer is 'Yes', False if the answer is 'No'.
        """
        inpt, val = HumanInputAgent.ask_user_to_choose_from_options({'y': 'Yes', 'n': 'No'}, text=question + " \n{}\n")
        return val == 'Yes'

    @staticmethod
    def ask_user_to_choose_from_options(answer_option_dict,
                                        text='Your options: \n{}\n',
                                        no_option_text="You have no options, press Enter to continue.\n",
                                        one_option_text="You have only one option ({}), press Enter to choose it.\n"):
        """
        1 Displays the mapping from keys to values in option_answer_dict. (If key and value are the same, only key is displayed)

        2 and asks the user to choose one of the key values (waiting for user input is blocking).

        3 Repeats the previous steps until the input matches with one of the keys.

        4 Then returns the chosen key and corresponding value.

        :param answer_option_dict: Dictionary of answer -> option mappings. where answer is the text the user has to input to choose the option.
        :param text: Text displayed when there are 2 or more options. It must contain one {} where the possible options should be displayed.
        :param no_option_text: Text displayed when there is no option to choose from.
        :param one_option_text: Text displayed when there is exactly 1 option to choose from. It must contain one {} where the possible option is displayed.
        :return: The key, value pair (as tuple) chosen by the user. If the dict is empty, returns (None, None).
        """

        if len(answer_option_dict) == 0:
            HumanInputAgent.ask_user_for_input(no_option_text)
            return None, None
        elif len(answer_option_dict) == 1:
            HumanInputAgent.ask_user_for_input(one_option_text.format(next(iter(answer_option_dict.values()))))
            return next(iter(answer_option_dict.items()))
        else:
            answer_option_dict = OrderedDict({str(k): o for k, o in answer_option_dict.items()})
            opt_string = "\n".join("'"+str(answ)+"'"+(" for "+str(o) if answ != o else "") for answ, o in answer_option_dict.items())
            possible_answers = {str(k) for k in answer_option_dict}
            while True:
                inpt = HumanInputAgent.ask_user_for_input(text.format(opt_string))
                if inpt in possible_answers:
                    print("You chose: ", inpt, '->', answer_option_dict[inpt])
                    return inpt, answer_option_dict[inpt]
                else:
                    print("Wrong input, please try again.")

    @staticmethod
    def ask_user_for_keypress():
        """
        Asks the user to press any key.
        :return: The input given by the user
        """
        return HumanInputAgent.ask_user_for_input("Press Enter to continue.")

    @staticmethod
    def ask_user_for_input(text):
        """
        Displays the text and waits for user input
        :param text:
        :return: The user input
        """
        return input(str(text))
