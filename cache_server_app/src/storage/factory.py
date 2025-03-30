import importlib

from cache_server_app.src.storage.base import Storage
from cache_server_app.src.storage.type import StorageType


class StorageFactory:
    @staticmethod
    def create_storage(storage_type: str, *args) -> Storage:
        try:
            storage_enum = StorageType(storage_type.lower())

            #!TODO Check this
            module_name = f"cache_server_app.src.storage.providers.{storage_enum.value}"

            class_name = f"{storage_enum.value.capitalize()}Storage"
            module = importlib.import_module(module_name)

            storage_class = getattr(module, class_name)

            return storage_class(storage_enum, *args)

        except (ValueError, AttributeError) as e:
            valid_types = ", ".join(StorageType.list())
            raise ValueError(f"Invalid storage type. Valid types are: {valid_types}")
