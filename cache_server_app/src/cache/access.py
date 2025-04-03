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

