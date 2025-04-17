#!/usr/bin/env python3.12
"""
type

Enum for storage type

Author: Radim Mifka

Date: 3.4.2025
"""

from enum import StrEnum


class StorageType(StrEnum):
    LOCAL = "local"
    S3 = "s3"

    @classmethod
    def list(cls):
        return [c.value for c in cls]

    @classmethod
    def str(cls):
        (", ".join(cls.list()))
