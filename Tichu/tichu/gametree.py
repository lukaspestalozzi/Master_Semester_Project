

class GameTree(object):

    def __init__(self, root=None):
        self._nodes = {}  # state -> node
        self._root_node = None
        if root is not None:
            self.add_root(root)

    def children(self, state):
        return self._nodes[state].children

    def parent(self, state):
        return self._nodes[state].parent

    def add_child(self, parent, action, child):
        """
        :Adds the given child to the given parent.
        :If parent is not in the Tree, tries to add the parent as root.

        :param parent:
        :param action:
        :param child:
        :return:
        :raises NoParentError: if the parent is None.
        :raises MultipleRootsError: if there is already a root in the tree, but the parent is not in the tree
        """
        if parent is None:
            raise NoParentError("Parent can't be None")
        try:
            parent_node = self._nodes[parent]
        except KeyError:
            # parent is not in the tree, try to make it root.
            parent_node = self.add_root(parent)  # raises MultipleRootsError if there is already a root

        # add the child
        self._nodes[child] = parent_node._add_child(action=action, data=child)

    def add_root(self, root):
        """
        Adds a root Node with root as data
        :param root:
        :return:
        :raises MultipleRootsError: If there is already a root in the Tree.
        """
        if self._root_node is not None:
            raise MultipleRootsError("This Tree already has a Root")
        assert root not in self._nodes  # sanity check
        self._root_node = Node(parent=None, action=None, data=root)
        self._nodes[root] = self._root_node


class Node(object):

    def __init__(self, parent, action, data=None):
        self._parent = parent  # the parent node (None for root)
        self._action = action  # the action lead here
        self._data = data  # any object
        self._children = []  # list of nodes
        self._actions = {}  # action -> child_node

    @property
    def parent(self):
        return self._parent.data

    @property
    def action(self):
        return self._action

    @property
    def data(self):
        return self._data

    @property
    def children(self):
        return [c.data for c in self._children]

    def child_for_action(self, action):
        return self._actions[action].data

    def _add_child(self, action, data):
        """
        :param action:
        :param data:
        :return: the newly created child node
        """
        # TODO allow duplicated actions/children
        assert action not in self._actions
        child_node = Node(parent=self, action=action, data=data)
        self._children.append(child_node)
        self._actions[action] = child_node
        return child_node

    def is_root(self):
        return self._parent is None

    def is_leaf(self):
        return len(self._children) == 0

    def __getattr__(self, i):
        return self._children[i].data

# --------- Tree Exceptions --------------------


class TreeError(Exception):
    pass


class MultipleRootsError(TreeError, ValueError):
    pass


class NoParentError(TreeError, ValueError):
    pass

