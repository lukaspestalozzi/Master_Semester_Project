from typing import Hashable, NewType, TypeVar, Tuple, List

NodeID = NewType('NodeID', Hashable)
Num = TypeVar('Num', int, float)
RewardVector = NewType('RewardVector', Tuple[Num, Num, Num, Num])

