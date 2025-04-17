#!/usr/bin/env python3.12
"""
access

Enum for cache access type

Author: Radim Mifka
Date: 3.4.2025
"""

from enum import Enum
from typing import List


class CacheAccess(Enum):
    PUBLIC = "public"
    PRIVATE = "private"

    def __str__(self) -> str:
        return self.value

    @classmethod
    def list(cls) -> List[str]:
        return [access.value for access in cls]

    @classmethod
    def str(cls):
        return ", ".join(cls.list())

