"""
base

This module provides an abstract class for storage objects.

Author: Radim Mifka
Date: 5.12.2024
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, List, Literal, Optional, Tuple, Union, overload


@dataclass
class StorageConfig:
    """Configuration requirements for a storage type.

    Attributes:
        required: List of required configuration keys
        prefix: Prefix for configuration keys
        config_key: Key used to identify this storage type in configuration
    """
    required: List[str]
    prefix: str
    config_key: str


class Storage(ABC):
    def __init__(
        self, id: str, name: str, type: str, config: Dict[str, str], root: str = ""
    ) -> None:
        """Initialize the storage object.

        Parameters:
            id (str): The ID of the storage.
            name (str): The name of the storage.
            type (str): The type of storage.
            config (Dict[str, str]): The storage configuration.
            root (str): The path to the root directory. Defaults to "".
        """
        self.id = id
        self.name = name
        self.type = type
        self.config = config
        self.root = root

        self.setup(config, root)

    def __str__(self) -> str:
        return f"{self.name} ({self.type})"

    @classmethod
    def get_config_requirements(cls) -> StorageConfig:
        """Get the configuration requirements for this storage type."""
        raise NotImplementedError

    @abstractmethod
    def setup(self, config: Dict[str, str], path: str) -> None:
        """Create a root directory if it does not exist.

        Parameters:
            path (str): The path to the root directory.
        """
        raise NotImplementedError

    @abstractmethod
    def new_file(self, path: str, data: bytes = b"") -> None:
        """Create a new file with the given data.

        Parameters:
            path (str): The path to the file from the root directory.
            data (bytes): The data to write to the file. Defaults to b"".
        """
        raise NotImplementedError

    @abstractmethod
    def save(self, path: str, data: bytes) -> None:
        """Save data to an existing file.

        Parameters:
            path (str): The path to the file from the root directory.
            data (bytes): The data to write to the file.
        """
        raise NotImplementedError

    @abstractmethod
    def remove(self, path: str) -> None:
        """Remove a file.

        Parameters:
            path (str): The path to the file to remove from the root directory.
        """
        raise NotImplementedError

    @overload
    def read(self, path: str, binary: Literal[True]) -> bytes: ...

    @overload
    def read(self, path: str, binary: Literal[False]) -> str: ...

    @overload
    def read(self, path: str) -> str: ...

    @abstractmethod
    def read(self, path: str, binary: bool = False) -> Union[str, bytes]:
        """Read the contents of a file.

        Parameters:
            path (str): The path to the file from the root directory.
            binary (bool): If True, the file is read in binary mode. Defaults to False.

        Returns:
            Union[str, bytes]: The contents of the file.
        """
        raise NotImplementedError

    @abstractmethod
    def rename(self, path: str, new_name: str) -> None:
        """Rename a file.

        Parameters:
            path (str): The path to the file to rename from the root directory.
            new_name (str): The new name of the file.
        """
        raise NotImplementedError

    @abstractmethod
    def list(self) -> List[str]:
        """List all files in the root directory.

        Returns:
            List[str]: A list of file names in the root directory.
        """
        raise NotImplementedError

    @abstractmethod
    def find(self, name: str, strict: bool = False) -> Optional[str]:
        """Check if a file with the given name exists in the root directory.

        Parameters:
            name (str): The name of the file to search for.
            strict (bool): If False, the search ignores extension. Defaults to False.

        Returns:
            Optional[str]: The path to the file if found, None otherwise.
        """
        raise NotImplementedError
