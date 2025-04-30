#!/usr/bin/env python3.12
"""
metrics

Module containing the metrics class for tracking cache load.

Author: Radim Mifka

Date: 27.4.2025
"""

import time

from cache_server_app.src.cache.constants import AVG_RESPONSE_TIME_WEIGHT, HIT_RATIO_WEIGHT, REQUEST_RATE_WEIGHT

class CacheMetrics:
    """Class to track and report cache load metrics."""

    def __init__(self, cache_id: str):
        self.cache_id = cache_id
        self.request_count = 0
        self.hit_count = 0
        self.miss_count = 0
        self.total_response_time = 0.0
        self.last_update_time = time.time()

    def record_request(self, is_hit: bool, response_time: float) -> None:
        """Record a cache request and its metrics."""
        self.request_count += 1
        if is_hit:
            self.hit_count += 1
        else:
            self.miss_count += 1
        self.total_response_time += response_time
        self.last_update_time = time.time()

    def get_load_score(self) -> float:
        """Calculate a normalized load score (lower is better)."""
        if self.request_count == 0:
            return 0.0

        avg_response_time = self.total_response_time / self.request_count

        hit_ratio = self.hit_count / self.request_count if self.request_count > 0 else 0

        time_window = 60  # seconds
        recency_factor = min(1.0, (time.time() - self.last_update_time) / time_window)
        request_rate = self.request_count * (1 - recency_factor)

        # nomaliuation 40& avg, 30% hit ratio, 30% request rate
        return (avg_response_time * AVG_RESPONSE_TIME_WEIGHT) + ((1 - hit_ratio) * HIT_RATIO_WEIGHT) + (request_rate * REQUEST_RATE_WEIGHT)

    def to_dict(self) -> dict:
        """Convert metrics to a dictionary for serialization."""
        return {
            "cache_id": self.cache_id,
            "request_count": self.request_count,
            "hit_count": self.hit_count,
            "miss_count": self.miss_count,
            "total_response_time": self.total_response_time,
            "last_update_time": self.last_update_time,
            "load_score": self.get_load_score()
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'CacheMetrics':
        """Create a CacheMetrics instance from a dictionary."""
        metrics = cls(data["cache_id"])
        metrics.request_count = data["request_count"]
        metrics.hit_count = data["hit_count"]
        metrics.miss_count = data["miss_count"]
        metrics.total_response_time = data["total_response_time"]
        metrics.last_update_time = data["last_update_time"]
        return metrics
