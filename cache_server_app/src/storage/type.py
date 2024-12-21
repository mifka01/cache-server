from enum import StrEnum


class StorageType(StrEnum):
    LOCAL = "local"
    S3 = "s3"

    @classmethod
    def list(cls):
        return [c.value for c in cls]
