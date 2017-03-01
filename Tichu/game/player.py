import abc

class Player(metaclass=abc.ABCMeta):

    def __init__(name, playerID):
        self.name = name
        self.id = playerID
        self.hand_cards = Cards([])
        self.tricks = [] # list of Cards instances

    # TODO add hash and equals (hash is UUID)

    def has_finished(self):
        return len(self.hand_cards) == 0

    @abc.abstractmethod
    def receive_first_8_cards(self, cards):
        """
        Called by the game manager to hand over the first 8 cards.
        """
        # TODO check argument

    @abc.abstractmethod
    def receive_last_6_cards(self, cards):
        """
        Called by the game manager to hand over the last 6 cards.
        """
        # TODO check argument

    @abc.abstractmethod
    def announce_grand_tichu_or_not(self, announced):
        """
        anounced: a list of integers (in range(0, 4)), denoting playerIDs that already have anounced a Tichu.
        Returns True if this player anounces a grand tichu, False otherwise.
        """

    @abc.abstractmethod
    def players_announced_grand_tichu(self, announced):
        """
        Called by the the game manager to notify the player about announced grand tichus.
        anounced: a list of integers (in range(0, 4)), denoting playerIDs that have anounced a Tichu.
        Returns None
        """

    @abc.abstractmethod
    def play_first(self):
        """
        Called by the the game manager to request a move.
        Returns the combination the player wants to play. The combination must be a valid play according to the Tichu rules, in particular, the combination must not be empy and the player must have all cards of the combination in it's hand cards.
        """

    @abc.abstractmethod
    def play_combination(self, on_trick):
        """
        Called by the the game manager to request a move.
        on_trick: the highest trick on the table
        Returns the combination the player wants to play. The combination must be a valid play according to the Tichu rules, in particular it must be of the same type as on_trick (or a bomb) and higher than on_trick
        Note that the combination may be empty (PASS)
        """

    @abc.abstractmethod
    def play_bomb_or_not(self, on_trick):
        """
        Called by the the game manager allow the player to play a bomb.
        on_trick (instance of Trick): The tricks currently on the table
        Returns the bomb (as Combination) if the player wants to play a bomb or False otherwise
        """

    @abc.abstractmethod
    def swap_cards(self):
        """
        Returns a dict containing the keys -1, 1, 'teammate'. And as values the card to give to that player.
        """

    @abc.abstractmethod
    def receive_swapped_cards(self, swapped_cards):
        """
        swapped_cards: a dict containing the keys -1, 1, 'teammate'. And as values the card from the players. (-1 and 1 are the player with id 1 lower resp. 1 higher % 4 of this players id )
        """




class DummyPlayer(Player):
    pass
