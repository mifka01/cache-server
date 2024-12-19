"""
base

This module provides an abstract class for storage objects.

Author: Radim Mifka
Date: 5.12.2024
"""

from abc import ABC, abstractmethod
from typing import Dict


class Storage(ABC):
    def __init__(self, config: Dict[str, str], root: str = "") -> None:
        """Initialize the storage object.

        Parameters:
            root (str): The path to the root directory. Defaults to "".
        """
        self.root = root
        self.config = config

        self.setup(config, root)

    def __str__(self) -> str:
        return self.get_type()

    @abstractmethod
    def setup(self, config: Dict[str, str], path: str) -> None:
        """Create a root directory if it does not exist.

        Parameters:
            path (str): The path to the root directory.
        """
        raise NotImplementedError

    @abstractmethod
    def get_type(self) -> str:
        """Return the type of the storage.

        Returns:
            str: The type of the storage.
        """
        raise NotImplementedError

    @abstractmethod
    def new_file(self, path: str, data: bytes = b"") -> None:
        """Create a new file with the given data.

        Parameters:
            path (str): The path to the file from the root directory.
            data (str): The data to write to the file. Defaults to b"".
        """
        raise NotImplementedError

    @abstractmethod
    def save(self, path: str, data: bytes) -> None:
        """Save data to an existing file.

        Parameters:
            path (str): The path to the file from the root directory.
            data (str): The data to write to the file.
        """
        raise NotImplementedError

    @abstractmethod
    def remove(self, path: str) -> None:
        """Remove a file.

        Parameters:
            path (str): The path to the file to remove from the root directory.
        """
        raise NotImplementedError

    @abstractmethod
    def read(self, path: str, binary: bool = False) -> str | bytes:
        """Read the contents of a file.

        Parameters:
            path (str): The path to the file from the root directory.
            binary (bool): If True, the file is read in binary mode. Defaults to False.

        Returns:
            str | bytes: The contents of the file.
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
    def list(self) -> list[str]:
        """List all files in the root directory.

        Returns:
            list: A list of file names in the root directory.
        """
        raise NotImplementedError

    @abstractmethod
    def find(self, name: str, strict: bool = False) -> str | None:
        """Check if a file with the given name exists in the root directory.

        Parameters:
            name (str): The name of the file to search for.
            strict (bool): If False, the search ignores extension. Defaults to False.

        Returns:
            str | None: The path to the file if found, None otherwise.
        """
        raise NotImplementedError
