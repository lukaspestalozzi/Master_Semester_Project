import unittest
from tichu.utils import crange


class OtherTest(unittest.TestCase):

    def test_init(self):
        def trick_ends_iterative(curr, leading, next_):
            # assert curr != leading
            for k in crange(curr, curr, 4):
                if k == leading:
                    return True
                elif k == next_:
                    return False
        # fed

        def trick_ends_fast(curr, leading, next_):
            return leading == next_ or curr < leading < next_ or next_ < curr < leading or leading < next_ < curr
        # fed

        for c in range(4):
            for n in range(4):
                if c == n:
                    continue
                for l in range(4):
                    if c == l:
                        continue
                    it, fast = trick_ends_iterative(c, l, n), trick_ends_fast(c, l, n)
                    self.assertEqual(it, fast, f"it: {it}, fast: {fast}, curr: {c}, leading: {l}, next: {n}")


if __name__ == '__main__':
    unittest.main()
