#!/usr/bin/env python3.12
"""
strategies

This file contains storage strategies for selecting the appropriate storage

Author: Radim Mifka

Date: 29.4.2025
"""


from enum import StrEnum
from typing import List

from cache_server_app.src.storage.base import Storage
from cache_server_app.src.types import StrategyStateDict

def round_robin(storages: List[Storage], state: StrategyStateDict) -> Storage:
    """ This strategy selects the next storage in the list, wrapping around """

    index = state.get("index", 0)

    if not isinstance(index, int):
        index = 0
        print("ERROR: index is not an int, should never happen, resetting to 0")

    index = index % len(storages)

    state["index"] = index + 1

    # try to find any empty storage
    if storages[index].is_full():
        return in_order(storages, state)

    return storages[index]

def in_order(storages: List[Storage], _: StrategyStateDict) -> Storage:
    """ This strategy selects the first storage in order that is not full """
    for storage in storages:
        if not storage.is_full():
            return storage

    raise ValueError("All storages are full")

def split(storages: List[Storage], state: StrategyStateDict) -> Storage:
    """ This strategy selects the storage by desired split value"""
    splits = state.get(Strategy.SPLIT.value, [])

    if not isinstance(splits, list):
        print("ERROR: splits is not a list, should never happen, fallback to in_order")
        return in_order(storages, state)

    total_used = sum(storage.get_used_space() for storage in storages)
    least_used = 0.0
    index = 0

    for i in range(len(storages)):
        used = storages[i].get_used_space()
        normalized = (used / total_used) * 100

        if not isinstance(splits[i], int):
            print("ERROR: splits is not a int, should never happen, fallback to in_order")
            return in_order(storages, state)

        delta = float(splits[i]) - normalized

        if delta > least_used:
            least_used = delta
            index = i

    # try to find any empty storage
    if storages[index].is_full():
        return in_order(storages, state)

    return storages[index]

def least_used(storages: List[Storage], _: StrategyStateDict) -> Storage:
    """ This strategy selects the storage with the least used space """
    least_used = min(storages, key=lambda s: s.get_used_space())
    if least_used.is_full():
        return in_order(storages, _)
    return least_used


class Strategy(StrEnum):
    ROUND_ROBIN = "round-robin"
    IN_ORDER = "in-order"
    SPLIT = "split"

    def __str__(self) -> str:
        return self.value

    def func(self, storages: List[Storage], state: StrategyStateDict) -> Storage:
        return STRATEGIES[self](storages, state)

STRATEGIES = {
    Strategy.ROUND_ROBIN: round_robin,
    Strategy.IN_ORDER: in_order,
    Strategy.SPLIT: split
}
