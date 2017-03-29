import random
import unittest
from tichu.gametree import GameTree, MultipleNodesError


class AllCombinationsTest(unittest.TestCase):

    def test_init(self):
        gt = GameTree()
        self.assertIsNone(gt.root)
        for k in range(10000):
            value = random.randint(-10000, 10000)
            gt = GameTree(root=value)
            self.assertTrue(gt.root == value, f"{gt}, value:{value}")

    def test_add_children_random(self):
        gt = GameTree(root=0)
        for k in range(10000):
            child = random.randint(1, 10000)
            parent = random.choice(list(gt._nodes.keys()))
            if child in gt:
                self.assertRaises(MultipleNodesError, gt.add_child, parent=parent, child=child)
            else:
                gt.add_child(parent=parent, child=child)
                self.assertTrue(gt.parent_of(child) == parent)
                self.assertTrue(child in gt.children_of(parent), f"child: {child}; children: {gt.children_of(parent)}; parent: {parent}")

    def test_specivic_scenarios1(self):
        gt = GameTree(root=0)
        gt.add_child(0, 1)
        gt.add_child(0, 2)
        gt.add_child(0, 3)

        gt.add_child(1, 11)
        gt.add_child(1, 12)

        gt.add_child(2, 21)
        gt.add_child(2, 22)

        gt.add_child(3, 31)
        gt.add_child(3, 32)
        gt.add_child(3, 33)

        gt.add_child(11, 111)
        gt.add_child(22, 221)

        self.assertTrue(gt.children_of(gt.root) == {1, 2, 3})
        self.assertTrue(gt.children_of(1) == {11, 12})
        self.assertTrue(gt.children_of(2) == {21, 22})
        self.assertTrue(gt.children_of(3) == {31, 32, 33})
        self.assertTrue(gt.children_of(11) == {111})
        self.assertTrue(gt.children_of(22) == {221})

        for p in [0, 1, 2, 3, 11, 22]:
            for c in gt.children_of(p):
                self.assertTrue(gt.parent_of(c) == p)

        self.assertTrue(gt.is_leaf(111))
        self.assertTrue(gt.is_leaf(221))
        self.assertTrue(gt.is_leaf(21))

        self.assertTrue(gt.is_leaf(0) is False)
        self.assertTrue(gt.is_leaf(11) is False)

        self.assertTrue(0 in gt)
        self.assertTrue(1 in gt)
        self.assertTrue(2 in gt)
        self.assertTrue(3 in gt)
        self.assertTrue(11 in gt)
        self.assertTrue(12 in gt)
        self.assertTrue(21 in gt)
        self.assertTrue(22 in gt)
        self.assertTrue(31 in gt)
        self.assertTrue(32 in gt)
        self.assertTrue(33 in gt)
        self.assertTrue(111 in gt)
        self.assertTrue(221 in gt)

        self.assertTrue(543 not in gt)
        self.assertTrue(-1 not in gt)


if __name__ == '__main__':
    unittest.main()