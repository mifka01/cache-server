"""
s3

This module contains the implementation of the S3Storage class, which is a subclass of the Storage class.

Author: Radim Mifka

Date: 5.12.2024
"""

import os
from typing import Dict

import boto3
from botocore.exceptions import ClientError

from cache_server_app.src.storage.base import Storage, StorageConfig
from cache_server_app.src.storage.registry import StorageRegistry
from cache_server_app.src.storage.type import StorageType


@StorageRegistry.register(StorageType.S3)
class S3Storage(Storage):
    @classmethod
    def get_config_requirements(cls) -> StorageConfig:
        """Get the configuration requirements for S3 storage."""
        return StorageConfig(
            required=["bucket", "region", "access-key", "secret-key"],
            prefix="s3_",
            config_key="s3"
        )

    def setup(self, config: Dict[str, str], path: str) -> None:
        if not self.__valid_credentials(
            config["s3_access-key"], config["s3_secret-key"]
        ):
            #!TODO Change this
            raise IOError("Invalid S3 credentials")

        self.s3_client = boto3.client(
            "s3",
            aws_access_key_id=config["s3_access-key"],
            aws_secret_access_key=config["s3_secret-key"],
        )

        self.bucket = config["s3_bucket"]
        self.root = path.strip("/") + "/"

    def get_type(self) -> str:
        return StorageType.S3

    def new_file(self, path: str, data: bytes = b"") -> None:
        full_path = os.path.join(self.root, path).lstrip("/")

        try:
            self.s3_client.put_object(Bucket=self.bucket, Key=full_path, Body=data)
        except ClientError as e:
            raise IOError(f"Error creating file {path}: {e}")

    def save(self, path: str, data: bytes) -> None:
        full_path = os.path.join(self.root, path).lstrip("/")

        try:
            self.s3_client.put_object(Bucket=self.bucket, Key=full_path, Body=data)
        except ClientError as e:
            raise IOError(f"Error saving file {path}: {e}")

    def remove(self, path: str) -> None:
        full_path = os.path.join(self.root, path).lstrip("/")

        try:
            self.s3_client.delete_object(Bucket=self.bucket, Key=full_path)
        except ClientError as e:
            raise IOError(f"Error removing file {path}: {e}")

    def read(self, path: str, binary: bool = False) -> str | bytes:
        full_path = os.path.join(self.root, path).lstrip("/")

        try:
            response = self.s3_client.get_object(Bucket=self.bucket, Key=full_path)
            data = response["Body"].read()

            return data if binary else data.decode("utf-8")
        except ClientError as e:
            raise IOError(f"Error reading file {path}: {e}")

    def rename(self, path: str, new_name: str) -> None:
        full_old_path = os.path.join(self.root, path).lstrip("/")
        full_new_path = os.path.join(self.root, new_name).lstrip("/")

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
                Bucket=self.bucket, Prefix=self.root
            )

            return [
                obj["Key"][len(self.root) :]
                for obj in response.get("Contents", [])
                if obj["Key"] != self.root
            ]
        except ClientError as e:
            raise IOError(f"Error listing files: {e}")

    def find(self, name: str, strict: bool = False) -> str | None:
        try:
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket, Prefix=self.root
            )

            for obj in response.get("Contents", []):
                file_path = obj["Key"][len(self.root) :]

                if strict and file_path == name:
                    return file_path
                elif not strict and name in file_path:
                    return file_path

            return None
        except ClientError as e:
            raise IOError(f"Error finding file {name}: {e}")

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
