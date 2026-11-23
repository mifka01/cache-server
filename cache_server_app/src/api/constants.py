"""
constants

This file contains constants used in api modules.

Author: Radim Mifka

Date: 28.4.2025
"""


# server
DATETIME_FORMAT = "%Y-%m-%dT%H:%M:%SZ"

# request bodies
MAX_JSON_BODY_SIZE = 16 * 1024 * 1024  # bytes; a narinfo query for ~400k store hashes
MAX_UPLOAD_PART_SIZE = 5 * 1024 * 1024 * 1024  # bytes; the largest part cachix sends

# outgoing HTTP requests (DHT service, remote caches)
HTTP_TIMEOUT = 10  # seconds without progress before a request is abandoned
