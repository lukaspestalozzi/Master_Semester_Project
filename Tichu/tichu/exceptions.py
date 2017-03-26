

class TichuError(Exception):
    """
    Parent class for all Error of the Tichu Module
    """
    pass


class LogicError(TichuError):
    """
    Exception raised for LogicErrors.
    Raise this instead of writing 'Should never happen'.
    """
    pass


class IllegalActionException(TichuError):
    """
    Exception raised when a Player makes an illegal Move
    """
    pass


class PlayerException(TichuError):
    """
    Exception raised by a Player.
    """
    pass
