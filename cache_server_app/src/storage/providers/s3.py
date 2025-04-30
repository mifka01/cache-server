"""
s3

This module contains the implementation of the S3Storage class, which is a subclass of the Storage class.

Author: Radim Mifka

Date: 5.12.2024
"""

import os
from typing import Dict
from datetime import datetime, timezone

import boto3
from botocore.exceptions import ClientError
import sys

from cache_server_app.src.storage.base import Storage, StorageConfig
from cache_server_app.src.storage.registry import StorageRegistry
from cache_server_app.src.storage.type import StorageType
from cache_server_app.src.storage.constants import CONSIDERED_NEW_FILE_AGE


@StorageRegistry.register(StorageType.S3)
class S3Storage(Storage):
    @classmethod
    def get_config_requirements(cls) -> StorageConfig:
        """Get the configuration requirements for S3 storage."""
        return StorageConfig(
            required=["bucket", "region", "access-key", "secret-key"],
            prefix="s3_",
            config_key=StorageType.S3.value,
        )

    def setup(self, config: Dict[str, str], path: str) -> None:
        if not self.__valid_credentials(
            config[f"s3_access-key"], config["s3_secret-key"]
        ):
            #TODO Check this
            raise IOError("Invalid S3 credentials")

        self.s3_client = boto3.client(
            "s3",
            aws_access_key_id=config["s3_access-key"],
            aws_secret_access_key=config["s3_secret-key"],
        )

        self.bucket = config["s3_bucket"]
        self.storage_path = path.strip("/") + "/"

    def get_type(self) -> str:
        return StorageType.S3


    def new_file(self, path: str, data: bytes = b"") -> None:
        full_path = os.path.join(self.storage_path, path).lstrip("/")

        try:
            self.s3_client.put_object(Bucket=self.bucket, Key=full_path, Body=data)
        except ClientError as e:
            raise IOError(f"Error creating file {path}: {e}")

    def save(self, path: str, data: bytes) -> None:
        full_path = os.path.join(self.storage_path, path).lstrip("/")

        try:
            self.s3_client.put_object(Bucket=self.bucket, Key=full_path, Body=data)
        except ClientError as e:
            raise IOError(f"Error saving file {path}: {e}")

    def remove(self, path: str) -> None:
        full_path = os.path.join(self.storage_path, path).lstrip("/")

        try:
            self.s3_client.delete_object(Bucket=self.bucket, Key=full_path)
        except ClientError as e:
            raise IOError(f"Error removing file {path}: {e}")

    def clear(self) -> None:
        try:
            response = self.s3_client.list_objects_v2(Bucket=self.bucket, Prefix=self.storage_path)

            for obj in response.get("Contents", []):
                self.s3_client.delete_object(Bucket=self.bucket, Key=obj["Key"])
        except ClientError as e:
            raise IOError(f"Error clearing storage: {e}")

    def read(self, path: str, binary: bool = False) -> str | bytes:
        full_path = os.path.join(self.storage_path, path).lstrip("/")

        try:
            response = self.s3_client.get_object(Bucket=self.bucket, Key=full_path)
            data = response["Body"].read()

            return data if binary else data.decode("utf-8")
        except ClientError as e:
            raise IOError(f"Error reading file {path}: {e}")

    def rename(self, path: str, new_name: str) -> None:
        full_old_path = os.path.join(self.storage_path, path).lstrip("/")
        full_new_path = os.path.join(self.storage_path, new_name).lstrip("/")

        try:
            self.s3_client.copy_object(
                Bucket=self.bucket,
                CopySource={"Bucket": self.bucket, "Key": full_old_path},
                Key=full_new_path,
            )

            self.s3_client.delete_object(Bucket=self.bucket, Key=full_old_path)
        except ClientError as e:
            raise IOError(f"Error renaming file from {path} to {new_name}: {e}")

    def list(self) -> list[str]:
        try:
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket, Prefix=self.storage_path
            )

            return [
                obj["Key"][len(self.storage_path) :]
                for obj in response.get("Contents", [])
                if obj["Key"] != self.storage_path
            ]
        except ClientError as e:
            raise IOError(f"Error listing files: {e}")

    def get_file_creation_time(self, path: str) -> datetime:
        full_path = os.path.join(self.storage_path, path).lstrip("/")

        try:
            response = self.s3_client.head_object(Bucket=self.bucket, Key=full_path)
            return datetime.fromtimestamp(
                response["LastModified"].timestamp(), tz=timezone.utc
            )
        except ClientError as e:
            raise IOError(f"Error getting file creation time for {path}: {e}")

    def is_new_file(self, path: str) -> bool:
        try:
            file_mod_time = self.get_file_creation_time(path)
            current_time = datetime.now(timezone.utc)

            return (current_time - file_mod_time).total_seconds() <= CONSIDERED_NEW_FILE_AGE
        except ClientError as e:
            raise IOError(f"Error checking if file {path} is new: {e}")

    def find(self, name: str, strict: bool = False) -> str | None:
        try:
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket, Prefix=self.storage_path
            )

            for obj in response.get("Contents", []):
                file_path = obj["Key"][len(self.storage_path) :]

                if strict and file_path == name:
                    return file_path
                elif not strict and name in file_path:
                    return file_path

            return None
        except ClientError as e:
            raise IOError(f"Error finding file {name}: {e}")

    def get_available_space(self) -> int:
        """Get the available space in bytes."""
        return sys.maxsize # s3 does not provide a way to get available space

    def get_used_space(self) -> int:
        """Get the used space in bytes."""
        try:
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket, Prefix=self.storage_path
            )
            total_size = sum(
                obj["Size"] for obj in response.get("Contents", [])
            )
            return total_size
        except ClientError as e:
            raise IOError(f"Error getting used space: {e}")

    def is_full(self) -> bool:
        """Check if the storage is full."""
        return False

    def __valid_credentials(self, access_key: str, secret_key: str) -> bool:
        try:
            boto3.client(
                "sts",
                aws_access_key_id=access_key,
                aws_secret_access_key=secret_key,
            ).get_caller_identity()
            return True
        except ClientError as e:
            return False
