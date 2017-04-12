import logging

from pprint import pformat
from tichu.utils import check_isinstance


u2514 = u'\u2514'  # 'L'
u251C = u'\u251C'  # '|-'
u2500 = u'\u2500'  # '-'
u2502 = u'\u2502'  # '|'


class GameTree(object):
    """
    A n-ary Tree

    - Each node has an associated game state (may be None)
    - Each node has exactly one parent pointer (None only for the Root)
    - The edges between a parent and a child should represent actions in the Game that change the game state.
    - Each node has a set of children. Note that not all children of a node P must have P as parent-pointer.
      This allows different action paths to lead to the same game state.
    """

    def __init__(self, root=None):
        self._nodes = dict()  # state -> node
        self._root_node = None
        if root is not None:
            self.add_root(root)

    @property
    def root(self):
        return self._root_node.data if self._root_node is not None else None

    @property
    def size(self):
        """
        :return: The number of Nodes in the Tree
        """
        return len(self._nodes)

    def children_of(self, state):
        return {cn.data for cn in self._node(state).children_nodes}

    def parent_of(self, state):
        try:
            parent_node = self._node(state).parent_node
        except KeyError as ke:
            raise NotInTreeError from ke
        else:
            return parent_node.data if parent_node is not None else None

    def add_child(self, parent, child):
        """
        Adds the given child to the given parent.

        If parent is not in the Tree, tries to add the parent as root.

        If the child is already in the Tree under a different Parent, then adds the existing child-node to the given parent.
        The child-node still has the old parent but is now present in both parent-nodes child set.

        :param parent: parent game state
        :param child: child game state
        :return: self
        :raises NoParentError: if the parent is None.
        :raises MultipleRootsError: if there is already a root in the tree, but the parent is not in the tree
        """
        if parent is None:
            raise NoParentError("Parent can't be None, use 'tree.add_root(child)' instead.")
        elif child in self._nodes:
            if child in self.children_of(parent):
                logging.debug("[add_child] tried to add a child already in the tree, but parent matched -> kept already existing child node")
                return self  # the child is already there -> keep existing node
            else:
                logging.debug("[add_child] tried to add a child already in the tree, under another parent -> kept already existing child node and added it to the parents children")
                self._node(parent).add_child_node(self._node(child))  # the child already exists -> keep existing child and add it to the parent's children
                return self
        else:
            try:
                parent_node = self._node(parent)
            except NotInTreeError:
                # parent is not in the tree, try to make it root.
                parent_node = self.add_root(parent)  # raises MultipleRootsError if there is already a root

            # add the child
            child_node = self._create_node(parent=parent_node, data=child)
            parent_node.add_child_node(child_node)
            self._nodes[child] = child_node
        return self

    def add_root(self, root):
        """
        Adds a root Node with root as game state

        :param root: the state
        :return: self
        :raises MultipleRootsError: If there is already a root in the Tree.
        """
        if self._root_node is not None:
            raise MultipleRootsError("This Tree already has a Root")
        assert root not in self._nodes  # sanity check
        self._root_node = self._create_node(parent=None, data=root)
        self._nodes[root] = self._root_node
        return self

    def is_leaf(self, state):
        return self._node(state).is_leaf()

    def pretty_string(self):
        if self._root_node is None:
            return "Tree is empty (Root is None)"
        else:
            return pformat(self._nodes)

    def print_hierarchy(self):
        return self._root_node.print_hierarchy(indent='', last=True)

    def clear(self):
        """
        Remove all Nodes from the Tree
        :return: tuple(nodes dict, rootdata)
        """
        logging.debug("Clearing The Tree.")
        nds = self._nodes
        self._nodes = dict()
        r = self.root
        self._root_node = None
        return (nds, r)

    def _node(self, state):
        try:
            return self._nodes[state]
        except KeyError as ke:
            raise NotInTreeError(f"'{state}' is not in the Tree.") from ke

    def _create_node(self, parent, data):
        """
        Creates a node, subclasses can overwrite this method to inject custom Nodes into the tree
        :param parent:
        :param data:
        :return:
        """
        return GameTreeNode(parent=parent, data=data)

    def __contains__(self, state):
        return state in self._nodes

    def __str__(self):
        if self._root_node is None:
            return "Tree is empty (Root is None)"
        else:
            return pformat(self._nodes)


class GameTreeNode(object):

    def __init__(self, parent, data=None):
        # assert action is None or isinstance(action, PlayerAction), f"action: {action}"
        parent is None or check_isinstance(parent, GameTreeNode)
        self._parent = parent  # the parent node (None for root)
        self._data = data  # any object
        self._children = set()

    @property
    def parent_node(self):
        return self._parent

    @property
    def data(self):
        return self._data

    @property
    def children_nodes(self):
        return frozenset(self._children)

    def add_child_node(self, node):
        self._children.add(node)

    def is_root(self):
        return self._parent is None

    def is_leaf(self):
        return len(self._children) == 0

    def _short_label(self):
        if self.is_root():
            return 'Root'
        else:
            return str(hash(self.data))

    def print_hierarchy(self, indent, last):
        string = ''
        next_indent = indent
        node_label = self._short_label()
        if self.is_root():
            string += node_label + '\n'
        else:
            string += f"{indent}{(u2514 if last else u251C)}{u2500}{u2500}{node_label}\n"
            if last and len(self._children) == 0:
                string += indent + '\n'
            next_indent = f'{indent}{" " if last else u2502}  '
        for k, childnode in enumerate(self._children):
            string += childnode.print_hierarchy(next_indent, last=k == len(self._children)-1)
        return string


# --------- Tree Exceptions --------------------


class TreeError(Exception): pass


class MultipleRootsError(TreeError, ValueError): pass


class NoParentError(TreeError, ValueError): pass


class NotInTreeError(TreeError, ValueError): pass


class MultipleNodesError(TreeError, ValueError): pass
