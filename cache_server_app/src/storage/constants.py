"""
constants

This module contains constants used in storage classes.

Author: Radim Mifka

Date: 28.4.2025
"""

# storage
MAX_STORAGE_USAGE = 0.95  # fraction of the file system in use at which a storage counts as full
CONSIDERED_NEW_FILE_AGE = 3600  # seconds
STREAM_CHUNK_SIZE = 1024 * 1024  # bytes read or written at once when streaming files
UPLOAD_COMPRESSIONS = ("xz", "zst")  # NAR compressions accepted for uploads

# local storage
DIR_PERMISSIONS = 0o755
