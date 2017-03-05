

class ExceptionWithMessage(Exception):
    """
    Exception that contains a message
    """

    def __init__(self, message):
        self.message = message

    def __str__(self):
        return repr(self.message)

class LogicError(ExceptionWithMessage):
    """
    Exception raised for LogicErrors.
    Raise this instead of writing 'Should never happen'.
    """
    def __init__(self, message):
        super().__init__(message)


class IllegalActionError(ExceptionWithMessage):
    """
    Exception raised when a Player makes an illegal Move
    """
    def __init__(self, message):
        super().__init__(message)
