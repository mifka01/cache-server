"""
constants

This module contains constants used in the cache classes.

Author: Radim Mifka

Date: 29.4.2025
"""

# WEIGHTS
# should add up to 1

## load score
AVG_RESPONSE_TIME_WEIGHT = 0.4
HIT_RATIO_WEIGHT = 0.3
REQUEST_RATE_WEIGHT = 0.3

## total score
LATENCY_WEIGHT = 0.2
LOAD_SCORE_WEIGHT = 0.8
