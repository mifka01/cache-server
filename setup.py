#!/usr/bin/env python3.12
from setuptools import setup

setup(
    name="cache-server",
    version="1.0",
    packages=[
        "cache_server_app",
        "cache_server_app/src",
        "cache_server_app/src/cache",
        "cache_server_app/src/commands",
        "cache_server_app/src/config",
        "cache_server_app/src/parser",
        "cache_server_app/src/storage",
        "cache_server_app/src/storage/providers",
    ],
    install_requires=["websockets", "pyjwt", "ed25519", 'boto3', 'pyyaml'],
    entry_points={
        "console_scripts": ["cache-server = cache_server_app.main:main"],
    },
)
