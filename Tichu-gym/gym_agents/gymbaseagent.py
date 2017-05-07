import abc

class BaseGymAgent(object):

    def action(self, state):
        return next(state.possible_actions())