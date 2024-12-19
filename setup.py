#!/usr/bin/env python3.12
from setuptools import setup

setup(
    name="cache-server",
    version="1.0",
    packages=[
        "cache_server_app",
        "cache_server_app/src",
        "cache_server_app/src/storage",
    ],
    install_requires=["websockets", "pyjwt", "ed25519"],
    entry_points={
        "console_scripts": ["cache-server = cache_server_app.main:main"],
    },
)
