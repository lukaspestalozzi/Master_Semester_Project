

class LogicError(Exception):
    """
    Exception raised for LogicErrors.
    Raise this instead of writing 'Should never happen'.
    """
    pass


class IllegalActionException(Exception):
    """
    Exception raised when a Player makes an illegal Move
    """
    pass


class PlayerException(Exception):
    """
    Exception raised by a Player.
    """
    pass
